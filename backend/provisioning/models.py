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

class ITConfirmation(models.Model):
    """Human IT acceptance of one immutable simulated provider operation."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    operation=models.OneToOneField(ITOperation,on_delete=models.PROTECT,related_name='confirmation')
    confirmed_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    simulation_digest=models.CharField(max_length=64)
    note=models.CharField(max_length=300)
    confirmed_at=models.DateTimeField(default=timezone.now)

class EquipmentReceipt(models.Model):
    """Employee receipt is distinct from provider simulation and IT confirmation."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.OneToOneField('onboarding.Task',on_delete=models.PROTECT,related_name='equipment_receipt')
    it_confirmation=models.OneToOneField(ITConfirmation,on_delete=models.PROTECT)
    accepted_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    note=models.CharField(max_length=300)
    received_at=models.DateTimeField(default=timezone.now)

class ITSimulationFailure(models.Model):
    """One immutable failure attempt. Does not represent external fulfillment."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    operation=models.ForeignKey(ITOperation,on_delete=models.PROTECT,related_name='failures')
    sequence=models.PositiveIntegerField()
    reported_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    cause=models.CharField(max_length=32,choices=[
        ('PROVIDER_UNAVAILABLE','PROVIDER_UNAVAILABLE'),
        ('SIMULATED_TIMEOUT','SIMULATED_TIMEOUT'),
        ('SIMULATED_REJECTION','SIMULATED_REJECTION')])
    note=models.CharField(max_length=300)
    reported_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['operation','sequence'],name='m4_it_failure_sequence_unique'),
            models.CheckConstraint(condition=models.Q(cause__in=[
                'PROVIDER_UNAVAILABLE','SIMULATED_TIMEOUT','SIMULATED_REJECTION']),
                name='m4_it_failure_valid_cause'),
            models.CheckConstraint(condition=models.Q(sequence__gte=1,sequence__lte=5),
                name='m4_it_failure_bounded_sequence'),
        ]
        ordering=['sequence']
