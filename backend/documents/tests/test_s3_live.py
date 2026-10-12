"""Live S3-versioning and actual clamd qualification (never runs without services).

This uses generated PDFs and the standard EICAR anti-malware test signature,
not real employee data. A healthy actual ClamAV daemon is REQUIRED.
"""
import hashlib
import os
import uuid
import io
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject,NameObject
from django.conf import settings
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.onboarding.commands import activate_case
from backend.onboarding.models import Task,OnboardingCase,TaskCompletion
from backend.documents.tests.test_secure_s3_journey import generated_pdf
from backend.documents.real_commands import prepare,receive,scan_one,review
from backend.documents.real_models import SecureCleanObject,SecureScanAttempt
from backend.documents import storage
from backend.documents.scanner import clamav_signature_provenance

pytestmark=pytest.mark.skipif(os.getenv('M3_LIVE_S3_CLAMAV')!='1',
    reason='Requires live versioned MinIO/S3 and ClamAV daemon')

EICAR=(b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$'
       b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')

@pytest.mark.django_db(transaction=True)
def test_live_s3_exact_versions_and_actual_antivirus_rejection_then_hr_approval(world):
    org,actors=world
    assert settings.M3_REAL_DOCUMENT_ENABLED
    assert clamav_signature_provenance().startswith('ClamAV ')
    s3=storage.client()
    q,clean=storage.buckets(s3)
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    equipment=Task.objects.get(case=case,key='equipment_setup')
    assert equipment.execution_state=='BLOCKED'
    raw=generated_pdf()
    # ClamAV does not reliably scan PDF comments. Place the contiguous
    # standard EICAR bytes in an uncompressed PDF page-content stream.
    # Keep the strict PDF parser enabled and the document structurally valid.
    infected=io.BytesIO()
    writer=PdfWriter()
    page=writer.add_blank_page(width=300,height=300)
    marker=DecodedStreamObject()
    marker.set_data(EICAR)
    page[NameObject('/Contents')]=writer._add_object(marker)
    writer.write(infected)
    attack=infected.getvalue()
    assert attack.count(EICAR)==1
    # Must still be a well-formed PDF for the scanner security gate.
    from backend.documents.pdf_validation import validate_pdf
    validate_pdf(attack)
    v1,_=prepare(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        sha256=hashlib.sha256(attack).hexdigest(),size=len(attack),
        filename='eicar_generated.pdf',key=uuid.uuid4(),expected_version=2)
    id1=uuid.UUID(v1['result']['upload_id'])
    received,_=receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        upload_id=id1,raw=attack,key=uuid.uuid4(),expected_version=3)
    assert received['result']['state']=='QUARANTINED'
    assert not SecureCleanObject.objects.filter(upload_id=id1).exists()
    malicious=scan_one(id1)
    assert malicious['state']=='REJECTED_SECURITY',malicious
    assert SecureScanAttempt.objects.get(upload_id=id1).outcome=='MALWARE'
    assert TaskCompletion.objects.count()==0
    normal,_=prepare(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
        filename='generated_replacement.pdf',key=uuid.uuid4(),expected_version=4)
    id2=uuid.UUID(normal['result']['upload_id'])
    received,_=receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        upload_id=id2,raw=raw,key=uuid.uuid4(),expected_version=5)
    assert received['result']['state']=='QUARANTINED'
    # Exercise actual S3 412 recovery using the immutable object version.
    from backend.documents.real_models import SecureUpload,StoredQuarantineObject
    same=storage.put_quarantine(SecureUpload.objects.get(pk=id2),raw)
    assert same==StoredQuarantineObject.objects.get(upload_id=id2).version_id
    clean_result=scan_one(id2)
    assert clean_result['state']=='AWAITING_HR_REVIEW',clean_result
    obj=SecureCleanObject.objects.get(upload_id=id2)
    assert obj.version_id and obj.version_id!='null'
    assert storage.download(obj)==raw
    assert s3.head_object(Bucket=clean,Key=obj.object_key,VersionId=obj.version_id)['ContentLength']==len(raw)
    accepted,_=review(actor=actors['HR'][0],case_id=case.pk,task_id=task.pk,
        upload_id=id2,decision='ACCEPTED',note='Real scanner and exact S3 version qualified',
        key=uuid.uuid4(),expected_version=6)
    assert accepted['result']['task_completion']=='COMPLETED'
    assert TaskCompletion.objects.get(task=task).evidence_type=='SECURE_DOCUMENT'
    assert Task.objects.get(pk=equipment.pk).execution_state=='BLOCKED'
    assert not SecureCleanObject.objects.filter(upload_id=id1).exists()

