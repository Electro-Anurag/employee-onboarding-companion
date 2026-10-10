"""M5 real predicate-gated exception episodes, not status-only dismissals.

All transitions run through M2's case lock, current actor reauthorization,
idempotency receipt and append-only case audit. Underlying typed task evidence
is never altered here.
"""
import uuid
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.audit.services import append_event
from backend.onboarding.commands import _command_case,_receipt
from backend.onboarding.models import (Task,CaseException,CaseExceptionEvent,
                                       EXCEPTION_CAUSES)
from backend.onboarding.services import (CommandFailure,set_command_timeouts)
from backend.onboarding.state_machine import preview_task_state,current_assignments

LIVE_CASES=('PRE_JOINING','ACTIVE')


def _note(value):
    if not isinstance(value,str) or not 8<=len(value.strip())<=240:
        raise CommandFailure('EXCEPTION_NOTE_REQUIRED',422)
    return value.strip()


def predicate_active(task,case,cause,now=None):
    """State comes solely from the authoritative graph, never a client flag."""
    now=now or timezone.now()
    if case.status not in LIVE_CASES or task.execution_state in ('COMPLETED','CANCELLED'):
        return False
    state,blocked=preview_task_state(task,case,now)
    if cause=='PREREQUISITE_BLOCKED':
        return 'PREREQUISITE_INCOMPLETE' in blocked
    if cause=='OWNER_UNAVAILABLE':
        return 'OWNER_UNAVAILABLE' in blocked
    if cause=='TASK_OVERDUE':
        return now>task.due_at
    return False


def _record(case,exc,actor,action,old_status,note):
    entry=CaseExceptionEvent.objects.create(exception=exc,actor=actor,action=action,
        previous_status=old_status,status=exc.status,note=note)
    event=append_event(stream_key=f'case:{case.pk}',actor=actor,
        event_type='M5_EXCEPTION_'+action,entity_id=exc.pk,
        changes={'task_id':str(exc.task_id),'cause':exc.cause,'episode':exc.episode,
                 'status':exc.status,'prior_status':old_status,'case_version':case.version})
    return str(entry.pk),str(event[0])


def _response(case,exc,event_ids,code):
    return {'case_id':str(case.pk),'case_version':case.version,
        'result':{'id':str(exc.pk),'task_id':str(exc.task_id),'cause':exc.cause,
            'episode':exc.episode,'status':exc.status,
            'assignee_role':exc.assignee.role if exc.assignee_id else None},
        'event_ids':event_ids},code


def open_exception(*,actor,case_id,task_id,cause,note,key,expected_version):
    if cause not in EXCEPTION_CAUSES:
        raise CommandFailure('INVALID_EXCEPTION_CAUSE',422)
    note=_note(note)
    payload={'task_id':str(task_id),'cause':cause,'note':note}
    with transaction.atomic():
        set_command_timeouts()
        case,member,prior,digest=_command_case(actor,case_id,'m5-exception-open',
            key,payload,expected_version)
        if prior is not None:return prior.response,prior.status_code
        task=Task.objects.filter(case=case,pk=task_id).first()
        if task is None:raise CommandFailure('NOT_FOUND',404)
        if not predicate_active(task,case,cause):
            raise CommandFailure('EXCEPTION_PREDICATE_NOT_ACTIVE',409)
        episodes=CaseException.objects.filter(case=case,task=task,cause=cause)
        if episodes.exclude(status='CLOSED').exists():
            raise CommandFailure('EXCEPTION_ALREADY_ACTIVE',409)
        last=episodes.order_by('-episode').first()
        number=(last.episode+1 if last else 1)
        exc=CaseException.objects.create(case=case,task=task,cause=cause,
            episode=number,status='OPEN',reason=note,opened_by=actor)
        case.version+=1
        case.save(update_fields=['version'])
        event_id,audit_id=_record(case,exc,actor,'OPEN','',note)
        response,code=_response(case,exc,[event_id,audit_id],201)
        _receipt(actor,'m5-exception-open',key,digest,case,response,code)
    return response,code


