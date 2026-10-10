"""Fail-closed historical provenance check for databases with 0019 already applied.

0019 acquired a preflight in a later source revision. A database which
recorded the earlier 0019 will not rerun that revised preflight. This new,
independent, forward-only migration runs in both installation histories.
"""
from django.db import migrations

SQL="""
DO $m4_existing_provenance$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.onboarding_taskcompletion completion
    LEFT JOIN public.onboarding_managerattestation att
      ON att.id=completion.manager_attestation_id
    WHERE completion.evidence_type='MANAGER_PREPARATION'
      AND (att.id IS NULL OR att.task_id IS DISTINCT FROM completion.task_id
           OR att.actor_id IS DISTINCT FROM completion.completed_by_id)
  ) THEN
    RAISE EXCEPTION 'historical manager actor mismatch blocks provenance validation'
      USING ERRCODE='23514';
  END IF;
END; $m4_existing_provenance$;
"""

class Migration(migrations.Migration):
    dependencies=[('onboarding','0019_restore_manager_actor_provenance')]
    # Validation has no inverse side effect. Reversing does not erase evidence
    # or disable the already installed 0019 insert guard.
    operations=[migrations.RunSQL(SQL,migrations.RunSQL.noop)]
