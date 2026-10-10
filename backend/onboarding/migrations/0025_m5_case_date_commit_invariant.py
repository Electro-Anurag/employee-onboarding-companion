"""M5 additive deferred case-date invariant: direct SQL cannot redate an active snapshot.

The M5 commit deliberately writes the case before its decision and shifted
task rows, all in one transaction. This deferred constraint validates the
complete authoritative evidence at COMMIT, not halfway through the command.
"""
from django.db import migrations

SQL=r"""
CREATE OR REPLACE FUNCTION public.m5_guard_case_date_revision()
RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,public AS $$
DECLARE valid_decision boolean;
BEGIN
 IF OLD.status IS DISTINCT FROM 'PRE_JOINING'
    OR NEW.status IS DISTINCT FROM 'PRE_JOINING'
    OR NEW.joining_date IS NOT DISTINCT FROM OLD.joining_date
    OR NEW.schedule_revision IS DISTINCT FROM OLD.schedule_revision+1
    OR NEW.version <= OLD.version
 THEN
    RAISE EXCEPTION 'M5 joining-date change requires approved pre-join revision'
        USING ERRCODE='23514';
 END IF;
 SELECT EXISTS (
   SELECT 1 FROM public.onboarding_casedatechange d
   JOIN public.onboarding_caseassignment a
     ON a.case_id=d.case_id AND a.role='HR' AND a.effective_to IS NULL
       AND a.effective_from<=d.created_at
   JOIN public.accounts_membership m
     ON m.id=a.member_id AND m.role='HR'
       AND m.organization_id=NEW.organization_id AND m.active AND m.available
   JOIN public.accounts_user u
     ON u.id=m.user_id AND u.is_active
   WHERE d.case_id=NEW.id AND d.revision=NEW.schedule_revision
     AND d.prior_date=OLD.joining_date
     AND d.joining_date=NEW.joining_date
     AND d.changed_by_id=u.id
     AND length(btrim(d.reason))>=8 AND length(d.preview_digest)=64
 ) INTO valid_decision;
 IF NOT valid_decision THEN
    RAISE EXCEPTION 'M5 joining-date approval decision missing or invalid'
        USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END; $$;

CREATE CONSTRAINT TRIGGER m5_case_date_revision_invariant
AFTER UPDATE ON public.onboarding_onboardingcase
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
WHEN (OLD.joining_date IS DISTINCT FROM NEW.joining_date
      OR OLD.schedule_revision IS DISTINCT FROM NEW.schedule_revision)
EXECUTE FUNCTION public.m5_guard_case_date_revision();
"""
REVERSE_SQL=r"""
DROP TRIGGER IF EXISTS m5_case_date_revision_invariant
  ON public.onboarding_onboardingcase;
DROP FUNCTION IF EXISTS public.m5_guard_case_date_revision();
"""

class Migration(migrations.Migration):
    dependencies=[('onboarding','0024_m5_narrow_snapshot_schedule_exception')]
    operations=[migrations.RunSQL(SQL,REVERSE_SQL)]
