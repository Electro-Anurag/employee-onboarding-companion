"""M5 initial true PostgreSQL recipient/replay/reminder contract."""
from datetime import timedelta
import uuid
import pytest
from django.test import Client
from django.utils import timezone
from backend.accounts.models import User,Membership
from backend.onboarding.models import OnboardingCase,Task
from backend.onboarding.commands import activate_case
from backend.onboarding.services import reassign_owner
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.notifications.models import ReminderIntent,Notification
from backend.notifications.services import reconcile_case,reconcile_batch


@pytest.mark.django_db(transaction=True)
def test_reminder_current_owner_duplicate_outage_and_resolution(world):
    _,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='manager_preparation')
    now=task.due_at+timedelta(hours=1)
    first=reconcile_case(case.pk,now=now)
    assert first['created']>=1
    note=Notification.objects.get(task=task,recipient=actors['MANAGER'][0])
    assert note.intent.rule_code=='OVERDUE_DAILY'
    assert note.intent.time_bucket==now.astimezone(
        __import__('zoneinfo').ZoneInfo(case.organization.timezone)).date().isoformat()
    assert reconcile_case(case.pk,now=now)=={'created':0,'retired':0}
    assert ReminderIntent.objects.filter(task=task,recipient=actors['MANAGER'][0],
                                         status='DELIVERED').count()==1
    # After downtime only CURRENT day is delivered; no historical daily storm.
    later=now+timedelta(hours=49)
    outcome=reconcile_case(case.pk,now=later)
    assert outcome['created']>=1
    assert ReminderIntent.objects.filter(task=task,recipient=actors['MANAGER'][0],
                                         status='DELIVERED').count()==1
    assert Notification.objects.filter(task=task,recipient=actors['MANAGER'][0],
                                       status='SUPERSEDED').exists()
    assert reconcile_batch(now=later,limit=1)['processed']==1

    client=Client()
    client.force_login(actors['MANAGER'][0])
    resp=client.get('/api/v1/notifications')
    assert resp.status_code==200 and resp.json()['delivery']=='IN_APP_ONLY'
    current=[row for row in resp.json()['results'] if row['task_id']==str(task.pk)]
    assert len(current)==1
    read=client.post('/api/v1/notifications/'+current[0]['id']+'/read',
                     data='{}',content_type='application/json')
    assert read.status_code==200
    assert client.post('/api/v1/notifications/'+current[0]['id']+'/read',
                     data='{}',content_type='application/json').status_code==200
    assert Notification.objects.get(pk=current[0]['id']).read_at is not None
    other=Client()
    other.force_login(actors['IT'][0])
    assert other.get('/api/v1/notifications')['Content-Type'].startswith('application/json')
    assert other.post('/api/v1/notifications/'+current[0]['id']+'/read',
        data='{}',content_type='application/json').status_code==404
    assert not any(x['id']==current[0]['id'] for x in other.get('/api/v1/notifications').json()['results'])


@pytest.mark.django_db(transaction=True)
def test_reminders_reassignment_revokes_old_owner_without_new_delivery(world):
    org,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='manager_preparation')
    future=task.due_at+timedelta(hours=1)
    reconcile_case(case.pk,now=future)
    old_note=Notification.objects.get(task=task,recipient=actors['MANAGER'][0])
    second=User.objects.create_user(email='alternate.manager@astervalelabs.test',
        password='VerifiedStrongPassword!2026',display_name='Replacement Manager')
    new_member=Membership.objects.create(user=second,organization=org,role='MANAGER')
    reassign_owner(actor=actors['HR'][0],case_id=case.pk,role='MANAGER',
        new_member_id=new_member.pk,reason='Synthetic on-call recovery',
        key=uuid.uuid4(),expected_version=case.version)
    old=Client();old.force_login(actors['MANAGER'][0])
    assert old.get('/api/v1/notifications').json()['results']==[]
    assert old.post('/api/v1/notifications/'+str(old_note.pk)+'/read',
        data='{}',content_type='application/json').status_code==404
    reconcile_case(case.pk,now=future)
    assert Notification.objects.filter(pk=old_note.pk,status='SUPERSEDED').exists()
    assert Notification.objects.filter(task=task,recipient=second,status='ACTIVE').count()==1


@pytest.mark.django_db(transaction=True)
def test_m5_reconciliation_denies_invalid_bounds():
    with pytest.raises(ValueError,match='INVALID_RECONCILIATION_LIMIT'):
        reconcile_batch(limit=101)
