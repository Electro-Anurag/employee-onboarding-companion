"""Live PostgreSQL M3 form correction-loop and confidentiality regression."""
import json
import uuid
import pytest
from django.test import Client
from django.db import DatabaseError,transaction
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.onboarding.models import OnboardingCase,Task
from backend.onboarding.commands import activate_case
from backend.onboarding.services import CommandFailure
from backend.forms.commands import submit,review
from backend.forms.models import FormSubmission,FormReview
from backend.audit.models import CommandReceipt,AuditEvent

@pytest.mark.django_db(transaction=True)
def test_real_form_revision_rejection_replacement_acceptance_and_replay(world):
    org,persons=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=persons['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='personal_details')
    assert task.execution_state=='READY'
    answers={'preferred_name':'Synthetic Employee','contact_email':'employee@example.test'}
    key=uuid.uuid4()
    with pytest.raises(CommandFailure) as denied:
        submit(actor=persons['IT'][0],case_id=case.pk,task_id=task.pk,
               answers=answers,key=uuid.uuid4(),expected_version=2)
    assert denied.value.code=='NOT_FOUND'
    result,status=submit(actor=persons['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
                         answers=answers,key=key,expected_version=2)
    assert status==201 and result['result']['revision']==1
    assert submit(actor=persons['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
                  answers=answers,key=key,expected_version=2)[0]==result
    assert OnboardingCase.objects.get(pk=case.pk).version==3
    with pytest.raises(CommandFailure) as stale:
        submit(actor=persons['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
               answers=answers,key=uuid.uuid4(),expected_version=2)
    assert stale.value.code=='STALE_VERSION'
    with pytest.raises(CommandFailure) as pending:
        submit(actor=persons['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
               answers=answers,key=uuid.uuid4(),expected_version=3)
    assert pending.value.code=='FORM_REVIEW_PENDING_OR_ACCEPTED'
    first=FormSubmission.objects.get(task=task,revision=1)
    with pytest.raises(CommandFailure) as denied_review:
        review(actor=persons['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
           submission_id=first.pk,decision='ACCEPTED',note='no',
           key=uuid.uuid4(),expected_version=3)
    assert denied_review.value.code=='NOT_FOUND'
    revised,code=review(actor=persons['HR'][0],case_id=case.pk,task_id=task.pk,
           submission_id=first.pk,decision='CHANGES_REQUESTED',note='Use corrected details',
           key=uuid.uuid4(),expected_version=3)
    assert code==201 and revised['result']['decision']=='CHANGES_REQUESTED'
    assert OnboardingCase.objects.get(pk=case.pk).version==4
    corrected={**answers,'preferred_name':'Corrected Synthetic Employee'}
    new,code=submit(actor=persons['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        answers=corrected,key=uuid.uuid4(),expected_version=4)
    assert code==201 and new['result']['revision']==2
    second=FormSubmission.objects.get(task=task,revision=2)
    approved,code=review(actor=persons['HR'][0],case_id=case.pk,task_id=task.pk,
        submission_id=second.pk,decision='ACCEPTED',note='Verified synthetic fields',
        key=uuid.uuid4(),expected_version=5)
    assert code==201 and approved['result']['task_completion']=='NOT_YET_SUPPORTED'
    assert FormSubmission.objects.filter(task=task).count()==2
    assert FormReview.objects.filter(submission__task=task).count()==2
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            FormSubmission.objects.filter(pk=first.pk).update(answers={'preferred_name':'tamper'})
    assert FormSubmission.objects.get(pk=first.pk).answers==answers
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    assert not hasattr(Task.objects.get(pk=task.pk),'completion')
    assert AuditEvent.objects.filter(event_type='FORM_REVIEWED').count()==2
    assert CommandReceipt.objects.filter(route='m3-form-submit').count()==2

@pytest.mark.django_db(transaction=True)
def test_form_api_case_scoped_and_owner_reads(world):
    org,persons=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=persons['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='personal_details')
    path=f'/api/v1/cases/{case.pk}/tasks/{task.pk}/form-submissions'
    employee=Client()
    employee.force_login(persons['EMPLOYEE'][0])
    answers={'preferred_name':'Synthetic Employee','contact_email':'employee@example.test'}
    response=employee.post(path,data=json.dumps({'answers':answers}),content_type='application/json',
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH=f'"case:{case.pk}:v2"')
    assert response.status_code==201,response.content
    assert employee.get(path).json()['results'][0]['answers']==answers
    hr=Client()
    hr.force_login(persons['HR'][0])
    assert hr.get(path).status_code==200
    it=Client()
    it.force_login(persons['IT'][0])
    assert it.get(path).status_code==404
    assert Client().get(path).status_code in (401,404)
