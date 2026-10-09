"""Append-only schedule revisions and attendance decisions."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
SQL="""
CREATE OR REPLACE FUNCTION public.m4_guard_activity_evidence()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'Activity occurrence and attendance history immutable' USING ERRCODE='23514';
END; $$;
CREATE TRIGGER m4_occurrence_immutable BEFORE UPDATE OR DELETE ON public.activities_activityoccurrence
 FOR EACH ROW EXECUTE FUNCTION public.m4_guard_activity_evidence();
CREATE TRIGGER m4_attendance_immutable BEFORE UPDATE OR DELETE ON public.activities_activityattendance
 FOR EACH ROW EXECUTE FUNCTION public.m4_guard_activity_evidence();
"""
REVERSE="""
DROP TRIGGER IF EXISTS m4_attendance_immutable ON public.activities_activityattendance;
DROP TRIGGER IF EXISTS m4_occurrence_immutable ON public.activities_activityoccurrence;
DROP FUNCTION IF EXISTS public.m4_guard_activity_evidence();
"""
class Migration(migrations.Migration):
    initial=True
    dependencies=[('onboarding','0015_training_completion'),('accounts','0002_security_constraints')]
    operations=[
        migrations.CreateModel(name='ActivityOccurrence',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('revision',models.PositiveIntegerField()),
            ('begins_at',models.DateTimeField()),
            ('ends_at',models.DateTimeField()),
            ('medium',models.CharField(max_length=16,choices=[('VIDEO','VIDEO'),('IN_PERSON','IN_PERSON')])),
            ('meeting_reference',models.CharField(max_length=160)),
            ('reason',models.CharField(max_length=300)),
            ('scheduled_at',models.DateTimeField(default=timezone.now)),
            ('scheduled_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='scheduled_occurrences',to='accounts.user')),
            ('task',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='activity_occurrences',to='onboarding.task')),
        ],options={'ordering':['revision']}),
        migrations.CreateModel(name='ActivityAttendance',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('outcome',models.CharField(max_length=16,choices=[('ATTENDED','ATTENDED'),('MISSED','MISSED')])),
            ('note',models.CharField(max_length=500)),
            ('recorded_at',models.DateTimeField(default=timezone.now)),
            ('occurrence',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='attendance',to='activities.activityoccurrence')),
            ('recorded_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
        ]),
        migrations.AddConstraint(model_name='activityoccurrence',constraint=models.UniqueConstraint(fields=('task','revision'),name='m4_activity_task_revision_unique')),
        migrations.AddConstraint(model_name='activityoccurrence',constraint=models.CheckConstraint(condition=models.Q(ends_at__gt=models.F('begins_at')),name='m4_activity_positive_duration')),
        migrations.AddConstraint(model_name='activityoccurrence',constraint=models.CheckConstraint(condition=models.Q(medium__in=['VIDEO','IN_PERSON']),name='m4_activity_valid_medium')),
        migrations.AddConstraint(model_name='activityattendance',constraint=models.CheckConstraint(condition=models.Q(outcome__in=['ATTENDED','MISSED']),name='m4_activity_attendance_outcome_valid')),
        migrations.RunSQL(SQL,REVERSE),
    ]
