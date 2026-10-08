"""Versioned, publish-once onboarding task DAG definitions."""
import uuid
from django.db import models
from django.utils import timezone
from backend.accounts.models import Organization, User, Membership

KINDS=('DOCUMENT','FORM','POLICY_ACK','EQUIPMENT','ACCESS','EQUIPMENT_RECEIPT',
       'TRAINING','ACTIVITY','INTRODUCTION','CHECK_IN','MANAGER_PREPARATION')
KIND_CHOICES=[(kind,kind) for kind in KINDS]
OWNER_ROLES=('EMPLOYEE','HR','IT','MANAGER')
OWNER_CHOICES=[(role,role) for role in OWNER_ROLES]

class OnboardingTemplate(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey(Organization,on_delete=models.PROTECT)
    key=models.CharField(max_length=80)
    name=models.CharField(max_length=160)
    created_by=models.ForeignKey(User,on_delete=models.PROTECT)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['organization','key'],name='m2_template_org_key_unique')]

class TemplateVersion(models.Model):
    DRAFT='DRAFT'
    PUBLISHED='PUBLISHED'
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    template=models.ForeignKey(OnboardingTemplate,on_delete=models.PROTECT,related_name='versions')
    version_number=models.PositiveSmallIntegerField(default=1)
    state=models.CharField(max_length=12,choices=[('DRAFT','DRAFT'),('PUBLISHED','PUBLISHED')],default='DRAFT')
    revision=models.PositiveIntegerField(default=1)
    content_hash=models.CharField(max_length=64,blank=True)
    published_at=models.DateTimeField(null=True)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['template','version_number'],name='m2_template_version_unique'),
            models.CheckConstraint(condition=models.Q(state__in=['DRAFT','PUBLISHED']),name='m2_template_valid_state'),
        ]

class TemplateTask(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    version=models.ForeignKey(TemplateVersion,on_delete=models.PROTECT,related_name='tasks')
    key=models.CharField(max_length=80)
    kind=models.CharField(max_length=24,choices=KIND_CHOICES)
    title=models.CharField(max_length=160)
    description=models.TextField(blank=True)
    owner_role=models.CharField(max_length=16,choices=OWNER_CHOICES)
    required=models.BooleanField(default=True)
    position=models.PositiveSmallIntegerField(default=0)
    available_offset_days=models.SmallIntegerField(default=0)
    due_offset_days=models.SmallIntegerField(default=0)
    evidence_spec=models.JSONField(default=dict)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['version','key'],name='m2_template_task_key_unique'),
            models.CheckConstraint(condition=models.Q(kind__in=KINDS),name='m2_template_kind_valid'),
            models.CheckConstraint(condition=models.Q(owner_role__in=OWNER_ROLES),name='m2_template_role_valid'),
            models.CheckConstraint(condition=models.Q(available_offset_days__gte=-90,available_offset_days__lte=365),name='m2_template_avail_window'),
            models.CheckConstraint(condition=models.Q(due_offset_days__gte=-90,due_offset_days__lte=365),name='m2_template_due_window'),
            models.CheckConstraint(condition=models.Q(due_offset_days__gte=models.F('available_offset_days')),name='m2_template_due_after_avail'),
        ]

class TemplateDependency(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    version=models.ForeignKey(TemplateVersion,on_delete=models.PROTECT,related_name='edges')
    predecessor=models.ForeignKey(TemplateTask,on_delete=models.PROTECT,related_name='outgoing_edges')
    successor=models.ForeignKey(TemplateTask,on_delete=models.PROTECT,related_name='incoming_edges')
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['version','predecessor','successor'],name='m2_template_edge_unique'),
            models.CheckConstraint(condition=~models.Q(predecessor=models.F('successor')),name='m2_template_no_self_edge'),
        ]
