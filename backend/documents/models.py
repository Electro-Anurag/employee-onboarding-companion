"""Immutable exact-fixture document revisions and HR decisions.

Bytes are restricted to two canonical synthetic plain text examples. Arbitrary
PDFs and genuine employee documents are not accepted by this feature slice.
"""
import uuid
from django.db import models
from django.utils import timezone

class DocumentRevision(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.ForeignKey('onboarding.Task',on_delete=models.PROTECT,related_name='document_revisions')
    revision=models.PositiveIntegerField()
    uploaded_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    content=models.BinaryField()
    content_sha256=models.CharField(max_length=64)
    byte_length=models.PositiveIntegerField()
    filename=models.CharField(max_length=80)
    content_type=models.CharField(max_length=32,default='text/plain')
    scan_status=models.CharField(max_length=32,default='VALIDATED_SYNTHETIC')
    scan_profile=models.CharField(max_length=64,default='EXACT_SYNTHETIC_FIXTURE_V1')
    uploaded_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[
           models.UniqueConstraint(fields=['task','revision'],name='m3_document_task_revision_unique'),
           models.CheckConstraint(condition=models.Q(scan_status='VALIDATED_SYNTHETIC',scan_profile='EXACT_SYNTHETIC_FIXTURE_V1',
                                                    content_type='text/plain',byte_length__gte=1,byte_length__lte=4096),
                                  name='m3_document_synthetic_guard'),
        ]
        ordering=['revision']

class DocumentReview(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    revision=models.OneToOneField(DocumentRevision,on_delete=models.PROTECT,related_name='review')
    reviewed_by=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    decision=models.CharField(max_length=32,choices=[(v,v) for v in ('ACCEPTED','REJECTED','NEEDS_CLARIFICATION')])
    note=models.CharField(max_length=500)
    reviewed_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(decision__in=['ACCEPTED','REJECTED','NEEDS_CLARIFICATION']),
                                            name='m3_document_review_decision_valid')]
