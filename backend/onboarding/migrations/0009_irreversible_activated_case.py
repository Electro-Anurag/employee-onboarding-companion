"""R5 closure: after activation, returning a case to CREATED is forbidden.

The 0008 provenance guard compares old/new status to protect the template FK.
An ordinary SQL transaction could previously move ACTIVE -> CREATED, clear the
template version, and return ACTIVE. This migration closes the intermediate
state rather than relying on application-layer authorization.
"""
from django.db import migrations

SQL = """
CREATE OR REPLACE FUNCTION public.m2_guard_case_template_binding()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM 'CREATED'
       AND NEW.status = 'CREATED' THEN
    RAISE EXCEPTION 'M2 activated case cannot return to CREATED'
      USING ERRCODE='23514';
  END IF;
  IF (OLD.status IS DISTINCT FROM 'CREATED' OR NEW.status IS DISTINCT FROM 'CREATED')
       AND NEW.template_version_id IS DISTINCT FROM OLD.template_version_id THEN
    RAISE EXCEPTION 'M2 activated case template binding immutable'
      USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END; $$;
"""
REVERSE_SQL = """
CREATE OR REPLACE FUNCTION public.m2_guard_case_template_binding()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
  IF (OLD.status IS DISTINCT FROM 'CREATED' OR NEW.status IS DISTINCT FROM 'CREATED')
       AND NEW.template_version_id IS DISTINCT FROM OLD.template_version_id THEN
    RAISE EXCEPTION 'M2 activated case template binding immutable'
      USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END; $$;
"""

class Migration(migrations.Migration):
    dependencies=[('onboarding','0008_completion_provenance_and_snapshot_lock')]
    operations=[migrations.RunSQL(SQL,REVERSE_SQL)]
