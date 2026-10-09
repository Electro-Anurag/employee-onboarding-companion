"""Immutable, isolated quarantine. No document task-completion or release path."""
import uuid
from django.db import models
from django.utils import timezone

class QuarantinedDocument(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.ForeignKey('onboarding.Task',on_delete=models.PROTECT,related_name='quarantine_uploads')
    uploaded_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    # Bounded bytes remain in PostgreSQL only for this local qualification slice.
    # S3/private object storage must replace this before real employee deployment.
    quarantined_bytes=models.BinaryField()
    content_sha256=models.CharField(max_length=64)
    byte_length=models.PositiveIntegerField()
    declared_type=models.CharField(max_length=40)
    uploaded_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.CheckConstraint(
            condition=models.Q(byte_length__gte=1,byte_length__lte=262144),
            name='m3_quarantine_byte_limit')]

class QuarantineScanAttempt(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    upload=models.ForeignKey(QuarantinedDocument,on_delete=models.PROTECT,related_name='scan_attempts')
    attempt=models.PositiveIntegerField()
    outcome=models.CharField(max_length=16,choices=[
        ('CLEAN','CLEAN'),('MALWARE','MALWARE'),('ERROR','ERROR')])
    detail=models.CharField(max_length=80)
    engine=models.CharField(max_length=32,default='CLAMAV_INSTREAM')
    scanned_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['upload','attempt'],name='m3_quarantine_scan_attempt_unique'),
            models.CheckConstraint(condition=models.Q(attempt__gte=1,attempt__lte=3),
                name='m3_quarantine_scan_attempt_bounded'),
            models.CheckConstraint(condition=models.Q(outcome__in=['CLEAN','MALWARE','ERROR'],
                engine='CLAMAV_INSTREAM'),name='m3_quarantine_scanner_outcome_valid')]
