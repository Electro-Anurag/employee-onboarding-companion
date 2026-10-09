"""Append-only typed, explicitly human-confirmed M4 evidence."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
SQL="CREATE OR REPLACE FUNCTION public.m4_guard_final_evidence()\nRETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$\nBEGIN\n RAISE EXCEPTION 'M4 human evidence is append only' USING ERRCODE='23514';\nEND; $$;\nCREATE TRIGGER m4_it_confirmation_immutable BEFORE UPDATE OR DELETE\n ON public.provisioning_itconfirmation FOR EACH ROW EXECUTE FUNCTION public.m4_guard_final_evidence();\nCREATE TRIGGER m4_equipment_receipt_immutable BEFORE UPDATE OR DELETE\n ON public.provisioning_equipmentreceipt FOR EACH ROW EXECUTE FUNCTION public.m4_guard_final_evidence();"
REVERSE="""
DROP TRIGGER IF EXISTS m4_equipment_receipt_immutable ON public.provisioning_equipmentreceipt;
DROP TRIGGER IF EXISTS m4_it_confirmation_immutable ON public.provisioning_itconfirmation;
DROP FUNCTION IF EXISTS public.m4_guard_final_evidence();
"""
class Migration(migrations.Migration):
    dependencies=[('provisioning','0001_initial'),('onboarding','0011_form_immediate_evidence_guard')]
    operations=[
        migrations.CreateModel(name='ITConfirmation',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('simulation_digest',models.CharField(max_length=64)),
            ('note',models.CharField(max_length=300)),
            ('confirmed_at',models.DateTimeField(default=timezone.now)),
            ('confirmed_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
            ('operation',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='confirmation',to='provisioning.itoperation')),
        ]),
        migrations.CreateModel(name='EquipmentReceipt',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('note',models.CharField(max_length=300)),
            ('received_at',models.DateTimeField(default=timezone.now)),
            ('accepted_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
            ('it_confirmation',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,to='provisioning.itconfirmation')),
            ('task',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='equipment_receipt',to='onboarding.task')),
        ]),
        migrations.RunSQL(SQL,REVERSE),
    ]
