"""M5 PostgreSQL evidence for HR-controlled joining-date changes."""
import json
import uuid
from datetime import timedelta
from django.db import transaction,DatabaseError
from django.test import Client
from django.utils import timezone
import pytest
from backend.audit.models import AuditEvent,CommandReceipt
from backend.onboarding.models import OnboardingCase,Task,TaskCompletion,CaseDateChange
from backend.onboarding.commands import activate_case,attest_manager
from backend.onboarding.date_changes import preview_change,commit_change
from backend.onboarding.services import CommandFailure
from backend.notifications.models import ReminderIntent,Notification
from backend.notifications.services import reconcile_case
from backend.onboarding.tests.test_m2_workflow import world,published,create


@pytest.fixture
def activated(world):
    result,_=create(world,published(world),offset=21)
    case=OnboardingCase.objects.get(pk=result['case_id'])
    activate_case(actor=world[1]['HR'][0],case_id=case.pk,
        key=uuid.uuid4(),expected_version=1)
    case.refresh_from_db()
    assert case.status=='PRE_JOINING'
    return case,world[1]


@pytest.mark.django_db(transaction=True)
def test_date_change_preview_pure_commit_keeps_completed_evidence_and_rescopes_reminders(activated):
    case,people=activated
    hr=people['HR'][0]
    manager=Task.objects.get(case=case,key='manager_preparation')
    equipment=Task.objects.get(case=case,key='equipment_setup')
    manager_earlier=manager.available_at,manager.due_at
    equipment_earlier=equipment.available_at,equipment.due_at
    attest_manager(actor=people['MANAGER'][0],case_id=case.pk,task_id=manager.pk,
        fields={'first_week_plan':'Pair on initial product architecture',
            'buddy_name':'Synthetic Buddy','workstation_ready':True},
        note='Verified synthetic preparation evidence',key=uuid.uuid4(),
        expected_version=case.version)
    case.refresh_from_db()
    manager.refresh_from_db();equipment.refresh_from_db()
    proof=TaskCompletion.objects.get(task=manager)
    timestamp=manager.completed_at
    future=equipment.due_at+timedelta(days=2)
    reconcile_case(case.pk,now=future)
    assert Notification.objects.filter(case=case,status='ACTIVE').exists()
    old_schedule_ids=list(ReminderIntent.objects.filter(case=case,
        status='DELIVERED').values_list('pk',flat=True))
    target=case.joining_date+timedelta(days=5)
    plan=preview_change(actor=hr,case_id=case.pk,new_date=target,
        expected_version=case.version)
    assert str(manager.pk) in plan['preserved_task_ids']
    assert any(x['task_id']==str(equipment.pk) for x in plan['changes'])
    assert plan['schedule_revision']==0
    assert plan==preview_change(actor=hr,case_id=case.pk,new_date=target,
        expected_version=case.version)
    assert CaseDateChange.objects.count()==0
    assert equipment.due_at==equipment_earlier[1]
    saved_version=case.version
    key=uuid.uuid4()
    outcome,code=commit_change(actor=hr,case_id=case.pk,new_date=target,
        preview_digest=plan['preview_digest'],
        reason='Employee requested revised start date',key=key,
        expected_version=saved_version)
    assert code==200
    assert outcome==commit_change(actor=hr,case_id=case.pk,new_date=target,
        preview_digest=plan['preview_digest'],
        reason='Employee requested revised start date',key=key,
        expected_version=saved_version)[0]
    case.refresh_from_db();manager.refresh_from_db();equipment.refresh_from_db()
    assert case.joining_date==target and case.schedule_revision==1
    assert case.version>saved_version
    assert (manager.available_at,manager.due_at)==manager_earlier
    assert manager.completed_at==timestamp
    assert TaskCompletion.objects.get(task=manager).pk==proof.pk
    assert equipment.available_at>equipment_earlier[0]
    assert equipment.due_at>equipment_earlier[1]
    assert TaskCompletion.objects.count()==1
    # An approved historical decision does not license arbitrary further SQL
    # edits to any snapshot, or re-dating the case without a *new* decision.
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Task.objects.filter(pk=equipment.pk).update(
                due_at=equipment.due_at+timedelta(days=1))
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Task.objects.filter(pk=manager.pk).update(
                due_at=manager.due_at+timedelta(days=1))
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            OnboardingCase.objects.filter(pk=case.pk).update(
                joining_date=target+timedelta(days=1))
    assert not ReminderIntent.objects.filter(pk__in=old_schedule_ids,
        status='DELIVERED').exists()
    assert not Notification.objects.filter(case=case,status='ACTIVE').exists()
    decision=CaseDateChange.objects.get(case=case,revision=1)
    assert decision.preview_digest==plan['preview_digest']
    assert decision.preserved_task_ids==plan['preserved_task_ids']
    assert AuditEvent.objects.filter(event_type='M5_JOINING_DATE_CHANGED',
        entity_id=decision.pk).count()==1
    assert CommandReceipt.objects.filter(case=case,
        route='m5-joining-date-commit').count()==1
    # A fresh reconciliation creates the new schedule identity and does not
    # revive retired notification identities.
    reconcile_case(case.pk,now=equipment.due_at+timedelta(days=2))
    assert ReminderIntent.objects.filter(case=case,
        status='DELIVERED',schedule_revision=1).exists()
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            CaseDateChange.objects.filter(pk=decision.pk).update(
                reason='Forged HR approval')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            CaseDateChange.objects.filter(pk=decision.pk).delete()


