"""Versioned S3 document pipeline; no private bytes in PostgreSQL.

Core upload intents, object receipts, scan attempts, clean promotion and HR
reviews are append-only. A scan result alone is not an HR approval.
"""
import uuid
from django.db import models
from django.utils import timezone

class SecureUpload(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.ForeignKey('onboarding.Task',on_delete=models.PROTECT,related_name='secure_uploads')
    revision=models.PositiveIntegerField()
    employee=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    sha256=models.CharField(max_length=64)
    byte_length=models.PositiveIntegerField()
    filename=models.CharField(max_length=120)
    mime=models.CharField(max_length=40,default='application/pdf')
    object_key=models.CharField(max_length=240,unique=True)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['task','revision'],name='m3_secure_document_revision_unique'),
            models.CheckConstraint(condition=models.Q(byte_length__gte=16,byte_length__lte=10485760,
                mime='application/pdf'),name='m3_secure_document_size_type'),
        ]
        ordering=['revision']

class StoredQuarantineObject(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    upload=models.OneToOneField(SecureUpload,on_delete=models.PROTECT,related_name='stored')
    version_id=models.CharField(max_length=200)
    stored_at=models.DateTimeField(default=timezone.now)

class SecureScanAttempt(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    upload=models.ForeignKey(SecureUpload,on_delete=models.PROTECT,related_name='secure_scans')
    number=models.PositiveSmallIntegerField()
    outcome=models.CharField(max_length=12,choices=[('CLEAN','CLEAN'),('MALWARE','MALWARE'),('ERROR','ERROR')])
    detail=models.CharField(max_length=120)
    scanner_version=models.CharField(max_length=150)
    scanned_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[
          models.UniqueConstraint(fields=['upload','number'],name='m3_secure_scan_attempt_unique'),
          models.CheckConstraint(condition=models.Q(number__gte=1,number__lte=3),name='m3_secure_scan_attempt_limit'),
          models.CheckConstraint(condition=models.Q(outcome__in=['CLEAN','MALWARE','ERROR']),name='m3_secure_scan_outcome'),
        ]

class SecureCleanObject(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    upload=models.OneToOneField(SecureUpload,on_delete=models.PROTECT,related_name='clean')
    scan=models.OneToOneField(SecureScanAttempt,on_delete=models.PROTECT)
    object_key=models.CharField(max_length=240,unique=True)
    version_id=models.CharField(max_length=200)
    promoted_at=models.DateTimeField(default=timezone.now)

class SecureHRReview(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    clean=models.OneToOneField(SecureCleanObject,on_delete=models.PROTECT,related_name='review')
    reviewer=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    decision=models.CharField(max_length=24,choices=[('ACCEPTED','ACCEPTED'),
         ('REJECTED','REJECTED'),('NEEDS_CLARIFICATION','NEEDS_CLARIFICATION')])
    note=models.CharField(max_length=500)
    reviewed_at=models.DateTimeField(default=timezone.now)
