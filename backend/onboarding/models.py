"""Minimal case/access skeleton for M1; task domain belongs to M2."""
import uuid
from django.db import models
from backend.accounts.models import Membership, Organization

class OnboardingCase(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey(Organization,on_delete=models.PROTECT)
    employee=models.ForeignKey(Membership,on_delete=models.PROTECT,related_name='employee_cases')
    joining_date=models.DateField()
    status=models.CharField(max_length=16,default='CREATED',choices=[('CREATED','CREATED')])
    version=models.PositiveBigIntegerField(default=1)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['employee'],name='m1_one_case_per_employee')]

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
