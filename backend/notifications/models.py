"""Durable, account-scoped in-app reminders; never carry document contents."""
import uuid
from django.db import models
from django.utils import timezone


class ReminderIntent(models.Model):
    """One immutable reminder identity per subject/recipient/revision/bucket."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey('onboarding.OnboardingCase', on_delete=models.PROTECT)
    task = models.ForeignKey('onboarding.Task', on_delete=models.PROTECT)
    recipient = models.ForeignKey('accounts.User', on_delete=models.PROTECT)
    subject_type = models.CharField(max_length=16, default='TASK')
    schedule_revision = models.PositiveBigIntegerField(default=0)
    action_revision = models.PositiveBigIntegerField()
    policy_version = models.CharField(max_length=32, default='M5-REMIND-V1')
    rule_code = models.CharField(max_length=32)
    time_bucket = models.CharField(max_length=40)
    due_at = models.DateTimeField()
    status = models.CharField(max_length=16, default='DELIVERED',
                              choices=[(v,v) for v in ('DELIVERED','SUPERSEDED','SUPPRESSED')])
    created_at = models.DateTimeField(default=timezone.now)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['subject_type','task','schedule_revision',
                'action_revision','recipient','rule_code','time_bucket','policy_version'],
                name='m5_unique_task_reminder_identity'),
        ]
        indexes = [models.Index(fields=['case','status'],name='m5_reminder_case_status')]


class Notification(models.Model):
    """Private persisted inbox record; no email, provider or browser delivery claim."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.OneToOneField(ReminderIntent,on_delete=models.PROTECT)
    case = models.ForeignKey('onboarding.OnboardingCase',on_delete=models.PROTECT)
    recipient = models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    task = models.ForeignKey('onboarding.Task',on_delete=models.PROTECT)
    summary = models.CharField(max_length=200)
    status = models.CharField(max_length=16,default='ACTIVE',
        choices=[(v,v) for v in ('ACTIVE','RESOLVED','SUPERSEDED')])
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True)
    class Meta:
        indexes = [models.Index(fields=['recipient','created_at'],name='m5_inbox_recipient_date')]
