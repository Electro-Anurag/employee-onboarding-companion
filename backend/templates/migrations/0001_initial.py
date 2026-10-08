import uuid
import django.db.models.deletion
from django.db import migrations,models
from django.utils import timezone
from backend.templates.models import KINDS,OWNER_ROLES,KIND_CHOICES,OWNER_CHOICES

class Migration(migrations.Migration):
    initial=True
    dependencies=[('accounts','0002_security_constraints')]
    operations=[
        migrations.CreateModel(name='OnboardingTemplate',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('key',models.CharField(max_length=80)),
            ('name',models.CharField(max_length=160)),
            ('created_at',models.DateTimeField(default=timezone.now)),
            ('organization',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.organization')),
            ('created_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user'))]),
        migrations.AddConstraint(model_name='onboardingtemplate',constraint=models.UniqueConstraint(fields=['organization','key'],name='m2_template_org_key_unique')),
        migrations.CreateModel(name='TemplateVersion',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('version_number',models.PositiveSmallIntegerField(default=1)),
            ('state',models.CharField(max_length=12,default='DRAFT',choices=[('DRAFT','DRAFT'),('PUBLISHED','PUBLISHED')])),
            ('revision',models.PositiveIntegerField(default=1)),
            ('content_hash',models.CharField(max_length=64,blank=True)),
            ('published_at',models.DateTimeField(null=True)),
            ('template',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='versions',to='templates.onboardingtemplate'))]),
        migrations.AddConstraint(model_name='templateversion',constraint=models.UniqueConstraint(fields=['template','version_number'],name='m2_template_version_unique')),
        migrations.AddConstraint(model_name='templateversion',constraint=models.CheckConstraint(condition=models.Q(state__in=['DRAFT','PUBLISHED']),name='m2_template_valid_state')),
        migrations.CreateModel(name='TemplateTask',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('key',models.CharField(max_length=80)),
            ('kind',models.CharField(max_length=24,choices=KIND_CHOICES)),
            ('title',models.CharField(max_length=160)),
            ('description',models.TextField(blank=True)),
            ('owner_role',models.CharField(max_length=16,choices=OWNER_CHOICES)),
            ('required',models.BooleanField(default=True)),
            ('position',models.PositiveSmallIntegerField(default=0)),
            ('available_offset_days',models.SmallIntegerField(default=0)),
            ('due_offset_days',models.SmallIntegerField(default=0)),
            ('evidence_spec',models.JSONField(default=dict)),
            ('version',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='tasks',to='templates.templateversion'))]),
        migrations.AddConstraint(model_name='templatetask',constraint=models.UniqueConstraint(fields=['version','key'],name='m2_template_task_key_unique')),
        migrations.AddConstraint(model_name='templatetask',constraint=models.CheckConstraint(condition=models.Q(kind__in=KINDS),name='m2_template_kind_valid')),
        migrations.AddConstraint(model_name='templatetask',constraint=models.CheckConstraint(condition=models.Q(owner_role__in=OWNER_ROLES),name='m2_template_role_valid')),
        migrations.AddConstraint(model_name='templatetask',constraint=models.CheckConstraint(condition=models.Q(available_offset_days__gte=-90,available_offset_days__lte=365),name='m2_template_avail_window')),
        migrations.AddConstraint(model_name='templatetask',constraint=models.CheckConstraint(condition=models.Q(due_offset_days__gte=-90,due_offset_days__lte=365),name='m2_template_due_window')),
        migrations.AddConstraint(model_name='templatetask',constraint=models.CheckConstraint(condition=models.Q(due_offset_days__gte=models.F('available_offset_days')),name='m2_template_due_after_avail')),
        migrations.CreateModel(name='TemplateDependency',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('version',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='edges',to='templates.templateversion')),
            ('predecessor',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='outgoing_edges',to='templates.templatetask')),
            ('successor',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='incoming_edges',to='templates.templatetask'))]),
        migrations.AddConstraint(model_name='templatedependency',constraint=models.UniqueConstraint(fields=['version','predecessor','successor'],name='m2_template_edge_unique')),
        migrations.AddConstraint(model_name='templatedependency',constraint=models.CheckConstraint(condition=~models.Q(predecessor=models.F('successor')),name='m2_template_no_self_edge')),
    ]
