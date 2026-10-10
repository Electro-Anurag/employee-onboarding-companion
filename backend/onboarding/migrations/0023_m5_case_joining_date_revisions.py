"""Additive, durable M5 HR date-change decisions and schedule revisions."""
import uuid
from django.db import migrations,models
import django.db.models.deletion
import django.utils.timezone

PROTECT_SQL="""
CREATE OR REPLACE FUNCTION public.m5_date_change_write_once()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'M5 joining-date change history is append only'
        USING ERRCODE = '23514';
END $$;
CREATE TRIGGER m5_date_change_write_once
BEFORE UPDATE OR DELETE ON onboarding_casedatechange
FOR EACH ROW EXECUTE FUNCTION public.m5_date_change_write_once();

CREATE OR REPLACE FUNCTION public.m5_date_change_case_guard()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM onboarding_onboardingcase c
        WHERE c.id = NEW.case_id AND c.joining_date=NEW.joining_date
          AND c.schedule_revision=NEW.revision
    ) THEN
        RAISE EXCEPTION 'M5 joining-date evidence does not match current case'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER m5_date_change_case_guard
BEFORE INSERT ON onboarding_casedatechange
FOR EACH ROW EXECUTE FUNCTION public.m5_date_change_case_guard();
"""
REVERSE_SQL="""
DROP TRIGGER IF EXISTS m5_date_change_case_guard ON onboarding_casedatechange;
DROP FUNCTION IF EXISTS public.m5_date_change_case_guard();
DROP TRIGGER IF EXISTS m5_date_change_write_once ON onboarding_casedatechange;
DROP FUNCTION IF EXISTS public.m5_date_change_write_once();
"""

class Migration(migrations.Migration):
    dependencies=[('onboarding','0022_m5_recurred_exception_supersession')]
    operations=[
        migrations.AddField(model_name='onboardingcase',name='schedule_revision',
            field=models.PositiveIntegerField(default=0)),
        migrations.CreateModel(name='CaseDateChange',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,
                editable=False,serialize=False)),
            ('revision',models.PositiveIntegerField()),
            ('prior_date',models.DateField()),
            ('joining_date',models.DateField()),
            ('preview_digest',models.CharField(max_length=64)),
            ('reason',models.CharField(max_length=240)),
            ('changes',models.JSONField(default=list)),
            ('preserved_task_ids',models.JSONField(default=list)),
            ('created_at',models.DateTimeField(default=django.utils.timezone.now)),
            ('case',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                related_name='date_changes',to='onboarding.onboardingcase')),
            ('changed_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                to='accounts.user')),
        ],options={'indexes':[models.Index(fields=['case','created_at'],
            name='m5_schedule_change_order')]}),
        migrations.AddConstraint(model_name='casedatechange',
            constraint=models.UniqueConstraint(fields=['case','revision'],
                name='m5_schedule_revision_unique')),
        migrations.AddConstraint(model_name='casedatechange',
            constraint=models.CheckConstraint(condition=models.Q(revision__gte=1),
                name='m5_schedule_revision_positive')),
        migrations.RunSQL(PROTECT_SQL,REVERSE_SQL),
    ]
