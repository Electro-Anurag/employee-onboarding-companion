"""M5 additive, narrowly evidenced schedule exception to M2 snapshot immutability.

No older migration is modified. Identity, topology, terminal task history,
template provenance, and all direct arbitrary schedule writes stay forbidden.
Only one exact predeclared HR case-date decision can shift untouched tasks.
"""
from django.db import migrations

SQL=r"""
CREATE OR REPLACE FUNCTION public.m5_exact_authorized_reschedule(
    before_task public.onboarding_task,
    after_task public.onboarding_task
)
RETURNS boolean LANGUAGE plpgsql
SET search_path=pg_catalog,public AS $$
DECLARE
    d public.onboarding_casedatechange%ROWTYPE;
    c public.onboarding_onboardingcase%ROWTYPE;
    tt public.templates_templatetask%ROWTYPE;
    zone text;
    has_approved_actor boolean;
    declared_change boolean;
    expected_start timestamptz;
    expected_due timestamptz;
BEGIN
    IF before_task.work_started_at IS NOT NULL
       OR before_task.completed_at IS NOT NULL
       OR before_task.execution_state IN ('COMPLETED','CANCELLED')
       OR after_task.work_started_at IS DISTINCT FROM before_task.work_started_at
       OR after_task.completed_at IS DISTINCT FROM before_task.completed_at
       OR after_task.execution_state IS DISTINCT FROM before_task.execution_state
       OR after_task.version IS DISTINCT FROM before_task.version+1
    THEN RETURN FALSE; END IF;

    SELECT * INTO c FROM public.onboarding_onboardingcase
      WHERE id=before_task.case_id;
    IF NOT FOUND OR c.status IS DISTINCT FROM 'PRE_JOINING'
      OR c.schedule_revision<1 THEN RETURN FALSE; END IF;
    SELECT * INTO d FROM public.onboarding_casedatechange
      WHERE case_id=c.id AND revision=c.schedule_revision
        AND joining_date=c.joining_date;
    IF NOT FOUND THEN RETURN FALSE; END IF;

    SELECT EXISTS (
      SELECT 1 FROM public.onboarding_caseassignment a
      JOIN public.accounts_membership m ON m.id=a.member_id
      JOIN public.accounts_user u ON u.id=m.user_id
      WHERE a.case_id=c.id AND a.role='HR'
        AND a.effective_to IS NULL AND a.effective_from<=d.created_at
        AND m.role='HR' AND m.organization_id=c.organization_id
        AND m.active AND m.available AND u.is_active
        AND u.id=d.changed_by_id
    ) INTO has_approved_actor;
    IF NOT has_approved_actor THEN RETURN FALSE; END IF;
    IF length(btrim(d.reason))<8 OR length(d.preview_digest)<>64
       THEN RETURN FALSE; END IF;

    SELECT * INTO tt FROM public.templates_templatetask
      WHERE id=before_task.template_task_id AND version_id=c.template_version_id;
    IF NOT FOUND THEN RETURN FALSE; END IF;
    SELECT timezone INTO zone FROM public.accounts_organization WHERE id=c.organization_id;
    IF zone IS NULL THEN RETURN FALSE; END IF;

    expected_start := ((c.joining_date+tt.available_offset_days)
                       + tt.available_local_time::time) AT TIME ZONE zone;
    expected_due := ((c.joining_date+tt.due_offset_days)
                     + tt.due_local_time::time) AT TIME ZONE zone;
    IF after_task.available_at IS DISTINCT FROM expected_start
       OR after_task.due_at IS DISTINCT FROM expected_due
       OR expected_start>expected_due
    THEN RETURN FALSE; END IF;

    SELECT EXISTS (
      SELECT 1
      FROM jsonb_array_elements(d.changes) AS change
      WHERE change->>'task_id'=before_task.id::text
        AND (change->>'old_available_at')::timestamptz=before_task.available_at
        AND (change->>'old_due_at')::timestamptz=before_task.due_at
        AND (change->>'new_available_at')::timestamptz=after_task.available_at
        AND (change->>'new_due_at')::timestamptz=after_task.due_at
    ) INTO declared_change;
    RETURN declared_change;
EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow
          OR invalid_parameter_value OR invalid_text_representation THEN
    RETURN FALSE;
END; $$;

-- Extend, never weaken, the M2 guard's two disjoint categories:
-- (1) snapshot identity ALWAYS immutable and
-- (2) schedule mutable ONLY through the tightly evidenced M5 exception.
CREATE OR REPLACE FUNCTION public.m2_guard_task_snapshot()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE cstatus text; cversion uuid; tv uuid;
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'M2 task snapshot may not be deleted' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' THEN
   IF (NEW.case_id,NEW.template_task_id,NEW.key,NEW.kind,NEW.title,
       NEW.description,NEW.owner_role,NEW.required,NEW.applicable,NEW.evidence_spec)
      IS DISTINCT FROM
      (OLD.case_id,OLD.template_task_id,OLD.key,OLD.kind,OLD.title,
       OLD.description,OLD.owner_role,OLD.required,OLD.applicable,OLD.evidence_spec)
   THEN RAISE EXCEPTION 'M2 task snapshot identity immutable'
        USING ERRCODE='23514';
   END IF;
   IF (NEW.available_at,NEW.due_at)
      IS DISTINCT FROM (OLD.available_at,OLD.due_at)
      AND NOT public.m5_exact_authorized_reschedule(OLD,NEW)
   THEN RAISE EXCEPTION 'M2 task snapshot identity/schedule immutable'
        USING ERRCODE='23514';
   END IF;
   IF OLD.execution_state IN ('COMPLETED','CANCELLED')
       AND (NEW.execution_state IS DISTINCT FROM OLD.execution_state
            OR NEW.completed_at IS DISTINCT FROM OLD.completed_at
            OR NEW.work_started_at IS DISTINCT FROM OLD.work_started_at)
   THEN RAISE EXCEPTION 'M2 terminal task evidence metadata immutable'
        USING ERRCODE='23514';
   END IF;
   RETURN NEW;
 END IF;
 SELECT status,template_version_id INTO cstatus,cversion
   FROM public.onboarding_onboardingcase WHERE id=NEW.case_id FOR SHARE;
 SELECT version_id INTO tv FROM public.templates_templatetask
   WHERE id=NEW.template_task_id FOR SHARE;
 IF cstatus IS DISTINCT FROM 'CREATED' OR tv IS DISTINCT FROM cversion THEN
   RAISE EXCEPTION 'M2 task must instantiate on matching CREATED case'
     USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
"""

