"""M5 stale inbox entries are hidden without relying on a live worker."""
from datetime import timedelta
import pytest
from backend.notifications.models import ReminderIntent,Notification
from backend.notifications.services import reconcile_case
from backend.notifications.views import _visible
from backend.notifications.tests.test_escalation import ready_manager_case


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
