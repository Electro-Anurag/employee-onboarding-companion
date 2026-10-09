"""One append-only acknowledgement of an exact case-frozen policy edition."""
import uuid
from django.db import models
from django.utils import timezone

class PolicyAcknowledgement(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.OneToOneField('onboarding.Task',on_delete=models.PROTECT,related_name='policy_acknowledgement')
    actor=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    policy_version=models.CharField(max_length=80)
    content_sha256=models.CharField(max_length=64)
    acknowledged_at=models.DateTimeField(default=timezone.now)
