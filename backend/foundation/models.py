"""Temporary M0 probe records; these are not the future onboarding-case schema."""
import uuid
from django.db import models

class FoundationOperation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=128)
    status = models.CharField(max_length=16, default="CREATED")
    crash_after_apply_once = models.BooleanField(default=False)
    crash_fired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True)

class FoundationAudit(models.Model):
    operation = models.ForeignKey(FoundationOperation, on_delete=models.PROTECT)
    event = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["operation", "event"], name="m0_unique_operation_event")]

class FoundationEffect(models.Model):
    operation = models.OneToOneField(FoundationOperation, on_delete=models.PROTECT, primary_key=True)
    applied_at = models.DateTimeField(auto_now_add=True)
