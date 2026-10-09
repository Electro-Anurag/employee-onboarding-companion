"""Restore M4 cancelled-occurrence DB authority after M3's 0017 SQL refresh.

M3 0017 replaced public.m4_guard_valid_attendance_insert() with its
pre-cancellation body. Restore M4 0002's complete authority check on both
fresh installs and databases upgraded from M3 0017.
"""
from django.db import migrations

SQL="CREATE OR REPLACE FUNCTION public.m4_guard_valid_attendance_insert()\nRETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$\nDECLARE organizer_role text; taskid uuid; task_state text;\nBEGIN\n SELECT t.owner_role,t.id,t.execution_state INTO organizer_role,taskid,task_state\n FROM public.activities_activityoccurrence o\n JOIN public.onboarding_task t ON t.id=o.task_id\n WHERE o.id=NEW.occurrence_id;\n IF taskid IS NULL OR organizer_role NOT IN ('HR','MANAGER')\n   OR task_state IS DISTINCT FROM 'IN_PROGRESS'\n   OR NOT EXISTS (\n      SELECT 1 FROM public.activities_activityoccurrence o\n      WHERE o.id=NEW.occurrence_id AND o.ends_at<=now()\n        AND NOT EXISTS(\n           SELECT 1 FROM public.activities_activityoccurrence later\n           WHERE later.task_id=o.task_id AND later.revision>o.revision))\n   OR EXISTS (\n      SELECT 1 FROM public.activities_activitycancellation ca WHERE ca.occurrence_id=NEW.occurrence_id)\n   OR NOT EXISTS (\n      SELECT 1 FROM public.onboarding_task t\n      JOIN public.onboarding_caseassignment a ON a.id=t.owner_assignment_id\n      JOIN public.accounts_membership m ON m.id=a.member_id\n      WHERE t.id=taskid AND a.effective_to IS NULL\n       AND m.user_id=NEW.recorded_by_id AND m.role=organizer_role AND m.active)\n THEN RAISE EXCEPTION 'M4 unauthorized or future attendance' USING ERRCODE='23514'; END IF;\n RETURN NEW;\nEND; $$;"

class Migration(migrations.Migration):
    dependencies=[
        ('onboarding','0017_secure_s3_document_completion'),
        ('activities','0002_activity_cancellation'),
    ]
    operations=[migrations.RunSQL(SQL)]