@pytest.mark.django_db(transaction=True)
def test_joining_date_preview_revision_and_authority_fail_closed(activated):
    case,people=activated
    target=case.joining_date+timedelta(days=6)
    with pytest.raises(CommandFailure) as exc:
        preview_change(actor=people['MANAGER'][0],case_id=case.pk,
            new_date=target,expected_version=case.version)
    assert exc.value.code=='NOT_FOUND'
    preview=preview_change(actor=people['HR'][0],case_id=case.pk,
        new_date=target,expected_version=case.version)
    with pytest.raises(CommandFailure) as exc:
        commit_change(actor=people['MANAGER'][0],case_id=case.pk,
            new_date=target,preview_digest=preview['preview_digest'],
            reason='Wrong actor should not approve dates',
            key=uuid.uuid4(),expected_version=case.version)
    assert exc.value.code=='NOT_FOUND'
    with pytest.raises(CommandFailure) as exc:
        commit_change(actor=people['HR'][0],case_id=case.pk,
            new_date=target,preview_digest='0'*64,
            reason='Fabricated preview digest is invalid',
            key=uuid.uuid4(),expected_version=case.version)
    assert exc.value.code=='STALE_DATE_CHANGE_PREVIEW'
    other=case.joining_date+timedelta(days=7)
    with pytest.raises(CommandFailure) as exc:
        commit_change(actor=people['HR'][0],case_id=case.pk,
            new_date=other,preview_digest=preview['preview_digest'],
            reason='Another target cannot reuse old preview',
            key=uuid.uuid4(),expected_version=case.version)
    assert exc.value.code=='STALE_DATE_CHANGE_PREVIEW'
    assert not CaseDateChange.objects.exists()
    # The actor still must provide a CURRENT preview after another case write.
    commit_change(actor=people['HR'][0],case_id=case.pk,
        new_date=target,preview_digest=preview['preview_digest'],
        reason='Human consent verified',key=uuid.uuid4(),
        expected_version=case.version)
    with pytest.raises(CommandFailure) as exc:
        commit_change(actor=people['HR'][0],case_id=case.pk,
            new_date=other,preview_digest=preview['preview_digest'],
            reason='Stale write must fail',key=uuid.uuid4(),
            expected_version=case.version)
    assert exc.value.code=='STALE_VERSION'
    case.refresh_from_db()
    with pytest.raises(CommandFailure) as exc:
        preview_change(actor=people['HR'][0],case_id=case.pk,
            new_date=case.joining_date,expected_version=case.version)
    assert exc.value.code=='JOINING_DATE_UNCHANGED'


@pytest.mark.django_db(transaction=True)
def test_date_change_http_csrf_preview_commit_then_stale_precondition(activated):
    case,people=activated
    hr=people['HR'][0]
    c=Client(enforce_csrf_checks=True)
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    login=c.post('/api/v1/auth/login',data=json.dumps({
        'email':hr.email,'password':'VerifiedStrongPassword!2026'}),
        content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert login.status_code==200
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    target=(case.joining_date+timedelta(days=3)).isoformat()
    base=f'/api/v1/cases/{case.pk}/joining-date'
    etag=f'"case:{case.pk}:v{case.version}"'
    preview=c.get(base+'/preview',{'joining_date':target},HTTP_IF_MATCH=etag)
    assert preview.status_code==200,preview.content
    assert preview.json()['change_count']>0
    no_csrf=Client(enforce_csrf_checks=True)
    no_csrf.force_login(hr)
    assert no_csrf.post(base+'/commit',data='{}',
        content_type='application/json',HTTP_IF_MATCH=etag).status_code==403
    commit=c.post(base+'/commit',data=json.dumps({
        'joining_date':target,'preview_digest':preview.json()['preview_digest'],
        'reason':'Synthetic employee approved new joining date'}),
        content_type='application/json',HTTP_IF_MATCH=etag,
        HTTP_X_CSRFTOKEN=csrf,HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert commit.status_code==200,commit.content
    stale=c.get(base+'/preview',{'joining_date':target},
        HTTP_IF_MATCH=etag)
    assert stale.status_code==409
    assert stale.json()['error']['code']=='STALE_VERSION'