REVERSE_SQL=r"""
-- Source-equivalent restoration of the last 0008 task guard at downgrade.
CREATE OR REPLACE FUNCTION public.m2_guard_task_snapshot()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE cstatus text; cversion uuid; tv uuid;
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'M2 task snapshot may not be deleted' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' THEN
   IF (NEW.case_id,NEW.template_task_id,NEW.key,NEW.kind,NEW.title,
       NEW.description,NEW.owner_role,NEW.required,NEW.applicable,NEW.evidence_spec,
       NEW.available_at,NEW.due_at)
      IS DISTINCT FROM
      (OLD.case_id,OLD.template_task_id,OLD.key,OLD.kind,OLD.title,
       OLD.description,OLD.owner_role,OLD.required,OLD.applicable,OLD.evidence_spec,
       OLD.available_at,OLD.due_at)
   THEN RAISE EXCEPTION 'M2 task snapshot identity/schedule immutable'
        USING ERRCODE='23514';
   END IF;
   IF OLD.execution_state IN ('COMPLETED','CANCELLED')
       AND (NEW.execution_state IS DISTINCT FROM OLD.execution_state
            OR NEW.completed_at IS DISTINCT FROM OLD.completed_at
            OR NEW.work_started_at IS DISTINCT FROM OLD.work_started_at)
   THEN RAISE EXCEPTION 'M2 terminal task evidence metadata immutable'
        USING ERRCODE='23514';
   END IF;
   RETURN NEW;
 END IF;
 SELECT status,template_version_id INTO cstatus,cversion
   FROM public.onboarding_onboardingcase WHERE id=NEW.case_id FOR SHARE;
 SELECT version_id INTO tv FROM public.templates_templatetask
   WHERE id=NEW.template_task_id FOR SHARE;
 IF cstatus IS DISTINCT FROM 'CREATED' OR tv IS DISTINCT FROM cversion THEN
   RAISE EXCEPTION 'M2 task must instantiate on matching CREATED case'
     USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
DROP FUNCTION IF EXISTS public.m5_exact_authorized_reschedule(
    public.onboarding_task,public.onboarding_task);
"""

class Migration(migrations.Migration):
    dependencies=[('onboarding','0023_m5_case_joining_date_revisions')]
    operations=[migrations.RunSQL(SQL,REVERSE_SQL)]
