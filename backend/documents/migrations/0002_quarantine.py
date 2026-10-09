"""Append-only, size-bounded local quarantine and scanner attempt history."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone

SQL="""
CREATE OR REPLACE FUNCTION public.m3_guard_quarantine_immutable()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'Quarantine evidence is immutable' USING ERRCODE='23514';
END; $$;
CREATE TRIGGER m3_quarantine_bytes_immutable BEFORE UPDATE OR DELETE
 ON public.documents_quarantineddocument FOR EACH ROW
 EXECUTE FUNCTION public.m3_guard_quarantine_immutable();
CREATE TRIGGER m3_quarantine_scan_immutable BEFORE UPDATE OR DELETE
 ON public.documents_quarantinescanattempt FOR EACH ROW
 EXECUTE FUNCTION public.m3_guard_quarantine_immutable();
"""
REVERSE="""
DROP TRIGGER IF EXISTS m3_quarantine_scan_immutable ON public.documents_quarantinescanattempt;
DROP TRIGGER IF EXISTS m3_quarantine_bytes_immutable ON public.documents_quarantineddocument;
DROP FUNCTION IF EXISTS public.m3_guard_quarantine_immutable();
"""
class Migration(migrations.Migration):
    dependencies=[('documents','0001_initial')]
    operations=[
        migrations.CreateModel(name='QuarantinedDocument',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('quarantined_bytes',models.BinaryField()),
            ('content_sha256',models.CharField(max_length=64)),
            ('byte_length',models.PositiveIntegerField()),
            ('declared_type',models.CharField(max_length=40)),
            ('uploaded_at',models.DateTimeField(default=timezone.now)),
            ('task',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                related_name='quarantine_uploads',to='onboarding.task')),
            ('uploaded_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
        ]),
        migrations.CreateModel(name='QuarantineScanAttempt',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('attempt',models.PositiveIntegerField()),
            ('outcome',models.CharField(max_length=16,choices=[
                ('CLEAN','CLEAN'),('MALWARE','MALWARE'),('ERROR','ERROR')])),
            ('detail',models.CharField(max_length=80)),
            ('engine',models.CharField(max_length=32,default='CLAMAV_INSTREAM')),
            ('scanned_at',models.DateTimeField(default=timezone.now)),
            ('upload',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                related_name='scan_attempts',to='documents.quarantineddocument')),
        ]),
        migrations.AddConstraint(model_name='quarantineddocument',constraint=models.CheckConstraint(
            condition=models.Q(byte_length__gte=1,byte_length__lte=262144),
            name='m3_quarantine_byte_limit')),
        migrations.AddConstraint(model_name='quarantinescanattempt',constraint=models.UniqueConstraint(
            fields=('upload','attempt'),name='m3_quarantine_scan_attempt_unique')),
        migrations.AddConstraint(model_name='quarantinescanattempt',constraint=models.CheckConstraint(
            condition=models.Q(attempt__gte=1,attempt__lte=3),
            name='m3_quarantine_scan_attempt_bounded')),
        migrations.AddConstraint(model_name='quarantinescanattempt',constraint=models.CheckConstraint(
            condition=models.Q(outcome__in=['CLEAN','MALWARE','ERROR'],
                engine='CLAMAV_INSTREAM'),name='m3_quarantine_scanner_outcome_valid')),
        migrations.RunSQL(SQL,REVERSE),
    ]
