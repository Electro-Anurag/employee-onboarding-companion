"""M1 authoritative case ownership and credential-issuance command boundaries."""
import hashlib
import json
import uuid
from django.db import transaction, connection
from django.utils import timezone
from backend.accounts.models import Membership, User, OneTimeToken
from backend.accounts.security import actor_context, issue_token
from backend.audit.models import CommandReceipt
from backend.audit.services import append_event
from backend.onboarding.models import CaseAssignment, OnboardingCase

class CommandFailure(Exception):
    def __init__(self,code,status=409):
        self.code,self.status=code,status

def set_command_timeouts():
    """Only normal web command transactions; migration/recovery roles have separate budgets."""
    if not connection.in_atomic_block:
        raise RuntimeError("Time limits must be set inside a transaction")
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL statement_timeout = '5s'")
        cursor.execute("SET LOCAL lock_timeout = '2s'")

def valid_case_root(case):
    """Fail closed even against legacy/malformed persisted membership relationships."""
    employee=case.employee
    return (employee.role==Membership.EMPLOYEE and
            employee.organization_id==case.organization_id and
            employee.active and employee.user.is_active)

def authorize_case(member,case):
    if (not member.active or not member.user.is_active or member.organization_id!=case.organization_id
            or not valid_case_root(case)):
        return False
    if member.role==Membership.EMPLOYEE:
        return case.employee_id==member.pk
    return case.assignments.filter(member=member,role=member.role,effective_to__isnull=True,
                                  effective_from__lte=timezone.now()).exists()

def get_authorized_case(user,case_id):
    member=actor_context(user)
    case=OnboardingCase.objects.select_related('employee__user').filter(pk=case_id).first()
    if case is None or not authorize_case(member,case):
        raise CommandFailure('NOT_FOUND',404)
    return member,case

def scoped_cases(user):
    member=actor_context(user)
    qs=OnboardingCase.objects.filter(organization_id=member.organization_id,
        employee__role=Membership.EMPLOYEE,employee__organization_id=member.organization_id,
        employee__active=True,employee__user__is_active=True)
    if member.role==Membership.EMPLOYEE:
        return qs.filter(employee=member)
    return qs.filter(assignments__member=member,assignments__role=member.role,
                     assignments__effective_to__isnull=True,
                     assignments__effective_from__lte=timezone.now()).distinct()

def case_summary(member,case):
    base={'id':str(case.pk),'joining_date':case.joining_date.isoformat(),'status':case.status,
          'version':case.version,'my_role':member.role,'allowed_actions':[]}
    base['employee_name']=case.employee.user.display_name
    if member.role==Membership.HR:
        base['employee_email']=case.employee.user.email
        base['allowed_actions']=['REASSIGN_IT','REASSIGN_MANAGER']
    return base

def issue_credential_for_case(*,actor,case_id,purpose):
    """Case lock -> actor User -> actor Membership -> target User is canonical order.

    A stale HR may not issue a token after a reassignment or account revocation.
    """
    if purpose not in (OneTimeToken.INVITE,OneTimeToken.RESET):
        raise CommandFailure('INVALID_PURPOSE',422)
    with transaction.atomic():
        set_command_timeouts()
        case=OnboardingCase.objects.select_for_update().select_related('employee__user').filter(pk=case_id).first()
        if case is None:
            raise CommandFailure('NOT_FOUND',404)
        member=actor_context(actor,locked=True)
        if member.role!=Membership.HR or not authorize_case(member,case):
            raise CommandFailure('NOT_FOUND',404)
        if not case.employee.active or not valid_case_root(case):
            raise CommandFailure('NOT_FOUND',404)
        token=issue_token(case.employee.user,purpose,actor)
        append_event(stream_key=f'case:{case.pk}',actor=actor,
                     event_type='INVITATION_ISSUED' if purpose==OneTimeToken.INVITE else 'RESET_ISSUED',
                     entity_id=case.pk,changes={'target_user_id':str(case.employee.user.pk)})
        return token

def reassign_owner(*,actor,case_id,role,new_member_id,reason,key,expected_version,command_id=None,fail_after_audit=False):
    if role not in (Membership.IT,Membership.MANAGER,Membership.HR):
        raise CommandFailure('INVALID_ROLE',422)
    if not isinstance(reason,str) or not reason.strip() or len(reason)>240:
        raise CommandFailure('REASON_REQUIRED',422)
    if not isinstance(key,uuid.UUID):
        raise CommandFailure('INVALID_IDEMPOTENCY_KEY',400)
    command_id=command_id or uuid.uuid4()
    canonical=json.dumps({'role':role,'new_member_id':str(new_member_id),'reason':reason},
                         sort_keys=True,separators=(',',':'))
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    with transaction.atomic():
        set_command_timeouts()
        case=OnboardingCase.objects.select_for_update().select_related('employee__user').filter(pk=case_id).first()
        if case is None:
            raise CommandFailure('NOT_FOUND',404)
        member=actor_context(actor,locked=True)
        if not authorize_case(member,case) or member.role!=Membership.HR:
            raise CommandFailure('NOT_FOUND',404)
        if role==Membership.HR and not member.can_coordinate_ownership:
            raise CommandFailure('FORBIDDEN',403)
        receipt=CommandReceipt.objects.filter(actor=actor,route='reassign-owner',idempotency_key=key).first()
        if receipt:
            if receipt.request_hash!=digest or receipt.case_id!=case_id:
                raise CommandFailure('IDEMPOTENCY_KEY_REUSED',409)
            return receipt.response,receipt.status_code
        if case.version!=expected_version:
            raise CommandFailure('STALE_VERSION',409)
        candidate=Membership.objects.filter(pk=new_member_id).values('user_id').first()
        if candidate is None:
            raise CommandFailure('INVALID_ASSIGNEE',422)
        # A User deactivation must not commit between eligibility and assignment.
        target_user=User.objects.select_for_update().filter(pk=candidate['user_id'],is_active=True).first()
        if target_user is None:
            raise CommandFailure('INVALID_ASSIGNEE',422)
        new=Membership.objects.select_for_update().filter(pk=new_member_id,
                        user_id=target_user.pk,organization_id=case.organization_id,
                        active=True,available=True,role=role).first()
        if new is None:
            raise CommandFailure('INVALID_ASSIGNEE',422)
        existing=CaseAssignment.objects.select_for_update().filter(case=case,role=role,
                        effective_to__isnull=True,effective_from__lte=timezone.now()).first()
        if existing is None:
            raise CommandFailure('ASSIGNMENT_MISSING',409)
        if existing.member_id==new.pk:
            raise CommandFailure('ALREADY_ASSIGNED',409)
        now=timezone.now()
        existing.effective_to=now
        existing.save(update_fields=['effective_to'])
        created=CaseAssignment.objects.create(case=case,role=role,member=new,
                        effective_from=now,assigned_by=member,reason=reason)
        case.version+=1
        case.save(update_fields=['version'])
        append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='OWNER_REASSIGNED',entity_id=case.pk,
                     command_id=command_id,changes={'role':role,
                         'previous_assignment_id':str(existing.pk),
                         'new_assignment_id':str(created.pk),
                         'new_member_id':str(new.pk),
                         'case_version':case.version},reason=reason)
        if fail_after_audit:
            raise RuntimeError('M1 injected rollback after audit')
        response={'command_id':str(command_id),'case_id':str(case.pk),'case_version':case.version,
                  'result':{'role':role,'owner_id':str(new.pk)}}
        CommandReceipt.objects.create(actor=actor,route='reassign-owner',
                       idempotency_key=key,request_hash=digest,case=case,
                       response=response,status_code=200)
    return response,200
