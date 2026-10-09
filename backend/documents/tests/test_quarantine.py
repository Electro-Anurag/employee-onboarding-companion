"""Quarantine is not a document review or an antivirus verdict without ClamAV."""
import hashlib
import struct
import time
import uuid
from unittest.mock import patch
import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError,transaction
from django.test import Client,override_settings
from backend.onboarding.tests.test_m2_workflow import world,create,published
from backend.onboarding.commands import activate_case
from backend.onboarding.models import OnboardingCase,Task,TaskCompletion
from backend.audit.models import CommandReceipt,AuditEvent
from backend.onboarding.services import CommandFailure
from backend.documents.quarantine_models import QuarantinedDocument,QuarantineScanAttempt
from backend.documents.quarantine_commands import submit,scan_upload
from backend.documents.scanner import clamav_scan,ScannerUnavailable

DEMO_PDF=b'%PDF-1.7\\n1 0 obj\\n<< /Type /Catalog >>\\nendobj\\n%%EOF\\n'.replace(b'\\n',b'\n')

@pytest.mark.django_db(transaction=True)
def test_quarantine_intake_disabled_by_default_and_separate_from_synthetic_reviews(world):
    org,people=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    with override_settings(M3_QUARANTINE_INTAKE_ENABLED=False,
                           M3_CLAMAV_HOST='127.0.0.1'):
        with pytest.raises(CommandFailure) as err:
            submit(actor=people['EMPLOYEE'][0],case_id=case.pk,
                task_id=task.pk,raw=DEMO_PDF,declared_type='application/pdf',
                key=uuid.uuid4(),expected_version=2)
        assert err.value.code=='QUARANTINE_INTAKE_DISABLED'
        c=Client()
        c.force_login(people['EMPLOYEE'][0])
        assert c.get(f'/api/v1/cases/{case.pk}/tasks/{task.pk}/quarantine-status').status_code==404
    assert QuarantinedDocument.objects.count()==0
    assert Task.objects.get(pk=task.pk).execution_state=='READY'

@pytest.mark.django_db(transaction=True)
@override_settings(M3_QUARANTINE_INTAKE_ENABLED=True,M3_CLAMAV_HOST='127.0.0.1')
def test_quarantine_failure_then_clean_scan_stays_unreviewable_and_does_not_unlock_tasks(world):
    org,people=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    wrong=dict(actor=people['EMPLOYEE'][0],case_id=case.pk,
             task_id=task.pk,declared_type='application/pdf',expected_version=2)
    with pytest.raises(CommandFailure) as not_pdf:
        submit(**wrong,raw=b'SYNTHETIC DOCUMENT TEXT NOT PDF',key=uuid.uuid4())
    assert not_pdf.value.code=='INVALID_QUARANTINED_UPLOAD'
    with pytest.raises(CommandFailure) as wrong_role:
        submit(**{**wrong,'actor':people['HR'][0]},
            raw=DEMO_PDF,key=uuid.uuid4())
    assert wrong_role.value.code=='NOT_FOUND'
    key=uuid.uuid4()
    saved,status=submit(**wrong,raw=DEMO_PDF,key=key)
    assert status==201 and saved['result']['state']=='QUARANTINED'
    assert saved['result']['malware_scanned'] is False
    assert submit(**wrong,raw=DEMO_PDF,key=key)[0]==saved
    upload=QuarantinedDocument.objects.get(pk=saved['result']['quarantine_id'])
    assert upload.content_sha256==hashlib.sha256(DEMO_PDF).hexdigest()
    assert Task.objects.get(pk=task.pk).execution_state=='READY'
    assert TaskCompletion.objects.count()==0
    assert DocumentReviewCount()==0
    def unavailable(raw):
        assert raw==DEMO_PDF
        raise ScannerUnavailable('SCANNER_UNAVAILABLE')
    first=scan_upload(upload.pk,scanner=unavailable)
    assert first['outcome']=='ERROR' and first['reviewable'] is False
    second=scan_upload(upload.pk,scanner=lambda raw:('CLEAN','mocked scanner OK'))
    assert second['outcome']=='CLEAN' and second['attempt']==2
    again=scan_upload(upload.pk,scanner=lambda raw:('MALWARE','unexpected'))
    assert again==second
    assert QuarantineScanAttempt.objects.filter(upload=upload).count()==2
    assert TaskCompletion.objects.count()==0
    assert Task.objects.get(pk=task.pk).execution_state=='READY'
    assert OnboardingCase.objects.get(pk=case.pk).version==3
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            QuarantinedDocument.objects.filter(pk=upload.pk).update(
                quarantined_bytes=b'corrupted')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            QuarantineScanAttempt.objects.filter(upload=upload).update(outcome='MALWARE')
    assert AuditEvent.objects.filter(event_type='QUARANTINE_UPLOAD_RECEIVED').count()==1
    assert CommandReceipt.objects.filter(route='m3-quarantine-intake').count()==1

