"""M1 authoritative case ownership and credential-issuance command boundaries."""
import hashlib
import json
import uuid
from django.db import transaction, connection, models
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
    # New M2 cases are private to their creating HR until activation; legacy
    # M1 setup-shell cases retain their originally qualified visibility.
    if case.status=='CREATED' and case.created_by_id is not None:
        return (member.role==Membership.HR and case.assignments.filter(
            member=member,role=Membership.HR,effective_to__isnull=True,
            effective_from__lte=timezone.now()).exists())
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
    if member.role!=Membership.HR:
        qs=qs.filter(models.Q(created_by__isnull=True) | ~models.Q(status='CREATED'))
    if member.role==Membership.EMPLOYEE:
        return qs.filter(employee=member)
    return qs.filter(assignments__member=member,assignments__role=member.role,
                     assignments__effective_to__isnull=True,
                     assignments__effective_from__lte=timezone.now()).distinct()

def case_summary(member,case):
    base={'id':str(case.pk),'joining_date':case.joining_date.isoformat(),'status':case.status,
          'version':case.version,'my_role':member.role,'allowed_actions':[]}
    base['employee_name']=case.employee.user.display_name
    if case.template_version_id is not None:
        from backend.onboarding.state_machine import case_progress
        base['progress']=case_progress(case)
    if member.role==Membership.HR:
        base['employee_email']=case.employee.user.email
        base['allowed_actions']=['REASSIGN_IT','REASSIGN_MANAGER']
    return base

def _lock_case_authority(case,actor,candidate_member_id=None):
    """Canonical case -> sorted User IDs -> sorted Membership IDs ordering.

    Preliminary unlocked lookups are IDs only; no authorization claim is accepted
    until *all* rows have been locked and the relationships are revalidated.
    Never use select_related with select_for_update on the initial case.
    """
    actor_hints=list(Membership.objects.filter(user_id=actor.pk,active=True)
                     .values_list('pk',flat=True)[:2])
    if len(actor_hints)!=1:
        raise CommandFailure('NOT_FOUND',404)
    actor_mid=actor_hints[0]
    root_hint=Membership.objects.filter(pk=case.employee_id).values('user_id').first()
    candidate_hint=(Membership.objects.filter(pk=candidate_member_id).values('user_id').first()
                    if candidate_member_id is not None else None)
    if root_hint is None:
        raise CommandFailure('NOT_FOUND',404)
    # Candidate hints/eligibility are not authoritative for a historical
    # committed receipt; a missing candidate only rejects a NEW transition.
    user_ids={actor.pk,root_hint['user_id']}
    if candidate_hint is not None:
        user_ids.add(candidate_hint['user_id'])
    locked_users={}
    for uid in sorted(user_ids,key=str):
        locked_users[uid]=User.objects.select_for_update().filter(pk=uid).first()
    # Only currently authorized actor and case-root identities may fail here.
    # Candidate User may have been deactivated after the original command.
    if any(locked_users.get(uid) is None or not locked_users[uid].is_active
           for uid in (actor.pk, root_hint['user_id'])):
        raise CommandFailure('NOT_FOUND',404)

    mids={actor_mid,case.employee_id}
    if candidate_member_id is not None:
        mids.add(candidate_member_id)
    locked_members={}
    for mid in sorted(mids,key=str):
        locked_members[mid]=Membership.objects.select_for_update().filter(pk=mid).first()
    if locked_members.get(actor_mid) is None or locked_members.get(case.employee_id) is None:
        raise CommandFailure('NOT_FOUND',404)
    member=locked_members[actor_mid]
    root=locked_members[case.employee_id]
    if not member.active or member.user_id!=actor.pk:
        raise CommandFailure('NOT_FOUND',404)
    if (not root.active or root.user_id!=root_hint['user_id']
            or root.organization_id!=case.organization_id
            or root.role!=Membership.EMPLOYEE):
        raise CommandFailure('NOT_FOUND',404)

    # FKs cannot change under an M1 case root; the fresh locked lookup is
    # authoritative even if actor's in-memory session user was loaded earlier.
    if not locked_users[actor.pk].is_active or not locked_users[root.user_id].is_active:
        raise CommandFailure('NOT_FOUND',404)
    member.user=locked_users[actor.pk]
    root.user=locked_users[root.user_id]
    candidate=locked_members.get(candidate_member_id) if candidate_member_id is not None else None
    # Inconsistent/missing candidate identity must reject NEW transitions, but
    # must never suppress a historical receipt for an authorized caller.
    if candidate is not None and (candidate_hint is None
            or candidate.user_id!=candidate_hint['user_id']
            or locked_users.get(candidate.user_id) is None
            or not locked_users[candidate.user_id].is_active):
        candidate=None
    return member,root,candidate


