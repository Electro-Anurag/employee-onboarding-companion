"""Private, versioned S3 storage. No presigned URLs or browser credentials."""
import hashlib
from urllib.parse import urlsplit
from django.conf import settings
from backend.onboarding.services import CommandFailure

MAX_FILE=10*1024*1024
def configured():
    return (getattr(settings,'M3_REAL_DOCUMENT_ENABLED',False)
        and bool(getattr(settings,'M3_S3_QUARANTINE_BUCKET',''))
        and bool(getattr(settings,'M3_S3_CLEAN_BUCKET',''))
        and getattr(settings,'M3_S3_QUARANTINE_BUCKET')!=getattr(settings,'M3_S3_CLEAN_BUCKET'))

def _validate_custom_endpoint():
    """Only an explicitly opted-in loopback MinIO endpoint may omit AWS KMS.

    Validate before constructing the network client, even for HEAD/list reads.
    A local-testing flag must never authorize a remote, unencrypted S3 host.
    """
    endpoint=getattr(settings,'M3_S3_ENDPOINT_URL','')
    if not endpoint:
        return
    try:
        parsed=urlsplit(endpoint)
        allowed=(getattr(settings,'M3_S3_ALLOW_LOCAL_TEST_ENDPOINT',False)
            and parsed.scheme in ('http','https')
            and parsed.hostname in ('127.0.0.1','localhost','::1')
            and parsed.port==9000
            and parsed.username is None and parsed.password is None
            and parsed.path in ('','/')
            and not parsed.query and not parsed.fragment)
    except ValueError:
        allowed=False
    if not allowed:
        raise CommandFailure('UNAPPROVED_STORAGE_ENDPOINT',503)

def client():
    if not configured():raise CommandFailure('REAL_DOCUMENT_STORAGE_DISABLED',404)
    _validate_custom_endpoint()
    import boto3
    from botocore.config import Config
    return boto3.client('s3',endpoint_url=getattr(settings,'M3_S3_ENDPOINT_URL',None) or None,
        region_name=getattr(settings,'M3_S3_REGION','ap-southeast-1'),
        config=Config(signature_version='s3v4',connect_timeout=4,read_timeout=15,
                      retries={'max_attempts':2},s3={'addressing_style':'path'}))

def buckets(s3):
    q=settings.M3_S3_QUARANTINE_BUCKET
    clean=settings.M3_S3_CLEAN_BUCKET
    try:
        if any(s3.get_bucket_versioning(Bucket=b).get('Status')!='Enabled' for b in (q,clean)):
            raise CommandFailure('VERSIONED_PRIVATE_STORAGE_REQUIRED',503)
    except CommandFailure:raise
    except Exception as exc:raise CommandFailure('OBJECT_STORAGE_UNAVAILABLE',503) from exc
    return q,clean

def encryption_options():
    # The local MinIO test endpoint may not offer SSE-KMS. Genuine AWS S3
    # requires a configured KMS key; never silently downgrade cloud encryption.
    if getattr(settings,'M3_S3_ENDPOINT_URL',''):
        _validate_custom_endpoint()
        return {}
    key=getattr(settings,'M3_S3_KMS_KEY_ID','')
    if not key:raise CommandFailure('KMS_KEY_REQUIRED',503)
    return {'ServerSideEncryption':'aws:kms','SSEKMSKeyId':key}

def put_quarantine(upload,raw):
    if len(raw)!=upload.byte_length or hashlib.sha256(raw).hexdigest()!=upload.sha256:
        raise CommandFailure('UPLOAD_CONTENT_MISMATCH',422)
    s3=client()
    q,_=buckets(s3)
    try:
        data=s3.put_object(Bucket=q,Key=upload.object_key,Body=raw,ContentType='application/pdf',
            Metadata={'sha256':upload.sha256},IfNoneMatch='*',**encryption_options())
        vid=data.get('VersionId')
        if not vid or vid=='null':raise CommandFailure('OBJECT_VERSION_MISSING',503)
        return str(vid)
    except CommandFailure:raise
    except Exception as exc:
        # If a process died after S3 committed but before DB finalization,
        # If-None-Match correctly rejects re-upload. Reconcile ONLY that exact
        # conflict, then read and SHA-verify the immutable stored version.
        # All other storage failures stay fail-closed.
        from botocore.exceptions import ClientError
        if (not isinstance(exc,ClientError)
                or exc.response.get('ResponseMetadata',{}).get('HTTPStatusCode')!=412
                or exc.response.get('Error',{}).get('Code') not in
                    ('PreconditionFailed','PreconditionFailedException')):
            raise CommandFailure('QUARANTINE_WRITE_FAILED',503) from exc
        try:
            info=s3.head_object(Bucket=q,Key=upload.object_key)
            vid=info.get('VersionId')
            if not vid or vid=='null':
                raise CommandFailure('OBJECT_VERSION_MISSING',503)
            # Do not trust caller metadata, ETags or the existence of a key.
            # read_exact makes recovery content-addressed and version-pinned.
            recovered=read_exact(q,upload.object_key,str(vid),upload.sha256)
            if len(recovered)!=upload.byte_length:
                raise CommandFailure('OBJECT_INTEGRITY_FAILED',409)
            return str(vid)
        except CommandFailure:raise
        except Exception as recovery_error:
            raise CommandFailure('QUARANTINE_RECOVERY_FAILED',503) from recovery_error

def read_exact(bucket,key,version,expected_sha,max_bytes=MAX_FILE):
    s3=client()
    try:
        response=s3.get_object(Bucket=bucket,Key=key,VersionId=version)
        raw=response['Body'].read(max_bytes+1)
        response['Body'].close()
    except Exception as exc:raise CommandFailure('OBJECT_READ_FAILED',503) from exc
    if len(raw)>max_bytes or hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise CommandFailure('OBJECT_INTEGRITY_FAILED',409)
    return raw

def promote(upload,quarantine_version):
    s3=client()
    q,clean=buckets(s3)
    key='clean/'+str(upload.task.case_id)+'/'+str(upload.id)+'.pdf'
    try:
        result=s3.copy_object(Bucket=clean,Key=key,
            CopySource={'Bucket':q,'Key':upload.object_key,'VersionId':quarantine_version},
            Metadata={'sha256':upload.sha256},MetadataDirective='REPLACE',
            ContentType='application/pdf',**encryption_options())
        vid=result.get('VersionId')
        if not vid or vid=='null':raise CommandFailure('CLEAN_VERSION_MISSING',503)
        # Exact-version read verifies copied bytes, not ETag (multipart ETags differ).
        read_exact(clean,key,str(vid),upload.sha256)
        return key,str(vid)
    except CommandFailure:raise
    except Exception as exc:raise CommandFailure('CLEAN_PROMOTION_FAILED',503) from exc

def download(clean):
    return read_exact(settings.M3_S3_CLEAN_BUCKET,clean.object_key,
                      clean.version_id,clean.upload.sha256)
