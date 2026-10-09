"""Extend the original M2 BEFORE INSERT typed completion guard to FORM evidence.

Migration 0010 added the new deferred guards; the M2 0006 immediate guard
also remains installed. CREATE OR REPLACE keeps its referencing trigger.
"""
from django.db import migrations
SQL="""
CREATE OR REPLACE FUNCTION public.m2_validate_task_completion()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE t uuid; k text; reviewer uuid; verdict text;
BEGIN
 SELECT kind INTO k FROM public.onboarding_task WHERE id=NEW.task_id FOR SHARE;
 IF NEW.evidence_type='MANAGER_PREPARATION' THEN
   SELECT a.task_id INTO t FROM public.onboarding_managerattestation a
     WHERE a.id=NEW.manager_attestation_id FOR SHARE;
   IF t IS DISTINCT FROM NEW.task_id OR k IS DISTINCT FROM 'MANAGER_PREPARATION'
   THEN
     RAISE EXCEPTION 'invalid manager evidence task' USING ERRCODE='23514';
   END IF;
 ELSIF NEW.evidence_type='FORM' THEN
   SELECT s.task_id,r.reviewed_by_id,r.decision INTO t,reviewer,verdict
     FROM public.forms_formreview r
     JOIN public.forms_formsubmission s ON s.id=r.submission_id
     WHERE r.id=NEW.form_review_id;
   IF t IS DISTINCT FROM NEW.task_id OR k IS DISTINCT FROM 'FORM'
      OR reviewer IS DISTINCT FROM NEW.completed_by_id
      OR verdict IS DISTINCT FROM 'ACCEPTED'
   THEN
     RAISE EXCEPTION 'invalid accepted form evidence task' USING ERRCODE='23514';
   END IF;
 ELSE
   RAISE EXCEPTION 'unsupported typed completion' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
"""
class Migration(migrations.Migration):
    dependencies=[('onboarding','0010_form_completion_evidence')]
    operations=[migrations.RunSQL(SQL)]
