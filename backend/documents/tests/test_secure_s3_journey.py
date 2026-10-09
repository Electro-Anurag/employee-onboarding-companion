"""End-to-end M3 S3 document evidence saga against PostgreSQL, isolated service doubles.

Real S3 and clamd integration is separately mandatory; these tests alone
do not prove deployed scanner/storage reliability.
"""
import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock
from botocore.exceptions import ClientError
import io
import json
import time
import uuid
from unittest.mock import patch
import pytest
from django.db import DatabaseError,transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client,override_settings
from pypdf import PdfWriter
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.onboarding.commands import activate_case
from backend.onboarding.models import OnboardingCase,Task,TaskCompletion
from backend.onboarding.services import CommandFailure
from backend.documents.real_models import (SecureUpload,StoredQuarantineObject,
    SecureCleanObject,SecureScanAttempt,SecureHRReview)
from backend.documents.real_commands import prepare,receive,scan_one,review
from backend.documents.pdf_validation import validate_pdf
from backend.audit.models import AuditEvent,CommandReceipt

def generated_pdf():
    file=io.BytesIO()
    writer=PdfWriter()
    writer.add_blank_page(width=300,height=300)
    writer.write(file)
    return file.getvalue()

@pytest.fixture
def s3_doubles():
    from backend.documents import storage
    with (override_settings(M3_REAL_DOCUMENT_ENABLED=True,
            M3_S3_QUARANTINE_BUCKET='ci-quarantine',
            M3_S3_CLEAN_BUCKET='ci-clean',
            M3_S3_ENDPOINT_URL='http://127.0.0.1:9000',
            M3_S3_ALLOW_LOCAL_TEST_ENDPOINT=True),
          patch.object(storage,'client',return_value=object()),
          patch.object(storage,'buckets',return_value=('ci-quarantine','ci-clean')),
          patch.object(storage,'put_quarantine',return_value='versioned-original-1'),
          patch.object(storage,'promote',return_value=('clean/case/doc.pdf','versioned-clean-1')),
          patch.object(storage,'read_exact',side_effect=lambda *args,**kwargs:generated_pdf()),
          patch.object(storage,'download',side_effect=lambda clean:generated_pdf())):
        yield

