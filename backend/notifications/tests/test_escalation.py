"""M5 actual PostgreSQL 48h HR escalation: single policy identity, current actors."""
import uuid
from datetime import timedelta
import pytest
from django.utils import timezone
from backend.accounts.models import User,Membership
from backend.onboarding.models import OnboardingCase,Task
from backend.onboarding.commands import activate_case,attest_manager
from backend.onboarding.services import reassign_owner
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.notifications.models import ReminderIntent,Notification
from backend.notifications.services import reconcile_case,escalation_candidate
from backend.notifications.policy import (
    ESCALATION_POLICY_VERSION,ESCALATION_RULE,ESCALATION_DELAY)
from backend.notifications.tests.test_reminders import signed_in


@pytest.fixture
def ready_manager_case(world):
    _,actors=world
    result,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=result['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    case.refresh_from_db()
    assert case.status=='PRE_JOINING'
    task=Task.objects.get(case=case,key='manager_preparation')
    return case,task,actors


@pytest.fixture
def naturally_overdue_manager_case(world):
    _,actors=world
    # Actual past deadlines make session-safe HTTP verification possible
    # without advancing Django's authentication/session clock.
    result,_=create(world,published(world),offset=-14)
    case=OnboardingCase.objects.get(pk=result['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    case.refresh_from_db()
    assert case.status=='PRE_JOINING'
    task=Task.objects.get(case=case,key='manager_preparation')
    assert timezone.now()>=task.due_at+ESCALATION_DELAY
    return case,task,actors


def inbox(client):
    response=client.get('/api/v1/notifications')
    assert response.status_code==200,response.content
    return response.json()['results']


@pytest.mark.django_db(transaction=True)
def test_hr_escalation_starts_at_48h_preserves_owner_daily_reminder_and_is_idempotent(ready_manager_case):
    case,task,actors=ready_manager_case
    before=task.due_at+ESCALATION_DELAY-timedelta(seconds=1)
    assert reconcile_case(case.pk,now=before)['created']>=1
    assert not ReminderIntent.objects.filter(task=task,rule_code=ESCALATION_RULE).exists()
    instant=task.due_at+ESCALATION_DELAY
    first=reconcile_case(case.pk,now=instant)
    assert first['created']>=1
    escalation=ReminderIntent.objects.get(task=task,rule_code=ESCALATION_RULE)
    assert escalation.recipient_id==actors['HR'][0].pk
    assert escalation.policy_version==ESCALATION_POLICY_VERSION
    assert escalation.time_bucket=='due:'+task.due_at.isoformat()
    assert escalation.schedule_revision==case.schedule_revision
    assert Notification.objects.get(intent=escalation).summary.startswith(
        'Escalation to HR: 48 hours overdue')
    assert ReminderIntent.objects.filter(task=task,recipient=actors['MANAGER'][0],
        rule_code='OVERDUE_DAILY',status='DELIVERED').count()==1
    assert reconcile_case(case.pk,now=instant)=={'created':0,'retired':0}
    # Across days there is one HR escalation, never a backlog/duplicate storm.
    late=instant+timedelta(hours=75)
    reconcile_case(case.pk,now=late)
    assert ReminderIntent.objects.filter(task=task,rule_code=ESCALATION_RULE,
        status='DELIVERED').count()==1
    # The virtual deadline is intentionally in the future. Durable intent,
    # recipient and deduplication are proven above; real HTTP access is
    # covered with naturally overdue cases below, without time travel.


@pytest.mark.django_db(transaction=True)
def test_escalation_revoked_on_hr_reassignment_before_reconcile(naturally_overdue_manager_case):
    case,task,actors=naturally_overdue_manager_case
    now=timezone.now()
    reconcile_case(case.pk,now=now)
    intent=ReminderIntent.objects.get(task=task,rule_code=ESCALATION_RULE)
    old=signed_in(actors['HR'][0])
    assert any(x['id']==str(intent.notification.pk) for x in inbox(old))
    org=case.organization
    replacement=User.objects.create_user(email='policy-replacement-hr@synthetic.invalid',
        password='VerifiedStrongPassword!2026',display_name='Escalation Replacement HR')
    member=Membership.objects.create(user=replacement,organization=org,role='HR',
        active=True,available=True,can_coordinate_ownership=True)
    case.refresh_from_db()
    reassign_owner(actor=actors['HR'][0],case_id=case.pk,role='HR',
        new_member_id=member.pk,reason='Escalation owner changed for coverage',
        key=uuid.uuid4(),expected_version=case.version)
    assert not any(x['rule_code']==ESCALATION_RULE for x in inbox(old))
    reconcile_case(case.pk,now=now)
    assert ReminderIntent.objects.get(pk=intent.pk).status=='SUPERSEDED'
    current=signed_in(replacement)
    assert len([x for x in inbox(current)
                if x['rule_code']==ESCALATION_RULE])==1


@pytest.mark.django_db(transaction=True)
def test_escalation_is_read_denied_after_task_completion(naturally_overdue_manager_case):
    case,task,actors=naturally_overdue_manager_case
    now=timezone.now()
    reconcile_case(case.pk,now=now)
    intent=ReminderIntent.objects.get(task=task,rule_code=ESCALATION_RULE)
    case.refresh_from_db()
    attest_manager(actor=actors['MANAGER'][0],case_id=case.pk,task_id=task.pk,
        fields={'first_week_plan':'Synthetic real manager plan',
            'buddy_name':'Synthetic Buddy','workstation_ready':True},
        note='Confirmed preparation work for escalation closure',
        key=uuid.uuid4(),expected_version=case.version)
    hr=signed_in(actors['HR'][0])
    assert not any(x['id']==str(intent.notification.pk) for x in inbox(hr))
    reconcile_case(case.pk,now=now)
    assert ReminderIntent.objects.get(pk=intent.pk).status=='SUPERSEDED'
    assert not Notification.objects.filter(intent=intent,status='ACTIVE').exists()


@pytest.mark.django_db(transaction=True)
def test_escalation_requires_current_available_hr_and_actual_owner(ready_manager_case):
    case,task,actors=ready_manager_case
    now=task.due_at+timedelta(hours=49)
    hr_member=actors['HR'][1]
    hr_member.available=False;hr_member.save(update_fields=['available'])
    assert escalation_candidate(task,case,now) is None
    reconcile_case(case.pk,now=now)
    assert not ReminderIntent.objects.filter(task=task,rule_code=ESCALATION_RULE).exists()
    hr_member.available=True;hr_member.save(update_fields=['available'])
    hr_member.refresh_from_db();case.refresh_from_db();task.refresh_from_db()
    from backend.onboarding.state_machine import current_assignments
    from backend.notifications.services import current_recipient,_eligible_actor
    assigned=current_assignments(case,now)
    owner=current_recipient(task,case,now)
    hr=_eligible_actor(case,'HR',now)
    assert hr_member.available and owner is not None and hr is not None, {
        'hr_available':hr_member.available,
        'assigned_hr':str(assigned['HR'].member_id) if 'HR' in assigned else None,
        'current_hr':str(hr.pk) if hr else None,
        'owner':str(owner.pk) if owner else None,
        'task_state':task.execution_state,'case_status':case.status}
    assert escalation_candidate(task,case,now) is not None
