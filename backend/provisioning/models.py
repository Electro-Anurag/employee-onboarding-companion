"""Persisted synthetic IT operations. SIMULATED is not external fulfillment."""
import uuid
from django.db import models
from django.utils import timezone

class ITOperation(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.OneToOneField('onboarding.Task',on_delete=models.PROTECT,related_name='it_operation')
    requested_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT,related_name='requested_it_operations')
    status=models.CharField(max_length=24,choices=[('REQUESTED','REQUESTED'),('SIMULATED_FULFILLED','SIMULATED_FULFILLED')],default='REQUESTED')
    requested_at=models.DateTimeField(default=timezone.now)
    simulated_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT,null=True,related_name='simulated_it_operations')
    simulated_at=models.DateTimeField(null=True)
    simulation_digest=models.CharField(max_length=64,blank=True,default='')
    note=models.CharField(max_length=300,blank=True,default='')
    class Meta:
        constraints=[models.CheckConstraint(condition=(
            models.Q(status='REQUESTED',simulated_by__isnull=True,simulated_at__isnull=True,simulation_digest='',note='')
            | models.Q(status='SIMULATED_FULFILLED',simulated_by__isnull=False,simulated_at__isnull=False)
        ),name='m4_it_operation_consistent_status')]
