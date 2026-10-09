"""M3 immutable submitted form revisions and HR decisions."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
SQL="""
CREATE OR REPLACE FUNCTION public.m3_guard_form_evidence()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'M3 form evidence is immutable' USING ERRCODE='23514';
END; $$;
CREATE TRIGGER m3_form_submission_immutable BEFORE UPDATE OR DELETE
 ON public.forms_formsubmission FOR EACH ROW EXECUTE FUNCTION public.m3_guard_form_evidence();
CREATE TRIGGER m3_form_review_immutable BEFORE UPDATE OR DELETE
 ON public.forms_formreview FOR EACH ROW EXECUTE FUNCTION public.m3_guard_form_evidence();
"""
REVERSE="""
DROP TRIGGER IF EXISTS m3_form_review_immutable ON public.forms_formreview;
DROP TRIGGER IF EXISTS m3_form_submission_immutable ON public.forms_formsubmission;
DROP FUNCTION IF EXISTS public.m3_guard_form_evidence();
"""
class Migration(migrations.Migration):
    initial=True
    dependencies=[('onboarding','0009_irreversible_activated_case'),('accounts','0002_security_constraints')]
    operations=[
        migrations.CreateModel(name='FormSubmission',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('revision',models.PositiveIntegerField()),
            ('answers',models.JSONField()),
            ('content_hash',models.CharField(max_length=64)),
            ('submitted_at',models.DateTimeField(default=timezone.now)),
            ('submitted_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
            ('task',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='form_submissions',to='onboarding.task'))
        ],options={'ordering':['revision']}),
        migrations.CreateModel(name='FormReview',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('decision',models.CharField(max_length=24,choices=[('ACCEPTED','ACCEPTED'),('CHANGES_REQUESTED','CHANGES_REQUESTED')])),
            ('note',models.CharField(max_length=500)),
            ('reviewed_at',models.DateTimeField(default=timezone.now)),
            ('reviewed_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
            ('submission',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='review',to='forms.formsubmission'))
        ]),
        migrations.AddConstraint(model_name='formsubmission',constraint=models.UniqueConstraint(fields=('task','revision'),name='m3_form_task_revision_unique')),
        migrations.AddConstraint(model_name='formreview',constraint=models.CheckConstraint(condition=models.Q(decision__in=['ACCEPTED','CHANGES_REQUESTED']),name='m3_form_valid_review')),
        migrations.RunSQL(SQL,REVERSE),
    ]
