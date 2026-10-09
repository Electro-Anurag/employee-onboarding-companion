"""Durable synthetic IT failure evidence; no false task completion on retry."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
SQL="\nCREATE OR REPLACE FUNCTION public.m4_guard_it_failure_evidence()\nRETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$\nBEGIN\n RAISE EXCEPTION 'M4 IT failure history is immutable' USING ERRCODE='23514';\nEND; $$;\nCREATE TRIGGER m4_it_failure_immutable BEFORE UPDATE OR DELETE\nON public.provisioning_itsimulationfailure FOR EACH ROW\nEXECUTE FUNCTION public.m4_guard_it_failure_evidence();\n\nCREATE OR REPLACE FUNCTION public.m4_validate_it_failure_insert()\nRETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$\nBEGIN\n IF NOT EXISTS (\n    SELECT 1 FROM public.provisioning_itoperation op\n    JOIN public.onboarding_task t ON t.id=op.task_id\n    JOIN public.onboarding_onboardingcase c ON c.id=t.case_id\n    JOIN public.onboarding_caseassignment a ON a.id=t.owner_assignment_id\n    JOIN public.accounts_membership m ON m.id=a.member_id\n    JOIN public.accounts_user u ON u.id=m.user_id\n    WHERE op.id=NEW.operation_id\n      AND op.status='REQUESTED' AND t.execution_state='IN_PROGRESS'\n      AND t.kind IN ('ACCESS','EQUIPMENT')\n      AND c.status IN ('PRE_JOINING','ACTIVE')\n      AND a.role='IT' AND a.effective_to IS NULL AND a.effective_from<=now()\n      AND m.role='IT' AND m.user_id=NEW.reported_by_id\n      AND m.active AND m.available AND u.is_active\n ) THEN\n   RAISE EXCEPTION 'M4 simulation failure requires active assigned IT request'\n     USING ERRCODE='23514';\n END IF;\n RETURN NEW;\nEND; $$;\nCREATE TRIGGER m4_it_failure_authority BEFORE INSERT\nON public.provisioning_itsimulationfailure FOR EACH ROW\nEXECUTE FUNCTION public.m4_validate_it_failure_insert();\n"
class Migration(migrations.Migration):
    dependencies=[('provisioning','0002_evidence_confirmation_receipt')]
    operations=[
        migrations.CreateModel(name='ITSimulationFailure',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('sequence',models.PositiveIntegerField()),
            ('cause',models.CharField(max_length=32,choices=[
                ('PROVIDER_UNAVAILABLE','PROVIDER_UNAVAILABLE'),
                ('SIMULATED_TIMEOUT','SIMULATED_TIMEOUT'),
                ('SIMULATED_REJECTION','SIMULATED_REJECTION')])),
            ('note',models.CharField(max_length=300)),
            ('reported_at',models.DateTimeField(default=timezone.now)),
            ('operation',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='failures',to='provisioning.itoperation')),
            ('reported_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
        ],options={'ordering':['sequence']}),
        migrations.AddConstraint(model_name='itsimulationfailure',constraint=models.UniqueConstraint(
            fields=('operation','sequence'),name='m4_it_failure_sequence_unique')),
        migrations.AddConstraint(model_name='itsimulationfailure',constraint=models.CheckConstraint(
            condition=models.Q(cause__in=['PROVIDER_UNAVAILABLE','SIMULATED_TIMEOUT','SIMULATED_REJECTION']),
            name='m4_it_failure_valid_cause')),
        migrations.AddConstraint(model_name='itsimulationfailure',constraint=models.CheckConstraint(
            condition=models.Q(sequence__gte=1,sequence__lte=5),
            name='m4_it_failure_bounded_sequence')),
        migrations.RunSQL(SQL),
    ]