@pytest.mark.django_db(transaction=True)
def test_m3_s3_complete_clean_document_hr_acceptance_unlocks_only_real_dependencies(world,s3_doubles):
    org,people=world
    created,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=created['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,
        key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    equipment=Task.objects.get(case=case,key='equipment_setup')
    assert task.execution_state=='READY' and equipment.execution_state=='BLOCKED'
    raw=generated_pdf()
    sha=hashlib.sha256(raw).hexdigest()
    base=dict(actor=people['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        sha256=sha,size=len(raw),filename='generated_identity.pdf',expected_version=2)
    with pytest.raises(CommandFailure) as unauthorized:
        prepare(**{**base,'actor':people['MANAGER'][0]},key=uuid.uuid4())
    assert unauthorized.value.code=='NOT_FOUND'
    intent_key=uuid.uuid4()
    intent,status=prepare(**base,key=intent_key)
    assert status==201 and intent['result']['revision']==1
    assert prepare(**base,key=intent_key)[0]==intent
    assert Task.objects.get(pk=task.pk).execution_state=='READY'
    upload_id=uuid.UUID(intent['result']['upload_id'])
    with pytest.raises(CommandFailure) as wrong_sha:
        receive(actor=people['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
            upload_id=upload_id,raw=raw+b'altered',
            key=uuid.uuid4(),expected_version=3)
    assert wrong_sha.value.code=='UPLOAD_CONTENT_MISMATCH'
    receive_key=uuid.uuid4()
    stored,status=receive(actor=people['EMPLOYEE'][0],case_id=case.pk,
        task_id=task.pk,upload_id=upload_id,raw=raw,key=receive_key,
        expected_version=3)
    assert status==201 and stored['result']['state']=='QUARANTINED'
    # Exact replay cannot issue a second put_object or scan job.
    assert receive(actor=people['EMPLOYEE'][0],case_id=case.pk,
        task_id=task.pk,upload_id=upload_id,raw=raw,key=receive_key,
        expected_version=3)==(stored,201)
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    assert TaskCompletion.objects.count()==0
    result=scan_one(upload_id,scanner=lambda data:('CLEAN','real-service-response-simulated'))
    assert result['state']=='AWAITING_HR_REVIEW'
    clean=SecureCleanObject.objects.get(upload_id=upload_id)
    assert clean.version_id=='versioned-clean-1'
    assert SecureScanAttempt.objects.get(upload_id=upload_id).outcome=='CLEAN'
    assert scan_one(upload_id)['state']=='AWAITING_HR_REVIEW'
    with pytest.raises(CommandFailure) as forbidden:
        review(actor=people['IT'][0],case_id=case.pk,task_id=task.pk,
            upload_id=upload_id,decision='ACCEPTED',note='Unauthorized review',
            key=uuid.uuid4(),expected_version=4)
    assert forbidden.value.code=='NOT_FOUND'
    confirmed,status=review(actor=people['HR'][0],case_id=case.pk,
        task_id=task.pk,upload_id=upload_id,decision='ACCEPTED',
        note='Verified exact clean S3 object and synthetic employee consent',
        key=uuid.uuid4(),expected_version=4)
    assert status==201 and confirmed['result']['task_completion']=='COMPLETED'
    completion=TaskCompletion.objects.get(task=task)
    assert completion.evidence_type=='SECURE_DOCUMENT'
    assert completion.secure_review.clean_id==clean.id
    assert completion.evidence_hash==sha
    assert Task.objects.get(pk=task.pk).execution_state=='COMPLETED'
    # Historical receipt remains replayable even after case version and
    # evidence state have advanced; the object is never overwritten.
    assert receive(actor=people['EMPLOYEE'][0],case_id=case.pk,
        task_id=task.pk,upload_id=upload_id,raw=raw,key=receive_key,
        expected_version=3)==(stored,201)
    assert Task.objects.get(pk=equipment.pk).execution_state=='BLOCKED'
    assert OnboardingCase.objects.get(pk=case.pk).version==5
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            SecureHRReview.objects.filter(pk=completion.secure_review_id).update(
                decision='REJECTED')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            SecureUpload.objects.filter(pk=upload_id).update(sha256='0'*64)
    assert AuditEvent.objects.filter(event_type='DOCUMENT_SECURE_REVIEWED').count()==1
    assert CommandReceipt.objects.filter(route='m3-secure-prepare').count()==1

@pytest.mark.django_db(transaction=True)
def test_m3_s3_malware_cannot_be_reviewed_and_allows_fresh_revision(world,s3_doubles):
    org,people=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    raw=generated_pdf()
    sha=hashlib.sha256(raw).hexdigest()
    first,_=prepare(actor=people['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        sha256=sha,size=len(raw),filename='anonymized_example.pdf',
        key=uuid.uuid4(),expected_version=2)
    upload_id=uuid.UUID(first['result']['upload_id'])
    receive(actor=people['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        upload_id=upload_id,raw=raw,key=uuid.uuid4(),expected_version=3)
    scan=scan_one(upload_id,scanner=lambda content:('MALWARE','EICAR test signature found'))
    assert scan['state']=='REJECTED_SECURITY'
    assert not SecureCleanObject.objects.exists()
    with pytest.raises(CommandFailure) as forbidden:
        review(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
            upload_id=upload_id,decision='ACCEPTED',note='Cannot accept infected',
            key=uuid.uuid4(),expected_version=4)
    assert forbidden.value.code=='CLEAN_SCAN_REQUIRED'
    assert TaskCompletion.objects.count()==0
    replacement,_=prepare(actor=people['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        sha256=sha,size=len(raw),filename='replacement_generated.pdf',
        key=uuid.uuid4(),expected_version=4)
    assert replacement['result']['revision']==2
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'

@pytest.mark.django_db(transaction=True)
def test_m3_s3_http_private_download_and_employee_content_auth(world,s3_doubles):
    org,people=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,
        key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    base=f'/api/v1/cases/{case.pk}/tasks/{task.pk}/secure-documents'
    def client(role):
        c=Client()
        c.force_login(people[role][0])
        ses=c.session;ses['m1_session_started']=time.time();ses.save()
        return c
    employee=client('EMPLOYEE')
    hr=client('HR')
    it=client('IT')
    assert employee.get(base).status_code==200
    assert it.get(base).status_code==404
    raw=generated_pdf()
    prep=employee.post(base+'/prepare',
        data=json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),
                         'size':len(raw),'filename':'generated_demo.pdf'}),
        content_type='application/json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v2"')
    assert prep.status_code==201,prep.content
    ident=prep.json()['result']['upload_id']
    path=base+'/'+ident+'/content'
    forbidden=hr.post(path,data={'file':SimpleUploadedFile('generated_demo.pdf',raw,
        content_type='application/pdf')},HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v3"')
    assert forbidden.status_code==404
    stored=employee.post(path,data={'file':SimpleUploadedFile('generated_demo.pdf',raw,
        content_type='application/pdf')},HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v3"')
    assert stored.status_code==201,stored.content
    assert employee.get(base).json()['results'][0]['state']=='QUARANTINED'
    assert employee.get(base+'/'+ident+'/download').status_code==404
    scan_one(uuid.UUID(ident),scanner=lambda data:('CLEAN','synthetic fixed response'))
    download=hr.get(base+'/'+ident+'/download')
    assert download.status_code==200 and download.content==raw
    assert download.headers['Cache-Control']=='private, no-store'
    assert download.headers['Content-Security-Policy']=='sandbox'
    assert it.get(base+'/'+ident+'/download').status_code==404
    reviewed=hr.post(base+'/'+ident+'/review',
        data=json.dumps({'decision':'ACCEPTED','note':'Approved generated PDF'}),
        content_type='application/json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v4"')
    assert reviewed.status_code==201,reviewed.content
    assert TaskCompletion.objects.get(task=task).evidence_type=='SECURE_DOCUMENT'

def test_m3_generated_pdf_validator_rejects_bad_and_active_content():
    valid=generated_pdf()
    assert validate_pdf(valid) is None
    with pytest.raises(CommandFailure):
        validate_pdf(b'%PDF-1.4\\nNOT A PDF\\n%%EOF\\n'.replace(b'\\n',b'\n'))

def test_storage_recovers_only_matching_precondition_conflict_and_exact_bytes():
    from backend.documents import storage
    payload=generated_pdf()
    sha=hashlib.sha256(payload).hexdigest()
    upload=SimpleNamespace(object_key='quarantine/org/case/object.pdf',
        byte_length=len(payload),sha256=sha)
    error=ClientError({'Error':{'Code':'PreconditionFailed'},
        'ResponseMetadata':{'HTTPStatusCode':412}},'PutObject')
    s3=MagicMock()
    s3.put_object.side_effect=error
    s3.head_object.return_value={'VersionId':'previous-stored-version'}
    with (override_settings(M3_REAL_DOCUMENT_ENABLED=True,
            M3_S3_QUARANTINE_BUCKET='quarantine',M3_S3_CLEAN_BUCKET='clean',
            M3_S3_ENDPOINT_URL='http://127.0.0.1:9000',
            M3_S3_ALLOW_LOCAL_TEST_ENDPOINT=True),
          patch.object(storage,'client',return_value=s3),
          patch.object(storage,'buckets',return_value=('quarantine','clean')),
          patch.object(storage,'read_exact',return_value=payload) as checked):
        recovered=storage.put_quarantine(upload,payload)
        assert recovered=='previous-stored-version'
        checked.assert_called_once_with('quarantine',upload.object_key,
            'previous-stored-version',sha)
        s3.head_object.assert_called_once_with(Bucket='quarantine',
            Key=upload.object_key)
        with patch.object(storage,'read_exact',
                          side_effect=CommandFailure('OBJECT_INTEGRITY_FAILED',409)):
            with pytest.raises(CommandFailure) as denied:
                storage.put_quarantine(upload,payload)
            assert denied.value.code=='OBJECT_INTEGRITY_FAILED'
        s3.put_object.side_effect=ClientError(
            {'Error':{'Code':'AccessDenied'},'ResponseMetadata':{'HTTPStatusCode':403}},
            'PutObject')
        with pytest.raises(CommandFailure) as no_recovery:
            storage.put_quarantine(upload,payload)
        assert no_recovery.value.code=='QUARANTINE_WRITE_FAILED'
