"""M1 narrowly scoped ownership command; task transitions remain M2."""
import hashlib
import json
import uuid
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.accounts.security import actor_context
from backend.audit.models import CommandReceipt
from backend.audit.services import append_event
from backend.onboarding.models import CaseAssignment, OnboardingCase

class CommandFailure(Exception):
    def __init__(self,code,status=409): self.code,self.status=code,status

def authorize_case(member,case):
    if not member.active or not member.user.is_active or member.organization_id!=case.organization_id: return False
    if member.role==Membership.EMPLOYEE: return case.employee_id==member.pk
    return case.assignments.filter(member=member,role=member.role,effective_to__isnull=True).exists()

def get_authorized_case(user,case_id):
    member=actor_context(user)
    case=OnboardingCase.objects.select_related('employee__user').filter(pk=case_id).first()
    if case is None or not authorize_case(member,case): raise CommandFailure('NOT_FOUND',404)
    return member,case

def scoped_cases(user):
    member=actor_context(user)
    if member.role==Membership.EMPLOYEE:
        return OnboardingCase.objects.filter(employee=member)
    return OnboardingCase.objects.filter(assignments__member=member,assignments__role=member.role,assignments__effective_to__isnull=True).distinct()

def case_summary(member,case):
    base={'id':str(case.pk),'joining_date':case.joining_date.isoformat(),'status':case.status,'version':case.version,
          'my_role':member.role,'allowed_actions':[]}
    if member.role==Membership.EMPLOYEE:
        base['employee_name']=case.employee.user.display_name
    elif member.role==Membership.HR:
        base['employee_name']=case.employee.user.display_name
        base['employee_email']=case.employee.user.email
        base['allowed_actions']=['REASSIGN_IT','REASSIGN_MANAGER']
    else:
        base['employee_name']=case.employee.user.display_name
    return base

def reassign_owner(*,actor,case_id,role,new_member_id,reason,key,expected_version,command_id=None,fail_after_audit=False):
    if role not in [Membership.IT,Membership.MANAGER,Membership.HR]: raise CommandFailure('INVALID_ROLE',422)
    if not reason or len(reason)>240: raise CommandFailure('REASON_REQUIRED',422)
    if not isinstance(key,uuid.UUID): raise CommandFailure('INVALID_IDEMPOTENCY_KEY',400)
    command_id=command_id or uuid.uuid4()
    canonical=json.dumps({'role':role,'new_member_id':str(new_member_id),'reason':reason},sort_keys=True,separators=(',',':'))
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    with transaction.atomic():
        # This case lock serializes all domain writes and audit sequence additions.
        case=OnboardingCase.objects.select_for_update().get(pk=case_id)
        member=actor_context(actor)
        if not authorize_case(member,case) or member.role!=Membership.HR: raise CommandFailure('NOT_FOUND',404)
        if role==Membership.HR and not member.can_coordinate_ownership: raise CommandFailure('FORBIDDEN',403)
        receipt=CommandReceipt.objects.filter(actor=actor,route='reassign-owner',idempotency_key=key).first()
        if receipt:
            if receipt.request_hash!=digest or receipt.case_id!=case_id: raise CommandFailure('IDEMPOTENCY_KEY_REUSED',409)
            return receipt.response,receipt.status_code
        if case.version!=expected_version: raise CommandFailure('STALE_VERSION',409)
        new=Membership.objects.select_for_update().filter(pk=new_member_id,organization_id=case.organization_id,
                    active=True,available=True,user__is_active=True,role=role).first()
        if new is None: raise CommandFailure('INVALID_ASSIGNEE',422)
        existing=CaseAssignment.objects.select_for_update().filter(case=case,role=role,effective_to__isnull=True).first()
        if existing is None: raise CommandFailure('ASSIGNMENT_MISSING',409)
        if existing.member_id==new.pk: raise CommandFailure('ALREADY_ASSIGNED',409)
        now=timezone.now(); existing.effective_to=now; existing.save(update_fields=['effective_to'])
        created=CaseAssignment.objects.create(case=case,role=role,member=new,effective_from=now,assigned_by=member,reason=reason)
        case.version+=1;case.save(update_fields=['version'])
        append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='OWNER_REASSIGNED',entity_id=case.pk,
                     command_id=command_id,changes={'role':role,'previous_assignment_id':str(existing.pk),
                     'new_assignment_id':str(created.pk),'case_version':case.version},reason=reason)
        if fail_after_audit: raise RuntimeError('M1 injected rollback after audit')
        response={'command_id':str(command_id),'case_id':str(case.pk),'case_version':case.version,
                  'result':{'role':role,'owner_id':str(new.pk)}}
        CommandReceipt.objects.create(actor=actor,route='reassign-owner',idempotency_key=key,
                                      request_hash=digest,case=case,response=response,status_code=200)
    return response,200