def DocumentReviewCount():
    from backend.documents.models import DocumentReview
    return DocumentReview.objects.count()

@pytest.mark.django_db(transaction=True)
@override_settings(M3_QUARANTINE_INTAKE_ENABLED=True,M3_CLAMAV_HOST='127.0.0.1')
def test_quarantine_multipart_api_scoped_without_raw_download(world):
    org,people=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    base=f'/api/v1/cases/{case.pk}/tasks/{task.pk}'
    def client(role):
        c=Client()
        c.force_login(people[role][0])
        session=c.session
        session['m1_session_started']=time.time()
        session.save()
        return c
    employee=client('EMPLOYEE')
    hr=client('HR')
    it=client('IT')
    pdf=SimpleUploadedFile('sample.pdf',DEMO_PDF,content_type='application/pdf')
    r=employee.post(base+'/quarantine-intake',data={'file':pdf},
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v2"')
    assert r.status_code==201,r.content
    assert r.json()['result']['reviewable'] is False
    response=hr.get(base+'/quarantine-status')
    assert response.status_code==200
    data=response.json()
    assert data['release_supported'] is False
    assert len(data['records'])==1
    assert data['records'][0]['scan_attempts']==[]
    assert 'quarantined_bytes' not in response.content.decode()
    assert it.get(base+'/quarantine-status').status_code==404
    assert it.post(base+'/quarantine-intake',
        data={'file':SimpleUploadedFile('a.pdf',DEMO_PDF,content_type='application/pdf')},
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v3"').status_code==404
    assert Task.objects.get(pk=task.pk).execution_state=='READY'

@override_settings(M3_CLAMAV_HOST='127.0.0.1',M3_CLAMAV_PORT=3310)
def test_clamav_instream_requires_exact_result_and_fails_closed():
    class Socket:
        def __init__(self,reply):
            self.reply=reply
            self.sent=bytearray()
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def settimeout(self,value):assert value==2
        def sendall(self,data):self.sent.extend(data)
        def recv(self,n):
            result=self.reply
            self.reply=b''
            return result
    for reply,expected in [(b'stream: OK\0','CLEAN'),
        (b'stream: Eicar-Test-Signature FOUND\0','MALWARE')]:
        fake=Socket(reply)
        with patch('backend.documents.scanner.socket.create_connection',return_value=fake):
            outcome,_=clamav_scan(DEMO_PDF)
        assert outcome==expected
        assert fake.sent.startswith(b'zINSTREAM\0')
        assert fake.sent.endswith(struct.pack('!I',0))
        assert struct.pack('!I',len(DEMO_PDF))+DEMO_PDF in fake.sent
    for reply in [b'stream: ERROR\0',b'unknown',b'',b'stream: OK EXTRA\0']:
        fake=Socket(reply)
        with patch('backend.documents.scanner.socket.create_connection',return_value=fake):
            with pytest.raises(ScannerUnavailable):
                clamav_scan(DEMO_PDF)
    with patch('backend.documents.scanner.socket.create_connection',
               side_effect=OSError('connection refused')):
        with pytest.raises(ScannerUnavailable):
            clamav_scan(DEMO_PDF)
