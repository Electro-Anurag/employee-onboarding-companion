"""Append-only meeting occurrences and organizer attendance evidence."""
import uuid
from django.db import models
from django.utils import timezone

class ActivityOccurrence(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.ForeignKey('onboarding.Task',on_delete=models.PROTECT,related_name='activity_occurrences')
    revision=models.PositiveIntegerField()
    begins_at=models.DateTimeField()
    ends_at=models.DateTimeField()
    medium=models.CharField(max_length=16,choices=[('VIDEO','VIDEO'),('IN_PERSON','IN_PERSON')])
    meeting_reference=models.CharField(max_length=160)
    reason=models.CharField(max_length=300)
    scheduled_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT,related_name='scheduled_occurrences')
    scheduled_at=models.DateTimeField(default=timezone.now)
    class Meta:
        ordering=['revision']
        constraints=[
            models.UniqueConstraint(fields=['task','revision'],name='m4_activity_task_revision_unique'),
            models.CheckConstraint(condition=models.Q(ends_at__gt=models.F('begins_at')),name='m4_activity_positive_duration'),
            models.CheckConstraint(condition=models.Q(medium__in=['VIDEO','IN_PERSON']),name='m4_activity_valid_medium'),
        ]

class ActivityAttendance(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    occurrence=models.OneToOneField(ActivityOccurrence,on_delete=models.PROTECT,related_name='attendance')
    recorded_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    outcome=models.CharField(max_length=16,choices=[('ATTENDED','ATTENDED'),('MISSED','MISSED')])
    note=models.CharField(max_length=500)
    recorded_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(outcome__in=['ATTENDED','MISSED']),
              name='m4_activity_attendance_outcome_valid')]