def issue_credential_for_case(*,actor,case_id,purpose,_test_after_case_lock=None):
    """Recheck HR + employee authority while holding stable ordered row locks."""
    if purpose not in (OneTimeToken.INVITE,OneTimeToken.RESET):
        raise CommandFailure('INVALID_PURPOSE',422)
    with transaction.atomic():
        set_command_timeouts()
        case=OnboardingCase.objects.select_for_update(of=('self',)).filter(pk=case_id).first()
        if case is None:
            raise CommandFailure('NOT_FOUND',404)
        if _test_after_case_lock is not None:
            _test_after_case_lock()  # internal regression instrumentation only
        member,root,_=_lock_case_authority(case,actor)
        if member.role!=Membership.HR or not authorize_case(member,case):
            raise CommandFailure('NOT_FOUND',404)
        target=root.user
        token=issue_token(target,purpose,actor)
        append_event(stream_key=f'case:{case.pk}',actor=actor,
                     event_type='INVITATION_ISSUED' if purpose==OneTimeToken.INVITE else 'RESET_ISSUED',
                     entity_id=case.pk,changes={'target_user_id':str(target.pk)})
        return token

def reassign_owner(*,actor,case_id,role,new_member_id,reason,key,expected_version,command_id=None,fail_after_audit=False,_test_after_case_lock=None):
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
        case=OnboardingCase.objects.select_for_update(of=('self',)).filter(pk=case_id).first()
        if case is None:
            raise CommandFailure('NOT_FOUND',404)
        if _test_after_case_lock is not None:
            _test_after_case_lock()  # deterministic two-case interleaving test
        member,root,new=_lock_case_authority(case,actor,candidate_member_id=new_member_id)
        if not authorize_case(member,case) or member.role!=Membership.HR:
            raise CommandFailure('NOT_FOUND',404)
        if role==Membership.HR and not member.can_coordinate_ownership:
            raise CommandFailure('FORBIDDEN',403)
        # Cross-case use of one global actor/route/key must never escape as
        # an unhandled unique-constraint error after two independent case locks.
        key_bytes=hashlib.sha256(f'{actor.pk}:reassign-owner:{key}'.encode()).digest()
        lock_id=int.from_bytes(key_bytes[:8],'big',signed=True)
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)',[lock_id])
        receipt=CommandReceipt.objects.filter(actor=actor,route='reassign-owner',idempotency_key=key).first()
        if receipt:
            if receipt.request_hash!=digest or receipt.case_id!=case_id:
                raise CommandFailure('IDEMPOTENCY_KEY_REUSED',409)
            return receipt.response,receipt.status_code
        if case.version!=expected_version:
            raise CommandFailure('STALE_VERSION',409)
        # Idempotent earlier receipts were returned above. New owner changes
        # must never mutate a terminal onboarding case or its audit history.
        if case.status not in ('CREATED','PRE_JOINING','ACTIVE'):
            raise CommandFailure('CASE_NOT_MUTABLE',409)
        if (new is None or not new.active or not new.available or new.role!=role
                or new.organization_id!=case.organization_id
                or not new.user.is_active):
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
        if case.status in ('PRE_JOINING','ACTIVE') and case.template_version_id is not None:
            from backend.onboarding.state_machine import recompute
            recompute(case)
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
