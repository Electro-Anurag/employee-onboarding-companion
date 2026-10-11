"""M5 stale inbox entries are hidden without relying on a live worker."""
from datetime import timedelta
import pytest
from backend.onboarding.tests.test_m2_workflow import world
from backend.notifications.models import ReminderIntent,Notification
from backend.notifications.services import reconcile_case
from backend.notifications.views import _visible
from backend.notifications.tests.test_escalation import ready_manager_case,naturally_overdue_manager_case
from backend.notifications.tests.test_reminders import signed_in


@pytest.mark.django_db(transaction=True)
def test_due_soon_intent_hidden_after_deadline_without_reconcile(ready_manager_case):
    case,task,actors=ready_manager_case
    before=task.due_at-timedelta(hours=12)
    reconcile_case(case.pk,now=before)
    intent=ReminderIntent.objects.get(task=task,rule_code='DUE_SOON')
    notice=Notification.objects.select_related('intent','task').get(intent=intent)
    manager=actors['MANAGER'][0]
    assert _visible(manager,notice,before)
    assert not _visible(manager,notice,task.due_at+timedelta(seconds=1))
    intent.refresh_from_db()
    assert intent.status=='DELIVERED'


@pytest.mark.django_db(transaction=True)
def test_old_overdue_local_day_hidden_during_worker_outage(ready_manager_case):
    case,task,actors=ready_manager_case
    today=task.due_at+timedelta(hours=3)
    reconcile_case(case.pk,now=today)
    intent=ReminderIntent.objects.get(task=task,rule_code='OVERDUE_DAILY')
    notice=Notification.objects.select_related('intent','task').get(intent=intent)
    manager=actors['MANAGER'][0]
    assert _visible(manager,notice,today)
    assert not _visible(manager,notice,today+timedelta(days=1))
    intent.refresh_from_db()
    assert intent.status=='DELIVERED'


@pytest.mark.django_db(transaction=True)
def test_archived_backlog_does_not_crowd_out_current_inbox_notice(naturally_overdue_manager_case):
    case,task,actors=naturally_overdue_manager_case
    from django.utils import timezone
    now=timezone.now()
    reconcile_case(case.pk,now=now)
    manager=actors['MANAGER'][0]
    live=Notification.objects.get(task=task,recipient=manager,status='ACTIVE')
    assert live.intent.rule_code=='OVERDUE_DAILY'

    # More than 100 newer historical notices from a long-running case must
    # not make an older current notice disappear from the 100-item inbox.
    for number in range(105):
        retired=ReminderIntent.objects.create(
            case=case,task=task,recipient=manager,subject_type='TASK',
            schedule_revision=case.schedule_revision,
            action_revision=task.version,policy_version='M5-REMIND-V1',
            rule_code='OVERDUE_DAILY',time_bucket=f'archived-{number:03}',
            due_at=task.due_at,status='SUPERSEDED')
        Notification.objects.create(
            intent=retired,case=case,task=task,recipient=manager,
            summary='Expired synthetic reminder',status='SUPERSEDED')

    manager_session=signed_in(manager)
    response=manager_session.get('/api/v1/notifications')
    assert response.status_code==200,response.content
    rows=response.json()['results']
    assert len(rows)<=100
    assert str(live.pk) in {row['id'] for row in rows}
    assert not any(row['summary']=='Expired synthetic reminder' for row in rows)
    read=manager_session.post('/api/v1/notifications/'+str(live.pk)+'/read',
                              data='{}',content_type='application/json')
    assert read.status_code==200,read.content
