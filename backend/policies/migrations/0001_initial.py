"""Immutable policy acknowledgements do not alter their published task versions."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
SQL="""
CREATE OR REPLACE FUNCTION public.m3_guard_policy_ack_immutable()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'M3 policy acknowledgment is immutable' USING ERRCODE='23514';
END; $$;
CREATE TRIGGER m3_policy_ack_immutable BEFORE UPDATE OR DELETE
 ON public.policies_policyacknowledgement FOR EACH ROW EXECUTE FUNCTION public.m3_guard_policy_ack_immutable();
"""
REVERSE="""
DROP TRIGGER IF EXISTS m3_policy_ack_immutable ON public.policies_policyacknowledgement;
DROP FUNCTION IF EXISTS public.m3_guard_policy_ack_immutable();
"""
class Migration(migrations.Migration):
    initial=True
    dependencies=[('accounts','0002_security_constraints'),('onboarding','0012_m4_human_evidence_completion')]
    operations=[
      migrations.CreateModel(name='PolicyAcknowledgement',fields=[
       ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
       ('policy_version',models.CharField(max_length=80)),
       ('content_sha256',models.CharField(max_length=64)),
       ('acknowledged_at',models.DateTimeField(default=timezone.now)),
       ('actor',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
       ('task',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                                  related_name='policy_acknowledgement',to='onboarding.task')),
      ]),
      migrations.RunSQL(SQL,REVERSE),
    ]
