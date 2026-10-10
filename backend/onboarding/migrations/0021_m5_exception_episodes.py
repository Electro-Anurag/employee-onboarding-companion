"""M5 additive exception episodes and DB-enforced append-only event provenance."""
import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations,models

IMMUTABILITY_SQL="""
CREATE OR REPLACE FUNCTION public.m5_exception_event_write_once()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'M5 exception event history is append only' USING ERRCODE = '23514';
END $$;
CREATE TRIGGER m5_exception_event_write_once
BEFORE UPDATE OR DELETE ON onboarding_caseexceptionevent
FOR EACH ROW EXECUTE FUNCTION public.m5_exception_event_write_once();

CREATE OR REPLACE FUNCTION public.m5_exception_task_scope_guard()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM onboarding_task t
        WHERE t.id = NEW.task_id AND t.case_id = NEW.case_id
    ) THEN
        RAISE EXCEPTION 'M5 exception task must belong to same case'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER m5_exception_task_scope_guard
BEFORE INSERT OR UPDATE OF task_id,case_id ON onboarding_caseexception
FOR EACH ROW EXECUTE FUNCTION public.m5_exception_task_scope_guard();
"""
REVERSE_SQL="""
DROP TRIGGER IF EXISTS m5_exception_task_scope_guard ON onboarding_caseexception;
DROP FUNCTION IF EXISTS public.m5_exception_task_scope_guard();
DROP TRIGGER IF EXISTS m5_exception_event_write_once ON onboarding_caseexceptionevent;
DROP FUNCTION IF EXISTS public.m5_exception_event_write_once();
"""

class Migration(migrations.Migration):
    dependencies=[('onboarding','0020_audit_existing_manager_completion_provenance')]
    operations=[
        migrations.CreateModel(name='CaseException',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,
                                   editable=False,serialize=False)),
            ('cause',models.CharField(max_length=32,choices=[
                ('PREREQUISITE_BLOCKED','PREREQUISITE_BLOCKED'),
                ('OWNER_UNAVAILABLE','OWNER_UNAVAILABLE'),
                ('TASK_OVERDUE','TASK_OVERDUE')])),
            ('episode',models.PositiveIntegerField()),
            ('status',models.CharField(max_length=12,default='OPEN',choices=[
                ('OPEN','OPEN'),('ASSIGNED','ASSIGNED'),
                ('RESOLVED','RESOLVED'),('CLOSED','CLOSED')])),
            ('reason',models.CharField(max_length=240)),
            ('opened_at',models.DateTimeField(default=django.utils.timezone.now)),
            ('resolved_at',models.DateTimeField(null=True)),
            ('closed_at',models.DateTimeField(null=True)),
            ('case',models.ForeignKey(to='onboarding.onboardingcase',
                on_delete=django.db.models.deletion.PROTECT,related_name='exceptions')),
            ('task',models.ForeignKey(to='onboarding.task',
                on_delete=django.db.models.deletion.PROTECT,related_name='exceptions')),
            ('assignee',models.ForeignKey(to='accounts.membership',null=True,
                on_delete=django.db.models.deletion.PROTECT,related_name='assigned_exceptions')),
            ('opened_by',models.ForeignKey(to='accounts.user',
                on_delete=django.db.models.deletion.PROTECT,related_name='opened_exceptions'))
        ],options={'indexes':[models.Index(fields=['case','status'],
                     name='m5_exception_case_status')]}),
        migrations.AddConstraint(model_name='caseexception',
            constraint=models.UniqueConstraint(fields=['case','task','cause','episode'],
                name='m5_exception_unique_episode')),
        migrations.AddConstraint(model_name='caseexception',
            constraint=models.UniqueConstraint(fields=['task','cause'],
                condition=models.Q(status__in=['OPEN','ASSIGNED','RESOLVED']),
                name='m5_exception_one_active_episode')),
        migrations.AddConstraint(model_name='caseexception',
            constraint=models.CheckConstraint(condition=models.Q(cause__in=[
                'PREREQUISITE_BLOCKED','OWNER_UNAVAILABLE','TASK_OVERDUE']),
                name='m5_exception_valid_cause')),
        migrations.AddConstraint(model_name='caseexception',
            constraint=models.CheckConstraint(condition=models.Q(status__in=[
                'OPEN','ASSIGNED','RESOLVED','CLOSED']),
                name='m5_exception_valid_status')),
        migrations.AddConstraint(model_name='caseexception',
            constraint=models.CheckConstraint(condition=models.Q(episode__gte=1),
                name='m5_exception_positive_episode')),
        migrations.CreateModel(name='CaseExceptionEvent',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,
                editable=False,serialize=False)),
            ('action',models.CharField(max_length=12,choices=[
                ('OPEN','OPEN'),('ASSIGN','ASSIGN'),
                ('RESOLVE','RESOLVE'),('CLOSE','CLOSE')])),
            ('previous_status',models.CharField(max_length=12,blank=True)),
            ('status',models.CharField(max_length=12)),
            ('note',models.CharField(max_length=240)),
            ('created_at',models.DateTimeField(default=django.utils.timezone.now)),
            ('exception',models.ForeignKey(to='onboarding.caseexception',
                on_delete=django.db.models.deletion.PROTECT,related_name='events')),
            ('actor',models.ForeignKey(to='accounts.user',
                on_delete=django.db.models.deletion.PROTECT))
        ],options={'indexes':[models.Index(fields=['exception','created_at'],
                     name='m5_exception_event_order')]}),
        migrations.RunSQL(IMMUTABILITY_SQL,REVERSE_SQL),
    ]
