"""Restore actor equality lost when multi-kind completion SQL replaced M2 checks.

Additive, narrow insert guard; does not replace or weaken any M3/M4 evidence
branch or rewrite historical evidence.
"""
from django.db import migrations

SQL="""
-- Before installing the new guard, reject any existing contradictory
-- attribution. Historical evidence is immutable: never rewrite it silently.
DO $m3_provenance_upgrade$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.onboarding_taskcompletion completion
    LEFT JOIN public.onboarding_managerattestation att
      ON att.id=completion.manager_attestation_id
    WHERE completion.evidence_type='MANAGER_PREPARATION'
      AND (att.id IS NULL OR att.task_id IS DISTINCT FROM completion.task_id
           OR att.actor_id IS DISTINCT FROM completion.completed_by_id)
  ) THEN
    RAISE EXCEPTION 'historical manager actor mismatch blocks provenance upgrade'
      USING ERRCODE='23514';
  END IF;
END; $m3_provenance_upgrade$;
CREATE OR REPLACE FUNCTION public.m3_guard_manager_completion_actor()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
  IF NEW.evidence_type='MANAGER_PREPARATION' AND NOT EXISTS (
    SELECT 1 FROM public.onboarding_managerattestation att
    WHERE att.id=NEW.manager_attestation_id
      AND att.task_id=NEW.task_id
      AND att.actor_id=NEW.completed_by_id
  ) THEN
    RAISE EXCEPTION 'manager completion actor does not match attestation'
      USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER m3_manager_completion_actor_provenance
BEFORE INSERT ON public.onboarding_taskcompletion
FOR EACH ROW EXECUTE FUNCTION public.m3_guard_manager_completion_actor();
"""
REVERSE="""
DROP TRIGGER IF EXISTS m3_manager_completion_actor_provenance ON public.onboarding_taskcompletion;
DROP FUNCTION IF EXISTS public.m3_guard_manager_completion_actor();
"""

class Migration(migrations.Migration):
    dependencies=[('onboarding','0018_restore_activity_cancellation_authority')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
