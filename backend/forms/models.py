"""Append-only case-scoped form versions and decisions. No fake task completion."""
import uuid
from django.db import models
from django.utils import timezone

class FormSubmission(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.ForeignKey('onboarding.Task',on_delete=models.PROTECT,related_name='form_submissions')
    revision=models.PositiveIntegerField()
    submitted_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    answers=models.JSONField()
    content_hash=models.CharField(max_length=64)
    submitted_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['task','revision'],name='m3_form_task_revision_unique')]
        ordering=['revision']

class FormReview(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    submission=models.OneToOneField(FormSubmission,on_delete=models.PROTECT,related_name='review')
    reviewed_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    decision=models.CharField(max_length=24,choices=[('ACCEPTED','ACCEPTED'),('CHANGES_REQUESTED','CHANGES_REQUESTED')])
    note=models.CharField(max_length=500)
    reviewed_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(decision__in=['ACCEPTED','CHANGES_REQUESTED']),name='m3_form_valid_review')]
