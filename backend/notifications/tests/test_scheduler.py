"""M5 real PostgreSQL control-queue and >100-case recovery boundaries."""
import uuid
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
import pytest
from django.db import transaction,connection,close_old_connections
from django.utils import timezone
from backend.accounts.models import Organization,User,Membership
from backend.jobs.atomic import defer_atomic,AtomicDeferralRequired
from backend.jobs.tasks import reconcile_current_reminders
from backend.notifications.services import reconcile_batch
from backend.onboarding.tests.test_m2_workflow import world
from backend.onboarding.models import OnboardingCase


@pytest.mark.django_db(transaction=True)
def test_m5_continuation_enqueue_is_registered_and_atomic():
    with pytest.raises(AtomicDeferralRequired):
        defer_atomic(reconcile_current_reminders,after='')
    with transaction.atomic():
        job_id=defer_atomic(reconcile_current_reminders,after='test-cursor')
        with connection.cursor() as cursor:
            cursor.execute('SELECT task_name,args FROM procrastinate_jobs WHERE id=%s',[job_id])
            row=cursor.fetchone()
        assert row[0]=='m5.reconcile_current_reminders'
        args=json.loads(row[1]) if isinstance(row[1],str) else row[1]
        assert args['after']=='test-cursor'
    with connection.cursor() as cursor:
        cursor.execute('SELECT task_name FROM procrastinate_jobs WHERE id=%s',[job_id])
        assert cursor.fetchone()==('m5.reconcile_current_reminders',)


@pytest.mark.django_db(transaction=True)
def test_m5_reconciliation_over_100_cases_returns_cursor_without_dropping_remaining():
    org=Organization.objects.create(name='Synthetic cursor-bounded reminders')
    for i in range(101):
        user=User.objects.create_user(email=f'm5-batch-{i}@synthetic.invalid',
            password=None,display_name='Synthetic Batch Employee')
        member=Membership.objects.create(organization=org,user=user,role='EMPLOYEE')
        OnboardingCase.objects.create(organization=org,employee=member,
            joining_date=timezone.localdate(),status='CREATED')
    first=reconcile_batch(now=timezone.now(),limit=100)
    assert first['processed']==100 and first['next_cursor'] is not None
    second=reconcile_batch(now=timezone.now(),after=first['next_cursor'],limit=100)
    assert second['processed']==1 and second['next_cursor'] is None
    assert first['created']==second['created']==0


@pytest.mark.django_db(transaction=True)
def test_two_workers_reconcile_same_case_without_duplicate_notifications(world):
    """Real concurrent DB sessions serialize at the case lock, not Python GIL."""
    from backend.onboarding.tests.test_m2_workflow import published,create
    from backend.onboarding.commands import activate_case
    from backend.onboarding.models import Task
    from backend.notifications.models import ReminderIntent,Notification
    from backend.notifications.policy import ESCALATION_RULE
    org,actors=world
    made,_=create(world,published(world),offset=-14)
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='manager_preparation')
    instant=timezone.now()
    assert instant>=task.due_at+timedelta(hours=48)
    start=Barrier(3)
    def worker():
        close_old_connections()
        try:
            start.wait(timeout=15)
            return reconcile_case(case.pk,now=instant)
        finally:
            close_old_connections()
    from backend.notifications.services import reconcile_case
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(worker) for _ in range(2)]
        start.wait(timeout=15)
        outcomes=[f.result(timeout=45) for f in futures]
    daily=ReminderIntent.objects.filter(
        task=task,recipient=actors['MANAGER'][0],
        rule_code='OVERDUE_DAILY',status='DELIVERED')
    escalation=ReminderIntent.objects.filter(
        task=task,recipient=actors['HR'][0],
        rule_code=ESCALATION_RULE,status='DELIVERED')
    assert daily.count()==1
    assert escalation.count()==1
    assert Notification.objects.filter(intent__in=daily,status='ACTIVE').count()==1
    assert Notification.objects.filter(intent__in=escalation,status='ACTIVE').count()==1
    # Across both executions each exact reminder identity was inserted once.
    assert sum(outcome['created'] for outcome in outcomes)>=2
    assert sum(outcome['retired'] for outcome in outcomes)==0
    assert reconcile_case(case.pk,now=instant)=={'created':0,'retired':0}


@pytest.mark.django_db(transaction=True)
def test_delayed_worker_reconciles_only_current_day_without_replaying_missed_days(world):
    """A 72-hour worker outage cannot create one reminder per missed tick."""
    from backend.onboarding.tests.test_m2_workflow import published,create
    from backend.onboarding.commands import activate_case
    from backend.onboarding.models import Task
    from backend.notifications.models import ReminderIntent,Notification
    from backend.notifications.services import reconcile_case
    from backend.notifications.views import _visible
    _,actors=world
    made,_=create(world,published(world),offset=-14)
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='manager_preparation')
    first=timezone.now()
    early=reconcile_case(case.pk,now=first)
    assert early['created']>=1
    initial=ReminderIntent.objects.get(task=task,rule_code='OVERDUE_DAILY')
    after_outage=first+timedelta(hours=72)
    recovered=reconcile_case(case.pk,now=after_outage)
    assert recovered['created']>=1
    daily=ReminderIntent.objects.filter(task=task,rule_code='OVERDUE_DAILY')
    assert daily.count()==2  # initial + current, not 3 missing days
    assert daily.filter(status='DELIVERED').count()==1
    initial.refresh_from_db()
    assert initial.status=='SUPERSEDED'
    latest=daily.get(status='DELIVERED')
    assert _visible(actors['MANAGER'][0],Notification.objects.get(intent=latest),
                    after_outage)
    assert not _visible(actors['MANAGER'][0],Notification.objects.get(intent=initial),
                        after_outage)
    assert reconcile_case(case.pk,now=after_outage)=={'created':0,'retired':0}
