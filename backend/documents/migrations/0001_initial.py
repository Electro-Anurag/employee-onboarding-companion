"""M3 immutable synthetic document revisions and review evidence."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
SQL="""
CREATE OR REPLACE FUNCTION public.m3_guard_document_evidence()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'M3 document evidence immutable' USING ERRCODE='23514';
END; $$;
CREATE TRIGGER m3_document_revision_immutable BEFORE UPDATE OR DELETE
 ON public.documents_documentrevision FOR EACH ROW EXECUTE FUNCTION public.m3_guard_document_evidence();
CREATE TRIGGER m3_document_review_immutable BEFORE UPDATE OR DELETE
 ON public.documents_documentreview FOR EACH ROW EXECUTE FUNCTION public.m3_guard_document_evidence();
"""
REVERSE="""
DROP TRIGGER IF EXISTS m3_document_review_immutable ON public.documents_documentreview;
DROP TRIGGER IF EXISTS m3_document_revision_immutable ON public.documents_documentrevision;
DROP FUNCTION IF EXISTS public.m3_guard_document_evidence();
"""
class Migration(migrations.Migration):
    initial=True
    dependencies=[('onboarding','0013_policy_ack_completion'),('accounts','0002_security_constraints')]
    operations=[
      migrations.CreateModel(name='DocumentRevision',fields=[
        ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
        ('revision',models.PositiveIntegerField()),
        ('content',models.BinaryField()),
        ('content_sha256',models.CharField(max_length=64)),
        ('byte_length',models.PositiveIntegerField()),
        ('filename',models.CharField(max_length=80)),
        ('content_type',models.CharField(max_length=32,default='text/plain')),
        ('scan_status',models.CharField(max_length=32,default='VALIDATED_SYNTHETIC')),
        ('scan_profile',models.CharField(max_length=64,default='EXACT_SYNTHETIC_FIXTURE_V1')),
        ('uploaded_at',models.DateTimeField(default=timezone.now)),
        ('uploaded_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
        ('task',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='document_revisions',to='onboarding.task')),
      ],options={'ordering':['revision']}),
      migrations.CreateModel(name='DocumentReview',fields=[
        ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
        ('decision',models.CharField(max_length=32,choices=[('ACCEPTED','ACCEPTED'),('REJECTED','REJECTED'),('NEEDS_CLARIFICATION','NEEDS_CLARIFICATION')])),
        ('note',models.CharField(max_length=500)),
        ('reviewed_at',models.DateTimeField(default=timezone.now)),
        ('reviewed_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
        ('revision',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='review',to='documents.documentrevision')),
      ]),
      migrations.AddConstraint(model_name='documentrevision',constraint=models.UniqueConstraint(fields=('task','revision'),name='m3_document_task_revision_unique')),
      migrations.AddConstraint(model_name='documentrevision',constraint=models.CheckConstraint(condition=models.Q(scan_status='VALIDATED_SYNTHETIC',scan_profile='EXACT_SYNTHETIC_FIXTURE_V1',content_type='text/plain',byte_length__gte=1,byte_length__lte=4096),name='m3_document_synthetic_guard')),
      migrations.AddConstraint(model_name='documentreview',constraint=models.CheckConstraint(condition=models.Q(decision__in=['ACCEPTED','REJECTED','NEEDS_CLARIFICATION']),name='m3_document_review_decision_valid')),
      migrations.RunSQL(SQL,REVERSE),
    ]
