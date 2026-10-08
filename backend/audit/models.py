"""Append-only historical evidence and idempotency receipts."""
import uuid
from django.db import models
from django.utils import timezone
from backend.accounts.models import User, Organization
from backend.onboarding.models import OnboardingCase

class AuditStream(models.Model):
    key = models.CharField(max_length=110,primary_key=True)
    next_sequence=models.PositiveBigIntegerField(default=1)
    last_hash=models.CharField(max_length=64,default='0'*64)

class AuditEvent(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    stream=models.ForeignKey(AuditStream,on_delete=models.PROTECT)
    sequence=models.PositiveBigIntegerField()
    actor=models.ForeignKey(User,on_delete=models.PROTECT,null=True)
    event_type=models.CharField(max_length=80)
    entity_id=models.UUIDField(null=True)
    command_id=models.UUIDField()
    sanitized_change=models.JSONField(default=dict)
    reason=models.CharField(max_length=256,blank=True)
    created_at=models.DateTimeField(default=timezone.now)
    previous_hash=models.CharField(max_length=64)
    event_hash=models.CharField(max_length=64)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['stream','sequence'],name='audit_unique_stream_sequence')]

class CommandReceipt(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    actor=models.ForeignKey(User,on_delete=models.PROTECT)
    route=models.CharField(max_length=80)
    idempotency_key=models.UUIDField()
    request_hash=models.CharField(max_length=64)
    case=models.ForeignKey(OnboardingCase,null=True,on_delete=models.PROTECT)
    response=models.JSONField()
    status_code=models.PositiveSmallIntegerField()
    committed_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['actor','route','idempotency_key'],name='unique_actor_command_key')]
