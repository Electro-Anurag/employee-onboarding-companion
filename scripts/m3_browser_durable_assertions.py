"""Post-browser R2 proof from actual DB queue, audit and S3 immutable VersionIds."""
import os
import uuid
from pathlib import Path
if (os.getenv('M3_LIVE_S3_CLAMAV')!='1'
        or os.getenv('M3_S3_ENDPOINT_URL')!='http://127.0.0.1:9000'
        or not os.getenv('M3_CI_CRASH_MARKER')):
    raise SystemExit('Live isolated S3/ClamAV runner only')
marker=Path(os.environ['M3_CI_CRASH_MARKER'])
assert marker.read_text()=='WEB_EXIT_79_AFTER_REAL_S3_PUT\n'
data=Path(os.environ['M3_LIVE_BROWSER_CREDENTIAL_FILE']).read_text().splitlines()
cid=uuid.UUID(next(line.split()[1] for line in data if line.startswith('CASE ')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','backend.config.settings')
import django
django.setup()
from django.db import connection
from backend.documents.real_models import (SecureUpload,StoredQuarantineObject,
    SecureCleanObject,SecureScanAttempt,SecureHRReview)
from backend.documents import storage
from backend.onboarding.models import Task,TaskCompletion
from backend.audit.models import AuditEvent,CommandReceipt
case_tasks=Task.objects.filter(case_id=cid)
task=case_tasks.get(key='identity_document')
successor=case_tasks.get(key='equipment_setup')
uploads=list(SecureUpload.objects.filter(task=task).order_by('revision'))
assert len(uploads)==2 and [u.revision for u in uploads]==[1,2]
first,last=uploads
assert not StoredQuarantineObject.objects.filter(upload=first).exists()
assert not SecureScanAttempt.objects.filter(upload=first).exists()
assert not SecureCleanObject.objects.filter(upload=first).exists()
assert StoredQuarantineObject.objects.filter(upload=last).count()==1
assert SecureScanAttempt.objects.filter(upload=last,outcome='CLEAN').count()==1
assert SecureScanAttempt.objects.filter(upload=last).count()==1
assert SecureCleanObject.objects.filter(upload=last).count()==1
assert SecureHRReview.objects.filter(clean__upload=last,decision='ACCEPTED').count()==1
assert TaskCompletion.objects.filter(task=task,evidence_type='SECURE_DOCUMENT').count()==1
assert task.execution_state=='COMPLETED' and successor.execution_state=='READY'
assert AuditEvent.objects.filter(event_type='DOCUMENT_UPLOAD_INTENT_SUPERSEDED',
    entity_id=task.pk).count()==1
assert AuditEvent.objects.filter(event_type='DOCUMENT_QUARANTINED',
    entity_id=task.pk).count()==1
assert AuditEvent.objects.filter(event_type='TASK_COMPLETED',entity_id=task.pk).exists()
assert CommandReceipt.objects.filter(case_id=cid,route='m3-secure-receive').count()==1
with connection.cursor() as cur:
    cur.execute("SELECT status FROM procrastinate_jobs WHERE task_name=%s AND args->>'upload_id'=%s",
        ['m3.secure_document_scan',str(last.pk)])
    queue=cur.fetchall()
assert queue==[('succeeded',)],queue
stored=StoredQuarantineObject.objects.get(upload=last)
s3=storage.client()
q,clean=storage.buckets(s3)
response=s3.list_object_versions(Bucket=q,Prefix=last.object_key)
versions=[v for v in response.get('Versions',[]) if v['Key']==last.object_key]
assert len(versions)==1 and versions[0]['VersionId']==stored.version_id,versions
assert storage.read_exact(q,last.object_key,stored.version_id,last.sha256)==Path(
    os.environ['M3_LIVE_BROWSER_VALID_PDF']).read_bytes()
clean_obj=SecureCleanObject.objects.get(upload=last)
assert storage.download(clean_obj)==Path(os.environ['M3_LIVE_BROWSER_VALID_PDF']).read_bytes()
assert not s3.list_object_versions(Bucket=q,Prefix=first.object_key).get('Versions')
print('M3_R2_LIVE_BROWSER_HARD_EXIT_RECOVERY_PASS: 2 intents, 1 actual S3 version, '
      '1 receipt, 1 committed job and clean scan, independent HR completion')
