"""M2 case transition and dependency snapshot schema."""
import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
from backend.onboarding.models import TASK_STATES

class Migration(migrations.Migration):
    dependencies=[('onboarding','0004_immutable_roots_and_issuer_guard'),('templates','0001_initial')]
    operations=[
        migrations.RemoveConstraint(model_name='onboardingcase',name='m1_one_case_per_employee'),
        migrations.AlterField(model_name='onboardingcase',name='status',
            field=models.CharField(max_length=16,default='CREATED',choices=[(x,x) for x in ('CREATED','PRE_JOINING','ACTIVE','COMPLETED','CANCELLED')])),
        migrations.AddField(model_name='onboardingcase',name='template_version',
            field=models.ForeignKey(null=True,on_delete=django.db.models.deletion.PROTECT,to='templates.templateversion')),
        migrations.AddField(model_name='onboardingcase',name='created_by',
            field=models.ForeignKey(null=True,on_delete=django.db.models.deletion.PROTECT,related_name='created_cases',to='accounts.user')),
        migrations.AddField(model_name='onboardingcase',name='activated_at',field=models.DateTimeField(null=True)),
        migrations.AddField(model_name='onboardingcase',name='completed_at',field=models.DateTimeField(null=True)),
        migrations.AddField(model_name='onboardingcase',name='cancelled_at',field=models.DateTimeField(null=True)),
        migrations.AddField(model_name='onboardingcase',name='closeout_snapshot',field=models.JSONField(default=dict)),
        migrations.AddConstraint(model_name='onboardingcase',constraint=models.UniqueConstraint(
            fields=['employee'],condition=models.Q(status__in=['CREATED','PRE_JOINING','ACTIVE']),name='m2_one_open_case_per_employee')),
        migrations.AddConstraint(model_name='onboardingcase',constraint=models.CheckConstraint(
            condition=models.Q(status__in=['CREATED','PRE_JOINING','ACTIVE','COMPLETED','CANCELLED']),name='m2_case_known_status')),
        migrations.CreateModel(name='Task',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('key',models.CharField(max_length=80)),
            ('kind',models.CharField(max_length=24)),
            ('title',models.CharField(max_length=160)),
            ('description',models.TextField(blank=True)),
            ('required',models.BooleanField(default=True)),
            ('applicable',models.BooleanField(default=True)),
            ('owner_role',models.CharField(max_length=16)),
            ('evidence_spec',models.JSONField(default=dict)),
            ('execution_state',models.CharField(max_length=24,choices=[(s,s) for s in TASK_STATES],default='NOT_STARTED')),
            ('blocked_reason_codes',models.JSONField(default=list)),
            ('available_at',models.DateTimeField()),
            ('due_at',models.DateTimeField()),
            ('work_started_at',models.DateTimeField(null=True)),
            ('completed_at',models.DateTimeField(null=True)),
            ('version',models.PositiveIntegerField(default=1)),
            ('case',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='tasks',to='onboarding.onboardingcase')),
            ('template_task',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='templates.templatetask')),
            ('owner_assignment',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,null=True,to='onboarding.caseassignment'))]),
        migrations.AddConstraint(model_name='task',constraint=models.UniqueConstraint(fields=['case','key'],name='m2_case_task_key_unique')),
        migrations.AddConstraint(model_name='task',constraint=models.CheckConstraint(condition=models.Q(execution_state__in=TASK_STATES),name='m2_task_state_valid')),
        migrations.AddConstraint(model_name='task',constraint=models.CheckConstraint(condition=models.Q(due_at__gte=models.F('available_at')),name='m2_task_due_after_available')),
        migrations.AddIndex(model_name='task',index=models.Index(fields=['case','execution_state'],name='m2_task_case_state_idx')),
        migrations.AddIndex(model_name='task',index=models.Index(fields=['owner_assignment','due_at'],name='m2_task_owner_due_idx')),
        migrations.CreateModel(name='TaskDependency',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('case',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='task_dependencies',to='onboarding.onboardingcase')),
            ('predecessor',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='unlocks',to='onboarding.task')),
            ('successor',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='prerequisites',to='onboarding.task'))]),
        migrations.AddConstraint(model_name='taskdependency',constraint=models.UniqueConstraint(fields=['case','predecessor','successor'],name='m2_task_edge_unique')),
        migrations.AddConstraint(model_name='taskdependency',constraint=models.CheckConstraint(condition=~models.Q(predecessor=models.F('successor')),name='m2_task_no_self_edge')),
        migrations.CreateModel(name='ManagerAttestation',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('prepared_fields',models.JSONField(default=dict)),
            ('note',models.CharField(max_length=500)),
            ('created_at',models.DateTimeField(default=timezone.now)),
            ('actor',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
            ('task',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='manager_attestation',to='onboarding.task'))]),
        migrations.CreateModel(name='TaskCompletion',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('evidence_type',models.CharField(max_length=32,choices=[('MANAGER_PREPARATION','MANAGER_PREPARATION')])),
            ('completed_at',models.DateTimeField(default=timezone.now)),
            ('evidence_hash',models.CharField(max_length=64)),
            ('completed_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
            ('task',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='completion',to='onboarding.task')),
            ('manager_attestation',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,to='onboarding.managerattestation'))]),
        migrations.AddConstraint(model_name='taskcompletion',constraint=models.CheckConstraint(condition=models.Q(evidence_type='MANAGER_PREPARATION'),name='m2_completion_supported_kind')),
    ]
