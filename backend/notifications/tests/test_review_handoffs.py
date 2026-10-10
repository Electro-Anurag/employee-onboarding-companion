"""M5 review and correction handoffs: real typed M3 evidence, no invented state."""
import hashlib
import uuid
from django.test import Client
from django.utils import timezone
import pytest
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.onboarding.models import OnboardingCase,Task
from backend.onboarding.commands import activate_case
from backend.forms.commands import submit as submit_form,review as review_form
from backend.documents.commands import upload as submit_fixture,review as review_fixture
from backend.documents.fixtures import FIXTURES
from backend.documents.real_commands import (prepare as prepare_secure,
    receive as receive_secure,scan_one,review as review_secure)
from backend.documents.tests.test_secure_s3_journey import s3_doubles,generated_pdf
from backend.notifications.models import ReminderIntent,Notification
from backend.notifications.services import reconcile_case
from backend.notifications.tests.test_reminders import signed_in
from backend.onboarding.services import reassign_owner
from backend.accounts.models import User,Membership


def active(world):
    result,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=result['case_id'])
    activate_case(actor=world[1]['HR'][0],case_id=case.pk,
        key=uuid.uuid4(),expected_version=1)
    return case


def version(case):
    case.refresh_from_db()
    return case.version


def visible(client):
    response=client.get('/api/v1/notifications')
    assert response.status_code==200,response.content
    assert response['Cache-Control']=='private, no-store'
    return response.json()['results']


def notifications_for(client,task,rule=None):
    return [r for r in visible(client) if r['task_id']==str(task.pk)
            and (rule is None or r['rule_code']==rule)]


def check_not_readable(client,notice):
    resp=client.post(f'/api/v1/notifications/{notice.pk}/read',
        data='{}',content_type='application/json')
    assert resp.status_code==404


@pytest.mark.django_db(transaction=True)
def test_m5_form_review_and_correction_handoff_from_actual_revisions(world):
    case=active(world)
    actors=world[1]
    task=Task.objects.get(case=case,key='personal_details')
    employee=signed_in(actors['EMPLOYEE'][0])
    hr=signed_in(actors['HR'][0])
    it=signed_in(actors['IT'][0])
    answers={'preferred_name':'Synthetic Person','contact_email':'synthetic@example.invalid'}
    # Mere READY template task never fabricates a HR review request.
    assert reconcile_case(case.pk)['created']>=0
    assert notifications_for(hr,task)==[]
    submitted,_=submit_form(actor=actors['EMPLOYEE'][0],case_id=case.pk,
        task_id=task.pk,answers=answers,key=uuid.uuid4(),expected_version=version(case))
    first=uuid.UUID(submitted['result']['submission_id'])
    assert reconcile_case(case.pk)['created']>=1
    review_alert=Notification.objects.get(task=task,intent__rule_code='FORM_HR_REVIEW')
    assert review_alert.intent.time_bucket==str(first)
    assert 'synthetic@example.invalid' not in review_alert.summary
    assert 'Synthetic Person' not in review_alert.summary
    assert len(notifications_for(hr,task,'FORM_HR_REVIEW'))==1
    assert notifications_for(employee,task)==[]
    assert notifications_for(it,task)==[]
    check_not_readable(it,review_alert)
    check_not_readable(employee,review_alert)
    assert reconcile_case(case.pk)=={'created':0,'retired':0}

    review_form(actor=actors['HR'][0],case_id=case.pk,task_id=task.pk,
        submission_id=first,decision='CHANGES_REQUESTED',
        note='Correct synthetic details',key=uuid.uuid4(),
        expected_version=version(case))
    # Recipient access is revoked immediately, before periodic reconciliation.
    assert notifications_for(hr,task)==[]
    check_not_readable(hr,review_alert)
    reconcile_case(case.pk)
    assert Notification.objects.get(pk=review_alert.pk).status=='SUPERSEDED'
    employee_alert=Notification.objects.get(task=task,intent__rule_code='FORM_CORRECTION')
    assert employee_alert.intent.time_bucket==str(first)
    assert len(notifications_for(employee,task,'FORM_CORRECTION'))==1
    assert notifications_for(hr,task)==[]
    corrected={**answers,'preferred_name':'Corrected Synthetic Person'}
    again,_=submit_form(actor=actors['EMPLOYEE'][0],case_id=case.pk,
        task_id=task.pk,answers=corrected,key=uuid.uuid4(),
        expected_version=version(case))
    second=uuid.UUID(again['result']['submission_id'])
    assert notifications_for(employee,task)==[]
    check_not_readable(employee,employee_alert)
    reconcile_case(case.pk)
    assert Notification.objects.get(pk=employee_alert.pk).status=='SUPERSEDED'
    assert len(notifications_for(hr,task,'FORM_HR_REVIEW'))==1
    assert ReminderIntent.objects.get(task=task,status='DELIVERED').time_bucket==str(second)
    review_form(actor=actors['HR'][0],case_id=case.pk,task_id=task.pk,
        submission_id=second,decision='ACCEPTED',note='Verified synthetic submission',
        key=uuid.uuid4(),expected_version=version(case))
    assert notifications_for(hr,task)==[]
    reconcile_case(case.pk)
    assert not Notification.objects.filter(task=task,status='ACTIVE').exists()
    assert not Notification.objects.filter(task=task,recipient=actors['IT'][0]).exists()