@pytest.mark.django_db(transaction=True)
def test_live_s3_receive_hard_exit_after_object_put_recovers_same_upload_intent(world):
    """Real MinIO persisted PUT + process hard exit; resume without duplicate evidence."""
    import subprocess
    import sys
    from pathlib import Path
    from django.db import connection
    from backend.audit.models import AuditEvent, CommandReceipt
    from backend.documents.real_models import SecureUpload, StoredQuarantineObject

    _,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    raw=generated_pdf()
    intent,_=prepare(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
                     sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
                     filename='crash_recovery.pdf',key=uuid.uuid4(),expected_version=2)
    upload_id=uuid.UUID(intent['result']['upload_id'])
    upload=SecureUpload.objects.get(pk=upload_id)
    receive_key=uuid.uuid4()
    worker_code="""
import os,sys,django
django.setup()
from backend.accounts.models import User
from backend.documents.real_commands import receive
from uuid import UUID
receive(actor=User.objects.get(pk=UUID(sys.argv[1])),
        case_id=UUID(sys.argv[2]),task_id=UUID(sys.argv[3]),
        upload_id=UUID(sys.argv[4]),raw=sys.stdin.buffer.read(),
        key=UUID(sys.argv[5]),expected_version=3)
"""
    env=os.environ.copy()
    env['POSTGRES_DB']=connection.settings_dict['NAME']
    env['M3_CI_CRASH_AFTER_PUT']='1'
    # This crash switch is restricted by production code to loopback:9000.
    child=subprocess.run(
        [sys.executable,'-c',worker_code,str(actors['EMPLOYEE'][0].pk),
         str(case.pk),str(task.pk),str(upload_id),str(receive_key)],
        cwd=str(Path(__file__).resolve().parents[3]),input=raw,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=40,env=env)
    assert child.returncode==79,child.stderr[-1200:].decode('utf-8','replace')
    s3=storage.client()
    quarantine,_=storage.buckets(s3)
    original=s3.head_object(Bucket=quarantine,Key=upload.object_key)
    original_version=original['VersionId']
    assert original_version and original_version!='null'
    assert not StoredQuarantineObject.objects.filter(upload=upload).exists()
    assert not CommandReceipt.objects.filter(route='m3-secure-receive').exists()
    assert not AuditEvent.objects.filter(event_type='DOCUMENT_QUARANTINED').exists()
    assert OnboardingCase.objects.get(pk=case.pk).version==3

    # Resume the SAME intent and command key; do not create a replacement or
    # silently repeat the successful S3 write. Storage SHA/version are checked.
    resumed,code=receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,
                         task_id=task.pk,upload_id=upload_id,raw=raw,
                         key=receive_key,expected_version=3)
    assert code==201 and resumed['result']['state']=='QUARANTINED'
    stored=StoredQuarantineObject.objects.get(upload=upload)
    assert stored.version_id==original_version
    assert OnboardingCase.objects.get(pk=case.pk).version==4
    assert receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,
                   task_id=task.pk,upload_id=upload_id,raw=raw,
                   key=receive_key,expected_version=3)==(resumed,201)
    versions=s3.list_object_versions(Bucket=quarantine,Prefix=upload.object_key)
    exact=[v for v in versions.get('Versions',[]) if v['Key']==upload.object_key]
    assert len(exact)==1 and exact[0]['VersionId']==original_version
    assert CommandReceipt.objects.filter(route='m3-secure-receive').count()==1
    assert AuditEvent.objects.filter(event_type='DOCUMENT_QUARANTINED').count()==1
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM procrastinate_jobs "
            "WHERE task_name=%s AND args->>'upload_id'=%s",
            ['m3.secure_document_scan',str(upload_id)])
        assert cursor.fetchone()[0]==1
    assert not TaskCompletion.objects.filter(task=task).exists()


@pytest.mark.django_db(transaction=True)
def test_live_clamav_daemon_pause_and_recovery_keeps_quarantine_unreleased(world):
    """Actual clamd outage: no clean/HR evidence until the same daemon recovers."""
    import subprocess
    _,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    raw=generated_pdf()
    intent,_=prepare(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
                     sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
                     filename='scanner_outage.pdf',key=uuid.uuid4(),expected_version=2)
    upload_id=uuid.UUID(intent['result']['upload_id'])
    receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
            upload_id=upload_id,raw=raw,key=uuid.uuid4(),expected_version=3)
    assert clamav_signature_provenance().startswith('ClamAV ')
    subprocess.run(['docker','pause','m3-clamd'],check=True,
                   capture_output=True,timeout=15)
    try:
        interrupted=scan_one(upload_id)
        assert interrupted=={'outcome':'ERROR','state':'SCAN_FAILED'}
        assert SecureScanAttempt.objects.filter(
            upload_id=upload_id,outcome='ERROR').count()==1
        assert not SecureCleanObject.objects.filter(upload_id=upload_id).exists()
        assert not TaskCompletion.objects.filter(task=task).exists()
    finally:
        # Never leave the scanner stopped if an assertion raises; cleanup
        # in the workflow is an additional independent last resort.
        subprocess.run(['docker','unpause','m3-clamd'],check=True,
                       capture_output=True,timeout=15)
    assert clamav_signature_provenance().startswith('ClamAV ')
    recovered=scan_one(upload_id)
    assert recovered=={'outcome':'CLEAN','state':'AWAITING_HR_REVIEW'}
    assert list(SecureScanAttempt.objects.filter(upload_id=upload_id)
                .order_by('number').values_list('outcome',flat=True))==['ERROR','CLEAN']
    assert SecureCleanObject.objects.filter(upload_id=upload_id).count()==1
    assert scan_one(upload_id)==recovered
    assert SecureScanAttempt.objects.filter(upload_id=upload_id).count()==2
    assert not TaskCompletion.objects.filter(task=task).exists()


