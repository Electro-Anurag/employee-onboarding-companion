"""Expand immutable M2 task-completion provenance for M3 HR-accepted form evidence.

Intentionally irreversible once accepted form evidence exists: dropping the
provenance checks on downgrade would risk silently trusting invalid completions.
"""
import django.db.models.deletion
from django.db import migrations,models

SQL="-- Extend M2 deferred evidence validation to exact accepted M3 forms.\n-- Preserve manager attestation predicates unchanged.\nCREATE OR REPLACE FUNCTION public.m2_validate_completed_task()\nRETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$\nDECLARE t public.onboarding_task%ROWTYPE;\nBEGIN\n SELECT * INTO t FROM public.onboarding_task WHERE id=NEW.id;\n IF t.execution_state='COMPLETED' THEN\n   IF t.completed_at IS NULL OR NOT EXISTS (\n     SELECT 1 FROM public.onboarding_taskcompletion c\n     LEFT JOIN public.onboarding_managerattestation a ON a.id=c.manager_attestation_id\n     LEFT JOIN public.forms_formreview fr ON fr.id=c.form_review_id\n     LEFT JOIN public.forms_formsubmission fs ON fs.id=fr.submission_id\n     WHERE c.task_id=t.id AND c.completed_at IS NOT NULL AND\n       ((t.kind='MANAGER_PREPARATION' AND c.evidence_type='MANAGER_PREPARATION'\n          AND a.task_id=t.id AND a.actor_id=c.completed_by_id)\n       OR\n        (t.kind='FORM' AND c.evidence_type='FORM'\n          AND fs.task_id=t.id AND fr.decision='ACCEPTED'\n          AND fr.reviewed_by_id=c.completed_by_id\n          AND fs.submitted_by_id IS NOT NULL))\n   ) THEN\n     RAISE EXCEPTION 'M3 completed task lacks accepted typed evidence'\n       USING ERRCODE='23514';\n   END IF;\n END IF;\n RETURN NULL;\nEND; $$;\n\nCREATE OR REPLACE FUNCTION public.m2_check_completed_manager_evidence()\nRETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$\nDECLARE state text; finished timestamptz; taskkind text; evidence_actor uuid;\n        review_actor uuid; review_task uuid; decision text;\nBEGIN\n SELECT execution_state,completed_at,kind INTO state,finished,taskkind\n FROM public.onboarding_task WHERE id=NEW.task_id;\n IF state IS DISTINCT FROM 'COMPLETED' OR finished IS NULL THEN\n   RAISE EXCEPTION 'M3 completion requires completed task'\n     USING ERRCODE='23514';\n END IF;\n IF NEW.evidence_type='MANAGER_PREPARATION' THEN\n   SELECT actor_id INTO evidence_actor\n     FROM public.onboarding_managerattestation WHERE id=NEW.manager_attestation_id;\n   IF taskkind IS DISTINCT FROM 'MANAGER_PREPARATION'\n      OR evidence_actor IS DISTINCT FROM NEW.completed_by_id THEN\n      RAISE EXCEPTION 'M2 completion lacks matching manager evidence'\n        USING ERRCODE='23514';\n   END IF;\n ELSIF NEW.evidence_type='FORM' THEN\n   SELECT r.reviewed_by_id,s.task_id,r.decision\n     INTO review_actor,review_task,decision\n     FROM public.forms_formreview r\n     JOIN public.forms_formsubmission s ON s.id=r.submission_id\n     WHERE r.id=NEW.form_review_id;\n   IF taskkind IS DISTINCT FROM 'FORM'\n      OR review_task IS DISTINCT FROM NEW.task_id\n      OR review_actor IS DISTINCT FROM NEW.completed_by_id\n      OR decision IS DISTINCT FROM 'ACCEPTED'\n   THEN RAISE EXCEPTION 'M3 completion lacks matching accepted form review'\n     USING ERRCODE='23514';\n   END IF;\n ELSE\n   RAISE EXCEPTION 'M3 unsupported completion evidence type'\n     USING ERRCODE='23514';\n END IF;\n RETURN NEW;\nEND; $$;"

class Migration(migrations.Migration):
    dependencies=[('onboarding','0009_irreversible_activated_case'),('forms','0001_initial')]
    operations=[
        migrations.AddField(model_name='taskcompletion',name='form_review',
            field=models.OneToOneField(null=True,on_delete=django.db.models.deletion.PROTECT,to='forms.formreview')),
        migrations.AlterField(model_name='taskcompletion',name='manager_attestation',
            field=models.OneToOneField(null=True,on_delete=django.db.models.deletion.PROTECT,to='onboarding.managerattestation')),
        migrations.AlterField(model_name='taskcompletion',name='evidence_type',
            field=models.CharField(max_length=32,choices=[('MANAGER_PREPARATION','MANAGER_PREPARATION'),('FORM','FORM')])),
        migrations.RemoveConstraint(model_name='taskcompletion',name='m2_completion_supported_kind'),
        migrations.AddConstraint(model_name='taskcompletion',constraint=models.CheckConstraint(
            condition=(models.Q(evidence_type='MANAGER_PREPARATION',manager_attestation__isnull=False,form_review__isnull=True)
             | models.Q(evidence_type='FORM',manager_attestation__isnull=True,form_review__isnull=False)),
            name='m3_completion_evidence_exclusive')),
        migrations.RunSQL(SQL),
    ]