@pytest.mark.django_db(transaction=True)
def test_m5_fixture_document_review_and_employee_replacement_handoff(world):
    case=active(world)
    actors=world[1]
    task=Task.objects.get(case=case,key='identity_document')
    employee=signed_in(actors['EMPLOYEE'][0])
    hr=signed_in(actors['HR'][0])
    result,_=submit_fixture(actor=actors['EMPLOYEE'][0],case_id=case.pk,
        task_id=task.pk,raw=FIXTURES['identity_document'],key=uuid.uuid4(),
        expected_version=version(case))
    first=uuid.UUID(result['result']['document_revision_id'])
    reconcile_case(case.pk)
    alert=Notification.objects.get(task=task,intent__rule_code='DOCUMENT_HR_REVIEW')
    assert alert.intent.time_bucket==str(first)
    assert len(notifications_for(hr,task))==1
    assert notifications_for(employee,task)==[]
    review_fixture(actor=actors['HR'][0],case_id=case.pk,task_id=task.pk,
        revision_id=first,decision='NEEDS_CLARIFICATION',
        note='Replace synthetic example',key=uuid.uuid4(),expected_version=version(case))
    assert notifications_for(hr,task)==[]
    reconcile_case(case.pk)
    assert len(notifications_for(employee,task,'DOCUMENT_CORRECTION'))==1
    second,_=submit_fixture(actor=actors['EMPLOYEE'][0],case_id=case.pk,
        task_id=task.pk,raw=FIXTURES['identity_document'],key=uuid.uuid4(),
        expected_version=version(case))
    next_id=uuid.UUID(second['result']['document_revision_id'])
    reconcile_case(case.pk)
    assert not notifications_for(employee,task)
    assert len(notifications_for(hr,task))==1
    review_fixture(actor=actors['HR'][0],case_id=case.pk,task_id=task.pk,
        revision_id=next_id,decision='ACCEPTED',
        note='Accepted exact synthetic fixture',key=uuid.uuid4(),
        expected_version=version(case))
    assert notifications_for(hr,task)==[]
    reconcile_case(case.pk)
    assert not Notification.objects.filter(task=task,status='ACTIVE').exists()


@pytest.mark.django_db(transaction=True)
def test_m5_secure_pdf_only_clean_exact_version_can_reach_hr(world,s3_doubles):
    case=active(world)
    actors=world[1]
    task=Task.objects.get(case=case,key='identity_document')
    hr=signed_in(actors['HR'][0])
    employee=signed_in(actors['EMPLOYEE'][0])
    raw=generated_pdf()
    declared,_=prepare_secure(actor=actors['EMPLOYEE'][0],case_id=case.pk,
        task_id=task.pk,sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
        filename='synthetic.pdf',key=uuid.uuid4(),expected_version=version(case))
    upload_id=uuid.UUID(declared['result']['upload_id'])
    reconcile_case(case.pk)
    assert not notifications_for(hr,task)
    receive_secure(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        upload_id=upload_id,raw=raw,key=uuid.uuid4(),expected_version=version(case))
    reconcile_case(case.pk)
    assert not notifications_for(hr,task)  # quarantined, not trusted
    assert not notifications_for(employee,task)
    scan_one(upload_id,scanner=lambda _:('CLEAN','synthetic verified scan'))
    reconcile_case(case.pk)
    proof=Notification.objects.get(task=task,intent__rule_code='DOCUMENT_HR_REVIEW')
    assert proof.intent.time_bucket==str(upload_id)
    assert len(notifications_for(hr,task))==1
    assert 'synthetic.pdf' not in proof.summary
    review_secure(actor=actors['HR'][0],case_id=case.pk,task_id=task.pk,
        upload_id=upload_id,decision='REJECTED',note='Synthetic revision needs correction',
        key=uuid.uuid4(),expected_version=version(case))
    assert not notifications_for(hr,task)
    reconcile_case(case.pk)
    assert len(notifications_for(employee,task,'DOCUMENT_CORRECTION'))==1


@pytest.mark.django_db(transaction=True)
def test_m5_reassignment_revokes_pending_hr_handoff_even_before_reconcile(world):
    org,actors=world
    case=active(world)
    task=Task.objects.get(case=case,key='personal_details')
    submit_form(actor=actors['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
        answers={'preferred_name':'Synthetic','contact_email':'demo@example.invalid'},
        key=uuid.uuid4(),expected_version=version(case))
    reconcile_case(case.pk)
    alert=Notification.objects.get(task=task,intent__rule_code='FORM_HR_REVIEW')
    previous=signed_in(actors['HR'][0])
    assert len(notifications_for(previous,task))==1
    successor=User.objects.create_user(email='new.hr@m5.synthetic.invalid',
        password='VerifiedStrongPassword!2026',display_name='New current HR')
    member=Membership.objects.create(user=successor,organization=org,role='HR',
        can_coordinate_ownership=True,can_manage_templates=True)
    reassign_owner(actor=actors['HR'][0],case_id=case.pk,role='HR',
        new_member_id=member.pk,reason='Current HR changed by authorized owner',
        key=uuid.uuid4(),expected_version=version(case))
    assert not notifications_for(previous,task)
    check_not_readable(previous,alert)
    reconcile_case(case.pk)
    assert Notification.objects.get(pk=alert.pk).status=='SUPERSEDED'
    current=signed_in(successor)
    assert len(notifications_for(current,task,'FORM_HR_REVIEW'))==1
