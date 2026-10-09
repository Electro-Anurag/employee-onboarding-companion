"""M2 persisted cases, task snapshots and typed manager preparation evidence."""
import uuid
from django.db import models
from backend.accounts.models import Membership, Organization, User
from backend.templates.models import TemplateVersion, TemplateTask
from django.utils import timezone

class OnboardingCase(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey(Organization,on_delete=models.PROTECT)
    employee=models.ForeignKey(Membership,on_delete=models.PROTECT,related_name='employee_cases')
    joining_date=models.DateField()
    STATUS_CHOICES=[(x,x) for x in ('CREATED','PRE_JOINING','ACTIVE','COMPLETED','CANCELLED')]
    status=models.CharField(max_length=16,default='CREATED',choices=STATUS_CHOICES)
    version=models.PositiveBigIntegerField(default=1)
    template_version=models.ForeignKey(TemplateVersion,on_delete=models.PROTECT,null=True)
    created_by=models.ForeignKey(User,on_delete=models.PROTECT,null=True,related_name='created_cases')
    activated_at=models.DateTimeField(null=True)
    completed_at=models.DateTimeField(null=True)
    cancelled_at=models.DateTimeField(null=True)
    closeout_snapshot=models.JSONField(default=dict)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['employee'],condition=models.Q(status__in=['CREATED','PRE_JOINING','ACTIVE']),name='m2_one_open_case_per_employee'),
            models.CheckConstraint(condition=models.Q(status__in=['CREATED','PRE_JOINING','ACTIVE','COMPLETED','CANCELLED']),name='m2_case_known_status'),
        ]

class CaseAssignment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    case=models.ForeignKey(OnboardingCase,on_delete=models.PROTECT,related_name='assignments')
    role=models.CharField(max_length=16,choices=Membership.ROLE_CHOICES)
    member=models.ForeignKey(Membership,on_delete=models.PROTECT)
    effective_from=models.DateTimeField()
    effective_to=models.DateTimeField(null=True)
    assigned_by=models.ForeignKey(Membership,on_delete=models.PROTECT,related_name='assigned_owners',null=True)
    reason=models.CharField(max_length=240,blank=True)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['case','role'],condition=models.Q(effective_to__isnull=True),name='m1_one_active_assignment_per_role'),
            models.CheckConstraint(condition=models.Q(role__in=['HR','IT','MANAGER']),name='assignment_owner_role'),
            models.CheckConstraint(condition=models.Q(effective_to__isnull=True)|models.Q(effective_to__gte=models.F('effective_from')),name='assignment_valid_time_range'),
        ]

TASK_STATES=('NOT_STARTED','READY','IN_PROGRESS','BLOCKED','NEEDS_CLARIFICATION','COMPLETED','CANCELLED')
class Task(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    case=models.ForeignKey(OnboardingCase,on_delete=models.PROTECT,related_name='tasks')
    template_task=models.ForeignKey(TemplateTask,on_delete=models.PROTECT)
    key=models.CharField(max_length=80)
    kind=models.CharField(max_length=24)
    title=models.CharField(max_length=160)
    description=models.TextField(blank=True)
    required=models.BooleanField(default=True)
    applicable=models.BooleanField(default=True)
    owner_role=models.CharField(max_length=16)
    owner_assignment=models.ForeignKey(CaseAssignment,on_delete=models.PROTECT,null=True)
    evidence_spec=models.JSONField(default=dict)
    execution_state=models.CharField(max_length=24,choices=[(s,s) for s in TASK_STATES],default='NOT_STARTED')
    blocked_reason_codes=models.JSONField(default=list)
    available_at=models.DateTimeField()
    due_at=models.DateTimeField()
    work_started_at=models.DateTimeField(null=True)
    completed_at=models.DateTimeField(null=True)
    version=models.PositiveIntegerField(default=1)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['case','key'],name='m2_case_task_key_unique'),
            models.CheckConstraint(condition=models.Q(execution_state__in=TASK_STATES),name='m2_task_state_valid'),
            models.CheckConstraint(condition=models.Q(due_at__gte=models.F('available_at')),name='m2_task_due_after_available'),
        ]
        indexes=[models.Index(fields=['case','execution_state'],name='m2_task_case_state_idx'),
                 models.Index(fields=['owner_assignment','due_at'],name='m2_task_owner_due_idx')]

class TaskDependency(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    case=models.ForeignKey(OnboardingCase,on_delete=models.PROTECT,related_name='task_dependencies')
    predecessor=models.ForeignKey(Task,on_delete=models.PROTECT,related_name='unlocks')
    successor=models.ForeignKey(Task,on_delete=models.PROTECT,related_name='prerequisites')
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['case','predecessor','successor'],name='m2_task_edge_unique'),
            models.CheckConstraint(condition=~models.Q(predecessor=models.F('successor')),name='m2_task_no_self_edge'),
        ]

