"""M4 explicitly simulated IT request lifecycle."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
SQL="""
CREATE OR REPLACE FUNCTION public.m4_guard_it_operation()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
  IF TG_OP='DELETE' THEN
    RAISE EXCEPTION 'M4 IT operation cannot be deleted' USING ERRCODE='23514';
  END IF;
  IF NEW.task_id IS DISTINCT FROM OLD.task_id
     OR NEW.requested_by_id IS DISTINCT FROM OLD.requested_by_id
     OR NEW.requested_at IS DISTINCT FROM OLD.requested_at
     OR OLD.status IS DISTINCT FROM 'REQUESTED'
     OR NEW.status IS DISTINCT FROM 'SIMULATED_FULFILLED'
  THEN RAISE EXCEPTION 'M4 IT operation cannot be rewound or rebound' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER m4_it_operation_monotonic BEFORE UPDATE OR DELETE
ON public.provisioning_itoperation FOR EACH ROW EXECUTE FUNCTION public.m4_guard_it_operation();
"""
REVERSE="""
DROP TRIGGER IF EXISTS m4_it_operation_monotonic ON public.provisioning_itoperation;
DROP FUNCTION IF EXISTS public.m4_guard_it_operation();
"""
class Migration(migrations.Migration):
    initial=True
    dependencies=[('onboarding','0009_irreversible_activated_case'),('accounts','0002_security_constraints')]
    operations=[
        migrations.CreateModel(name='ITOperation',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('status',models.CharField(max_length=24,choices=[('REQUESTED','REQUESTED'),('SIMULATED_FULFILLED','SIMULATED_FULFILLED')],default='REQUESTED')),
            ('requested_at',models.DateTimeField(default=timezone.now)),
            ('simulated_at',models.DateTimeField(null=True)),
            ('simulation_digest',models.CharField(max_length=64,blank=True,default='')),
            ('note',models.CharField(max_length=300,blank=True,default='')),
            ('requested_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='requested_it_operations',to='accounts.user')),
            ('simulated_by',models.ForeignKey(null=True,on_delete=django.db.models.deletion.PROTECT,related_name='simulated_it_operations',to='accounts.user')),
            ('task',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='it_operation',to='onboarding.task')),
        ]),
        migrations.AddConstraint(model_name='itoperation',constraint=models.CheckConstraint(condition=(
            models.Q(status='REQUESTED',simulated_by__isnull=True,simulated_at__isnull=True,simulation_digest='',note='')
            | models.Q(status='SIMULATED_FULFILLED',simulated_by__isnull=False,simulated_at__isnull=False)
        ),name='m4_it_operation_consistent_status')),
        migrations.RunSQL(SQL,REVERSE),
    ]
