"""Document evidence security, correction, authoritative completion, and HTTP access.

This slice only accepts exact synthetic test fixtures; these tests do not
qualify a general antivirus scanner or production object storage.
"""
import uuid
import time
from django.db import DatabaseError,transaction
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
import pytest
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.onboarding.models import OnboardingCase,Task,TaskCompletion
from backend.onboarding.commands import activate_case
from backend.onboarding.services import CommandFailure
from backend.documents.commands import upload,review
from backend.documents.models import DocumentRevision,DocumentReview
from backend.documents.fixtures import FIXTURES
from backend.audit.models import AuditEvent,CommandReceipt

@pytest.mark.django_db(transaction=True)
def test_synthetic_upload_reject_replace_accept_and_dependency_unlock(world):
    org,people=world
    created,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=created['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='identity_document')
    assert task.execution_state=='READY'
    equipment=Task.objects.get(case=case,key='equipment_setup')
    assert equipment.execution_state=='BLOCKED'
    raw=FIXTURES['identity_document']
    args=dict(actor=people['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
              raw=raw,expected_version=2)
    with pytest.raises(CommandFailure) as bad_upload:
        upload(**{**args,'raw':b'ACTUAL PASSPORT DATA'},key=uuid.uuid4())
    assert bad_upload.value.code=='SYNTHETIC_FIXTURE_ONLY'
    with pytest.raises(CommandFailure):
        upload(**{**args,'actor':people['IT'][0]},key=uuid.uuid4())
    assert DocumentRevision.objects.count()==0
    key=uuid.uuid4()
    first,code=upload(**args,key=key)
    assert code==201 and first['result']['revision']==1
    assert first['result']['malware_scanned'] is False
    assert upload(**args,key=key)[0]==first
    assert OnboardingCase.objects.get(pk=case.pk).version==3
    with pytest.raises(CommandFailure) as pending:
        upload(**{**args,'expected_version':3},key=uuid.uuid4())
    assert pending.value.code=='DOCUMENT_REVIEW_PENDING_OR_ACCEPTED'
    first_id=uuid.UUID(first['result']['document_revision_id'])
    rejected,status=review(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
        revision_id=first_id,decision='REJECTED',note='Replace the synthetic demo revision',
        key=uuid.uuid4(),expected_version=3)
    assert status==201 and rejected['result']['task_completion']=='PENDING_CORRECTION'
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    second,code=upload(**{**args,'expected_version':4},key=uuid.uuid4())
    assert code==201 and second['result']['revision']==2
    with pytest.raises(CommandFailure) as superseded:
        review(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
            revision_id=first_id,decision='ACCEPTED',note='stale review',
            key=uuid.uuid4(),expected_version=5)
    assert superseded.value.code=='NOT_FOUND'
    second_id=uuid.UUID(second['result']['document_revision_id'])
    final,status=review(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
        revision_id=second_id,decision='ACCEPTED',note='Exact synthetic bytes verified',
        key=uuid.uuid4(),expected_version=5)
    assert status==201 and final['result']['task_completion']=='COMPLETED'
    assert OnboardingCase.objects.get(pk=case.pk).version==6
    assert Task.objects.get(pk=task.pk).execution_state=='COMPLETED'
    completion=TaskCompletion.objects.get(task=task)
    assert completion.evidence_type=='DOCUMENT'
    assert completion.document_review.revision_id==second_id
    assert DocumentRevision.objects.filter(task=task).count()==2
    assert DocumentReview.objects.filter(revision__task=task).count()==2
    # The other AND prerequisite remains incomplete; document alone must not unlock IT.
    assert Task.objects.get(pk=equipment.pk).execution_state=='BLOCKED'
    assert DocumentRevision.objects.get(pk=first_id).content == raw
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            DocumentRevision.objects.filter(pk=second_id).update(content=b'tamper')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            DocumentReview.objects.filter(pk=completion.document_review_id).update(decision='REJECTED')
    assert CommandReceipt.objects.filter(route='m3-document-upload').count()==2
    assert AuditEvent.objects.filter(event_type='SYNTHETIC_DOCUMENT_REVIEWED').count()==2

@pytest.mark.django_db(transaction=True)
def test_synthetic_document_http_multipart_scope_sample_and_private_download(world):
    org,people=world
    created,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=created['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
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
    assert it.get(base+'/document-revisions').status_code==404
    assert it.get(base+'/document-sample').status_code==404
    sample=employee.get(base+'/document-sample')
    assert sample.status_code==200 and sample.content==FIXTURES['identity_document']
    assert sample.headers['Cache-Control']=='private, no-store'
    unsafe=SimpleUploadedFile('real_private.txt',b'IDENTITY REAL',content_type='text/plain')
    wrong=employee.post(base+'/document-revisions',data={'file':unsafe},
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH=f'"case:{case.pk}:v2"')
    assert wrong.status_code==422
    fixture=SimpleUploadedFile('fixture.txt',FIXTURES['identity_document'],content_type='text/plain')
    sent=employee.post(base+'/document-revisions',data={'file':fixture},
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH=f'"case:{case.pk}:v2"')
    assert sent.status_code==201,sent.content
    assert sent.json()['result']['malware_scanned'] is False
    listing=hr.get(base+'/document-revisions')
    assert listing.status_code==200 and listing.json()['results'][0]['review'] is None
    r_id=sent.json()['result']['document_revision_id']
    path=base+'/document-revisions/'+r_id+'/download'
    assert hr.get(path).content==FIXTURES['identity_document']
    assert employee.get(path).content==FIXTURES['identity_document']
    assert it.get(path).status_code==404
    assert Client().get(path).status_code in (401,404)
    responded=hr.post(base+'/document-revisions/'+r_id+'/review',
        data={'decision':'ACCEPTED','note':'Clean synthetic fixed fixture'},
        content_type='application/json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v3"')
    assert responded.status_code==201,responded.content
    assert hr.get(base+'/document-revisions').json()['results'][0]['review']['decision']=='ACCEPTED'
    assert Task.objects.get(pk=task.pk).completion.evidence_type=='DOCUMENT'
