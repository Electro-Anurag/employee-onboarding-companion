"""Private, versioned S3 storage. No presigned URLs or browser credentials."""
import hashlib
import os
from django.conf import settings
from backend.onboarding.services import CommandFailure

MAX_FILE=10*1024*1024
def configured():
    return (getattr(settings,'M3_REAL_DOCUMENT_ENABLED',False)
        and bool(getattr(settings,'M3_S3_QUARANTINE_BUCKET',''))
        and bool(getattr(settings,'M3_S3_CLEAN_BUCKET',''))
        and getattr(settings,'M3_S3_QUARANTINE_BUCKET')!=getattr(settings,'M3_S3_CLEAN_BUCKET'))

def client():
    if not configured():raise CommandFailure('REAL_DOCUMENT_STORAGE_DISABLED',404)
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
        if not getattr(settings,'M3_S3_ALLOW_LOCAL_TEST_ENDPOINT',False):
            raise CommandFailure('UNAPPROVED_STORAGE_ENDPOINT',503)
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
    except Exception as exc:raise CommandFailure('QUARANTINE_WRITE_FAILED',503) from exc

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
