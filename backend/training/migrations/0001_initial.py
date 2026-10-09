"""Immutable synthetic training attempts."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
SQL="""
CREATE OR REPLACE FUNCTION public.m4_training_attempt_immutable()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'M4 training attempt is immutable' USING ERRCODE='23514';
END; $$;
CREATE TRIGGER m4_training_attempt_immutable BEFORE UPDATE OR DELETE
 ON public.training_trainingattempt FOR EACH ROW EXECUTE FUNCTION public.m4_training_attempt_immutable();
"""
REVERSE="""
DROP TRIGGER IF EXISTS m4_training_attempt_immutable ON public.training_trainingattempt;
DROP FUNCTION IF EXISTS public.m4_training_attempt_immutable();
"""
class Migration(migrations.Migration):
    initial=True
    dependencies=[('onboarding','0014_synthetic_document_completion'),('accounts','0002_security_constraints')]
    operations=[
        migrations.CreateModel(name='TrainingAttempt',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('attempt_number',models.PositiveIntegerField()),
            ('module_version',models.CharField(max_length=80)),
            ('content_sha256',models.CharField(max_length=64)),
            ('answers',models.JSONField()),
            ('score',models.PositiveIntegerField()),
            ('passing_score',models.PositiveIntegerField()),
            ('passed',models.BooleanField()),
            ('submitted_at',models.DateTimeField(default=timezone.now)),
            ('actor',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
            ('task',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='training_attempts',to='onboarding.task')),
        ],options={'ordering':['attempt_number']}),
        migrations.AddConstraint(model_name='trainingattempt',constraint=models.UniqueConstraint(fields=('task','attempt_number'),name='m4_training_attempt_sequence_unique')),
        migrations.AddConstraint(model_name='trainingattempt',constraint=models.CheckConstraint(condition=models.Q(passing_score__gte=1,score__lte=models.F('passing_score')),name='m4_training_score_bounded')),
        migrations.RunSQL(SQL,REVERSE),
    ]