@pytest.mark.django_db(transaction=True)
def test_live_clean_copy_committed_before_db_failure_is_reused_exactly(world):
    """Real clean S3 copy survives a failed finalization without creating a second version."""
    from unittest.mock import patch
    from backend.documents.real_models import SecureUpload,StoredQuarantineObject
    _,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    raw=generated_pdf()
    intent,_=prepare(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
                     sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
                     filename='promotion_recovery.pdf',key=uuid.uuid4(),expected_version=2)
    upload_id=uuid.UUID(intent['result']['upload_id'])
    receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
            upload_id=upload_id,raw=raw,key=uuid.uuid4(),expected_version=3)
    upload=SecureUpload.objects.get(pk=upload_id)
    original_promotion=storage.promote
    captured=[]
    def lose_receipt_after_real_copy(upload,version):
        captured.append(original_promotion(upload,version))
        raise OSError('CI-only failure after real clean S3 commit')
    with patch.object(storage,'promote',side_effect=lose_receipt_after_real_copy):
        first=scan_one(upload_id)
    assert first=={'outcome':'CLEAN','state':'PROMOTION_PENDING'}
    assert len(captured)==1
    assert not SecureCleanObject.objects.filter(upload_id=upload_id).exists()
    assert SecureScanAttempt.objects.filter(upload_id=upload_id,outcome='CLEAN').count()==1
    recovered=scan_one(upload_id)
    assert recovered=={'outcome':'CLEAN','state':'AWAITING_HR_REVIEW'}
    clean=SecureCleanObject.objects.get(upload_id=upload_id)
    assert (clean.object_key,clean.version_id)==captured[0]
    s3=storage.client()
    _,bucket=storage.buckets(s3)
    versions=s3.list_object_versions(Bucket=bucket,Prefix=clean.object_key)
    exact=[v for v in versions.get('Versions',[]) if v['Key']==clean.object_key]
    assert len(exact)==1 and exact[0]['VersionId']==clean.version_id
    assert storage.download(clean)==raw
    assert scan_one(upload_id)==recovered
    assert SecureScanAttempt.objects.filter(upload_id=upload_id).count()==1
    assert not TaskCompletion.objects.filter(task=task).exists()


@pytest.mark.django_db(transaction=True)
def test_live_private_quarantine_and_clean_versions_deny_anonymous_get(world):
    """Real MinIO object versions must not be readable without S3 credentials."""
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    from botocore.exceptions import ClientError
    from backend.documents.real_models import SecureUpload,StoredQuarantineObject
    _,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    raw=generated_pdf()
    intent,_=prepare(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
                     sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
                     filename='private_access.pdf',key=uuid.uuid4(),expected_version=2)
    upload_id=uuid.UUID(intent['result']['upload_id'])
    receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
            upload_id=upload_id,raw=raw,key=uuid.uuid4(),expected_version=3)
    assert scan_one(upload_id)=={'outcome':'CLEAN','state':'AWAITING_HR_REVIEW'}
    upload=SecureUpload.objects.get(pk=upload_id)
    stored=StoredQuarantineObject.objects.get(upload=upload)
    clean=SecureCleanObject.objects.get(upload=upload)
    signed=storage.client()
    q,c=storage.buckets(signed)
    assert storage.download(clean)==raw
    anonymous=boto3.client(
        's3',endpoint_url=settings.M3_S3_ENDPOINT_URL,
        region_name=settings.M3_S3_REGION,
        config=Config(signature_version=UNSIGNED,s3={'addressing_style':'path'}))
    for bucket,key,version in ((q,upload.object_key,stored.version_id),
                               (c,clean.object_key,clean.version_id)):
        with pytest.raises(ClientError) as denied:
            anonymous.get_object(Bucket=bucket,Key=key,VersionId=version)
        assert denied.value.response.get('ResponseMetadata',{}).get(
            'HTTPStatusCode') in (403,404)
    assert not TaskCompletion.objects.filter(task=task).exists()


