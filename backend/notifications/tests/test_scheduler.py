"""M5 real PostgreSQL control-queue and >100-case recovery boundaries."""
import uuid
import json
import pytest
from django.db import transaction,connection
from django.utils import timezone
from backend.accounts.models import Organization,User,Membership
from backend.jobs.atomic import defer_atomic,AtomicDeferralRequired
from backend.jobs.tasks import reconcile_current_reminders
from backend.notifications.services import reconcile_batch
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