def _transition(*,actor,case_id,exception_id,action,note,key,
                expected_version,assignee_role=None):
    note=_note(note)
    if action not in ('ASSIGN','RESOLVE','CLOSE'):
        raise CommandFailure('UNKNOWN_EXCEPTION_TRANSITION',422)
    if action=='ASSIGN' and assignee_role not in ('HR','IT','MANAGER'):
        raise CommandFailure('INVALID_EXCEPTION_ASSIGNEE_ROLE',422)
    payload={'exception_id':str(exception_id),'action':action,'note':note}
    if action=='ASSIGN':payload['assignee_role']=assignee_role
    route='m5-exception-'+action.lower()
    with transaction.atomic():
        set_command_timeouts()
        case,member,prior,digest=_command_case(actor,case_id,route,key,payload,expected_version)
        if prior is not None:return prior.response,prior.status_code
        exc=CaseException.objects.select_for_update().select_related(
            'task','assignee').filter(case=case,pk=exception_id).first()
        if exc is None:raise CommandFailure('NOT_FOUND',404)
        if case.status not in LIVE_CASES:
            raise CommandFailure('CASE_NOT_ACTIVE',409)
        now=timezone.now()
        assignments=current_assignments(case,now)
        if action=='ASSIGN':
            if member.role!=Membership.HR or exc.status not in ('OPEN','ASSIGNED'):
                raise CommandFailure('EXCEPTION_TRANSITION_FORBIDDEN',409)
            owner=assignments.get(assignee_role)
            if (owner is None or not owner.member.active or not owner.member.available
                    or not owner.member.user.is_active or owner.member.role!=assignee_role
                    or owner.member.organization_id!=case.organization_id):
                raise CommandFailure('EXCEPTION_ASSIGNEE_UNAVAILABLE',409)
            assigned=owner.member
            if exc.status=='ASSIGNED' and exc.assignee_id==assigned.pk:
                raise CommandFailure('EXCEPTION_ALREADY_ASSIGNED',409)
            old=exc.status
            exc.status='ASSIGNED';exc.assignee=assigned
            exc.save(update_fields=['status','assignee'])
        elif action=='RESOLVE':
            if exc.status!='ASSIGNED':
                raise CommandFailure('EXCEPTION_NOT_ASSIGNED',409)
            current=assignments.get(exc.assignee.role) if exc.assignee_id else None
            if (member.role!=Membership.HR and
                (member.pk!=exc.assignee_id or current is None
                 or current.member_id!=member.pk)):
                raise CommandFailure('NOT_FOUND',404)
            if predicate_active(exc.task,case,exc.cause,now):
                raise CommandFailure('EXCEPTION_PREDICATE_STILL_ACTIVE',409)
            old=exc.status
            exc.status='RESOLVED';exc.resolved_at=now
            exc.save(update_fields=['status','resolved_at'])
        else:
            if member.role!=Membership.HR or exc.status!='RESOLVED':
                raise CommandFailure('EXCEPTION_TRANSITION_FORBIDDEN',409)
            if predicate_active(exc.task,case,exc.cause,now):
                raise CommandFailure('EXCEPTION_PREDICATE_RECURRED',409)
            old=exc.status
            exc.status='CLOSED';exc.closed_at=now
            exc.save(update_fields=['status','closed_at'])
        case.version+=1
        case.save(update_fields=['version'])
        event_id,audit_id=_record(case,exc,actor,action,old,note)
        response,code=_response(case,exc,[event_id,audit_id],200)
        _receipt(actor,route,key,digest,case,response,code)
    return response,code


def assign_exception(*,actor,case_id,exception_id,assignee_role,note,key,expected_version):
    return _transition(actor=actor,case_id=case_id,exception_id=exception_id,
        action='ASSIGN',assignee_role=assignee_role,note=note,
        key=key,expected_version=expected_version)


def resolve_exception(*,actor,case_id,exception_id,note,key,expected_version):
    return _transition(actor=actor,case_id=case_id,exception_id=exception_id,
        action='RESOLVE',note=note,key=key,expected_version=expected_version)


def close_exception(*,actor,case_id,exception_id,note,key,expected_version):
    return _transition(actor=actor,case_id=case_id,exception_id=exception_id,
        action='CLOSE',note=note,key=key,expected_version=expected_version)