@pytest.mark.django_db(transaction=True)
def test_live_m3_real_content_worker_hard_exit_redelivery(world):
    """Actual worker dies after committed clean evidence, before ACK; retry is idempotent."""
    import asyncio
    import subprocess
    import sys
    import time
    from pathlib import Path
    from django.db import connection
    from procrastinate.contrib.django import app
    org,actors=world
    assert clamav_signature_provenance().startswith('ClamAV ')
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    raw=generated_pdf()
    intent,_=prepare(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
        filename='actual_worker_recovery.pdf',key=uuid.uuid4(),expected_version=2)
    ident=uuid.UUID(intent['result']['upload_id'])
    receive(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        upload_id=ident,raw=raw,key=uuid.uuid4(),expected_version=3)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM procrastinate_jobs WHERE task_name=%s AND args->>'upload_id'=%s",
            ['m3.secure_document_scan',str(ident)])
        rows=cursor.fetchall()
    assert len(rows)==1
    job_id=rows[0][0]
    def job_status():
        connection.close()
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM procrastinate_jobs WHERE id=%s",[job_id])
            return cursor.fetchone()[0]
    def start_worker(crash):
        env=os.environ.copy()
        env['POSTGRES_DB']=connection.settings_dict['NAME']
        env['PGAPPNAME']='eoc_m3_worker_crash' if crash else 'eoc_m3_worker_recovery'
        if crash:env['M3_CI_CRASH_AFTER_SCAN']='1'
        else:env.pop('M3_CI_CRASH_AFTER_SCAN',None)
        return subprocess.Popen([sys.executable,'manage.py','procrastinate','worker'],
            cwd=str(Path(__file__).resolve().parents[3]),env=env,
            stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    def close_worker(worker):
        if worker.poll() is None:
            worker.terminate()
            try:worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()
    first=start_worker(True)
    try:
        first.wait(timeout=40)
        assert first.returncode==77, 'Expected exact M3 worker post-commit hard exit'
    finally:
        close_worker(first)
    assert SecureScanAttempt.objects.filter(upload_id=ident,outcome='CLEAN').count()==1
    assert SecureCleanObject.objects.filter(upload_id=ident).count()==1
    assert not TaskCompletion.objects.filter(task=task).exists()
    assert job_status()=='doing'
    time.sleep(3)
    async def recover():
        async with app.open_async():
            stalled=await app.job_manager.get_stalled_jobs(seconds_since_heartbeat=2)
            selected=[job for job in stalled
                if job.id==job_id and job.task_name=='m3.secure_document_scan']
            assert len(selected)==1
            await app.job_manager.retry_job(selected[0])
    asyncio.run(recover())
    assert job_status()=='todo'
    second=start_worker(False)
    try:
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            if job_status()=='succeeded':break
            if second.poll() is not None:
                raise AssertionError('Restarted M3 worker exited before ACK')
            time.sleep(.3)
        assert job_status()=='succeeded'
    finally:
        close_worker(second)
    assert SecureScanAttempt.objects.filter(upload_id=ident).count()==1
    assert SecureCleanObject.objects.filter(upload_id=ident).count()==1
    assert not TaskCompletion.objects.filter(task=task).exists()
    accepted,_=review(actor=actors['HR'][0],case_id=case.pk,task_id=task.pk,
        upload_id=ident,decision='ACCEPTED',note='Verified replay after worker hard exit',
        key=uuid.uuid4(),expected_version=4)
    assert accepted['result']['task_completion']=='COMPLETED'
    assert TaskCompletion.objects.filter(task=task,evidence_type='SECURE_DOCUMENT').count()==1
    # Diagnose the observed Django test database teardown warning. Only
    # PostgreSQL session metadata is logged, never query text or credentials.
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT pid, state, backend_type, application_name, client_port
            FROM pg_stat_activity
            WHERE datname=current_database() AND pid<>pg_backend_pid()
            ORDER BY pid
        """)
        sessions=cursor.fetchall()
    print('M3_POST_WORKER_PG_SESSIONS='+repr(sessions),flush=True)
    # Identify only local test DB TCP socket ownership. No process arguments,
    # SQL text, environment or credentials are emitted.
    try:
        socket_list=subprocess.run(['ss','-tnpH'],check=False,
                                   capture_output=True,text=True,timeout=5)
        owners=[]
        for session in sessions:
            client_port=session[-1]
            owners.extend(line for line in socket_list.stdout.splitlines()
                          if client_port and ':'+str(client_port) in line)
        print('M3_POST_WORKER_SOCKET_OWNERS='+repr(owners),flush=True)
    except (OSError,subprocess.TimeoutExpired):
        print('M3_POST_WORKER_SOCKET_OWNERS=UNAVAILABLE',flush=True)
