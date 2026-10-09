"""Private S3 document intents, exact versions, scan provenance and human review."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone

SQL="""
CREATE OR REPLACE FUNCTION public.m3_guard_object_evidence_immutable()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
  RAISE EXCEPTION 'M3 S3 object document evidence immutable' USING ERRCODE='23514';
END; $$;
CREATE TRIGGER m3_secure_upload_immutable BEFORE UPDATE OR DELETE ON public.documents_secureupload
 FOR EACH ROW EXECUTE FUNCTION public.m3_guard_object_evidence_immutable();
CREATE TRIGGER m3_secure_stored_immutable BEFORE UPDATE OR DELETE ON public.documents_storedquarantineobject
 FOR EACH ROW EXECUTE FUNCTION public.m3_guard_object_evidence_immutable();
CREATE TRIGGER m3_secure_scan_immutable BEFORE UPDATE OR DELETE ON public.documents_securescanattempt
 FOR EACH ROW EXECUTE FUNCTION public.m3_guard_object_evidence_immutable();
CREATE TRIGGER m3_secure_clean_immutable BEFORE UPDATE OR DELETE ON public.documents_securecleanobject
 FOR EACH ROW EXECUTE FUNCTION public.m3_guard_object_evidence_immutable();
CREATE TRIGGER m3_secure_review_immutable BEFORE UPDATE OR DELETE ON public.documents_securehrreview
 FOR EACH ROW EXECUTE FUNCTION public.m3_guard_object_evidence_immutable();
"""
class Migration(migrations.Migration):
    dependencies=[('documents','0002_quarantine'),('onboarding','0016_activity_completion')]
    operations=[
        migrations.CreateModel(name='SecureUpload',fields=[
            ('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
            ('revision',models.PositiveIntegerField()),
            ('sha256',models.CharField(max_length=64)),
            ('byte_length',models.PositiveIntegerField()),
            ('filename',models.CharField(max_length=120)),
            ('mime',models.CharField(default='application/pdf',max_length=40)),
            ('object_key',models.CharField(max_length=240,unique=True)),
            ('created_at',models.DateTimeField(default=timezone.now)),
            ('employee',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
            ('task',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='secure_uploads',to='onboarding.task')),
        ],options={'ordering':['revision']}),
        migrations.CreateModel(name='StoredQuarantineObject',fields=[
            ('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
            ('version_id',models.CharField(max_length=200)),
            ('stored_at',models.DateTimeField(default=timezone.now)),
            ('upload',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='stored',to='documents.secureupload')),
        ]),
        migrations.CreateModel(name='SecureScanAttempt',fields=[
            ('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
            ('number',models.PositiveSmallIntegerField()),
            ('outcome',models.CharField(max_length=12,choices=[('CLEAN','CLEAN'),('MALWARE','MALWARE'),('ERROR','ERROR')])),
            ('detail',models.CharField(max_length=120)),
            ('scanner_version',models.CharField(max_length=150)),
            ('scanned_at',models.DateTimeField(default=timezone.now)),
            ('upload',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='secure_scans',to='documents.secureupload')),
        ]),
        migrations.CreateModel(name='SecureCleanObject',fields=[
            ('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
            ('object_key',models.CharField(max_length=240,unique=True)),
            ('version_id',models.CharField(max_length=200)),
            ('promoted_at',models.DateTimeField(default=timezone.now)),
            ('scan',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,to='documents.securescanattempt')),
            ('upload',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='clean',to='documents.secureupload')),
        ]),
        migrations.CreateModel(name='SecureHRReview',fields=[
            ('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
            ('decision',models.CharField(max_length=24,choices=[
                ('ACCEPTED','ACCEPTED'),('REJECTED','REJECTED'),
                ('NEEDS_CLARIFICATION','NEEDS_CLARIFICATION')])),
            ('note',models.CharField(max_length=500)),
            ('reviewed_at',models.DateTimeField(default=timezone.now)),
            ('clean',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='review',to='documents.securecleanobject')),
            ('reviewer',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
        ]),
        migrations.AddConstraint(model_name='secureupload',constraint=models.UniqueConstraint(
            fields=('task','revision'),name='m3_secure_document_revision_unique')),
        migrations.AddConstraint(model_name='secureupload',constraint=models.CheckConstraint(
            condition=models.Q(byte_length__gte=16,byte_length__lte=10485760,mime='application/pdf'),
            name='m3_secure_document_size_type')),
        migrations.AddConstraint(model_name='securescanattempt',constraint=models.UniqueConstraint(
            fields=('upload','number'),name='m3_secure_scan_attempt_unique')),
        migrations.AddConstraint(model_name='securescanattempt',constraint=models.CheckConstraint(
            condition=models.Q(number__gte=1,number__lte=3),name='m3_secure_scan_attempt_limit')),
        migrations.AddConstraint(model_name='securescanattempt',constraint=models.CheckConstraint(
            condition=models.Q(outcome__in=['CLEAN','MALWARE','ERROR']),name='m3_secure_scan_outcome')),
        migrations.RunSQL(SQL),
    ]