class ManagerAttestation(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.OneToOneField(Task,on_delete=models.PROTECT,related_name='manager_attestation')
    actor=models.ForeignKey(User,on_delete=models.PROTECT)
    prepared_fields=models.JSONField(default=dict)
    note=models.CharField(max_length=500)
    created_at=models.DateTimeField(default=timezone.now)

class TaskCompletion(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.OneToOneField(Task,on_delete=models.PROTECT,related_name='completion')
    manager_attestation=models.OneToOneField(ManagerAttestation,on_delete=models.PROTECT,null=True)
    form_review=models.OneToOneField('forms.FormReview',on_delete=models.PROTECT,null=True)
    it_confirmation=models.OneToOneField('provisioning.ITConfirmation',on_delete=models.PROTECT,null=True)
    equipment_receipt=models.OneToOneField('provisioning.EquipmentReceipt',on_delete=models.PROTECT,null=True)
    policy_ack=models.OneToOneField('policies.PolicyAcknowledgement',on_delete=models.PROTECT,null=True)
    document_review=models.OneToOneField('documents.DocumentReview',on_delete=models.PROTECT,null=True)
    training_attempt=models.OneToOneField('training.TrainingAttempt',on_delete=models.PROTECT,null=True)
    activity_attendance=models.OneToOneField('activities.ActivityAttendance',on_delete=models.PROTECT,null=True)
    evidence_type=models.CharField(max_length=32,choices=[('MANAGER_PREPARATION','MANAGER_PREPARATION'),('FORM','FORM'),('IT_CONFIRMATION','IT_CONFIRMATION'),('EQUIPMENT_RECEIPT','EQUIPMENT_RECEIPT'),('POLICY_ACK','POLICY_ACK'),('DOCUMENT','DOCUMENT'),('TRAINING','TRAINING'),('ACTIVITY_ATTENDANCE','ACTIVITY_ATTENDANCE')])
    completed_by=models.ForeignKey(User,on_delete=models.PROTECT)
    completed_at=models.DateTimeField(default=__import__('django.utils.timezone',fromlist=['now']).now)
    evidence_hash=models.CharField(max_length=64)
    class Meta:
        constraints=[models.CheckConstraint(condition=(
            models.Q(evidence_type='MANAGER_PREPARATION',manager_attestation__isnull=False,form_review__isnull=True,it_confirmation__isnull=True,equipment_receipt__isnull=True,policy_ack__isnull=True,document_review__isnull=True,training_attempt__isnull=True,activity_attendance__isnull=True)
            | models.Q(evidence_type='FORM',manager_attestation__isnull=True,form_review__isnull=False,it_confirmation__isnull=True,equipment_receipt__isnull=True,policy_ack__isnull=True,document_review__isnull=True,training_attempt__isnull=True,activity_attendance__isnull=True)
            | models.Q(evidence_type='IT_CONFIRMATION',manager_attestation__isnull=True,form_review__isnull=True,it_confirmation__isnull=False,equipment_receipt__isnull=True,policy_ack__isnull=True,document_review__isnull=True,training_attempt__isnull=True,activity_attendance__isnull=True)
            | models.Q(evidence_type='EQUIPMENT_RECEIPT',manager_attestation__isnull=True,form_review__isnull=True,it_confirmation__isnull=True,equipment_receipt__isnull=False,policy_ack__isnull=True,document_review__isnull=True,training_attempt__isnull=True,activity_attendance__isnull=True)
            | models.Q(evidence_type='POLICY_ACK',manager_attestation__isnull=True,form_review__isnull=True,it_confirmation__isnull=True,equipment_receipt__isnull=True,policy_ack__isnull=False,document_review__isnull=True,training_attempt__isnull=True,activity_attendance__isnull=True)
            | models.Q(evidence_type='DOCUMENT',manager_attestation__isnull=True,form_review__isnull=True,
                       it_confirmation__isnull=True,equipment_receipt__isnull=True,
                       policy_ack__isnull=True,document_review__isnull=False,training_attempt__isnull=True,activity_attendance__isnull=True)
            | models.Q(evidence_type='TRAINING',manager_attestation__isnull=True,form_review__isnull=True,
                       it_confirmation__isnull=True,equipment_receipt__isnull=True,
                       policy_ack__isnull=True,document_review__isnull=True,training_attempt__isnull=False,activity_attendance__isnull=True)
            | models.Q(evidence_type='ACTIVITY_ATTENDANCE',manager_attestation__isnull=True,
                form_review__isnull=True,it_confirmation__isnull=True,equipment_receipt__isnull=True,
                policy_ack__isnull=True,document_review__isnull=True,training_attempt__isnull=True,
                activity_attendance__isnull=False)),
            name='m4_activity_completion_evidence_exclusive')]
