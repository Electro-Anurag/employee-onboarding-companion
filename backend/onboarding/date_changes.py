"""M5 joining-date impact preview and human-committed reschedule.

A preview is a read-only projection of the *current* case/template/task state.
Commit rechecks its digest under the canonical M2 case/actor lock before
touching deadlines; prior evidence and started tasks retain their timestamps.
"""
import hashlib
import json
import uuid
from datetime import date,timedelta
from zoneinfo import ZoneInfo
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.audit.services import append_event
from backend.onboarding.commands import _command_case,_receipt
from backend.onboarding.models import OnboardingCase,Task,CaseDateChange
from backend.onboarding.services import CommandFailure,get_authorized_case,set_command_timeouts
from backend.onboarding.state_machine import scheduled_at,preview_task_state,recompute
from backend.notifications.models import ReminderIntent,Notification


def _assert_allowed(case,new_date):
    if type(new_date) is not date:
        raise CommandFailure('INVALID_JOINING_DATE',422)
    if case.status!='PRE_JOINING':
        raise CommandFailure('DATE_CHANGE_REQUIRES_PRE_JOINING',409)
    today=timezone.localdate(timezone=ZoneInfo(case.organization.timezone))
    if new_date<today or new_date>today+timedelta(days=365):
        raise CommandFailure('DATE_OUTSIDE_APPROVED_WINDOW',422)
    if new_date==case.joining_date:
        raise CommandFailure('JOINING_DATE_UNCHANGED',409)


def _plan(case,new_date):
    _assert_allowed(case,new_date)
    tasks=list(Task.objects.filter(case=case).select_related(
        'template_task').order_by('key')[:61])
    if not tasks or len(tasks)>60:
        raise CommandFailure('INVALID_CASE_TASK_SNAPSHOT',409)
    changes=[]
    preserved=[]
    digest_tasks=[]
    for task in tasks:
        # Existing task timestamps are independent historical evidence.
        # Do not rewrite due/available times after any work or completion.
        keep=(task.work_started_at is not None
              or task.completed_at is not None
              or task.execution_state in ('COMPLETED','CANCELLED'))
        spec=task.template_task
        if spec.version_id!=case.template_version_id or spec.key!=task.key:
            raise CommandFailure('TASK_TEMPLATE_MISMATCH',409)
        before_start=task.available_at.isoformat()
        before_due=task.due_at.isoformat()
        new_start=scheduled_at(new_date,spec.available_offset_days,
            case.organization.timezone,spec.available_local_time)
        new_due=scheduled_at(new_date,spec.due_offset_days,
            case.organization.timezone,spec.due_local_time)
        if new_start>new_due:
            raise CommandFailure('INVALID_SHIFTED_TASK_SCHEDULE',409)
        if keep:
            after_start=task.available_at
            after_due=task.due_at
            preserved.append(str(task.pk))
        else:
            after_start=new_start
            after_due=new_due
        digest_tasks.append({
            'id':str(task.pk),'template_id':str(task.template_task_id),
            'version':task.version,'state':task.execution_state,
            'started_at':task.work_started_at.isoformat() if task.work_started_at else None,
            'completed_at':task.completed_at.isoformat() if task.completed_at else None,
            'start':before_start,'due':before_due,
            'next_start':after_start.isoformat(),'next_due':after_due.isoformat(),
            'preserve':keep})
        if not keep and (task.available_at!=after_start or task.due_at!=after_due):
            changes.append({'task_id':str(task.pk),'title':task.title,
                'old_available_at':before_start,'old_due_at':before_due,
                'new_available_at':after_start.isoformat(),
                'new_due_at':after_due.isoformat()})
    raw={'case':str(case.pk),'case_version':case.version,
        'schedule_revision':case.schedule_revision,'old':case.joining_date.isoformat(),
        'new':new_date.isoformat(),'tasks':digest_tasks}
    digest=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'case_id':str(case.pk),'case_version':case.version,
        'schedule_revision':case.schedule_revision,
        'old_joining_date':case.joining_date.isoformat(),
        'new_joining_date':new_date.isoformat(),
        'preview_digest':digest,'changes':changes,
        'preserved_task_ids':preserved,'change_count':len(changes),
        'preserved_count':len(preserved),
        'warnings':(['Started/completed tasks keep historical timestamps and evidence.']
                    if preserved else [])},tasks


def preview_change(*,actor,case_id,new_date,expected_version):
    member,case=get_authorized_case(actor,case_id)
    if member.role!=Membership.HR:
        raise CommandFailure('NOT_FOUND',404)
    if type(expected_version) is not int or case.version!=expected_version:
        raise CommandFailure('STALE_VERSION',409)
    case=OnboardingCase.objects.select_related('organization').get(pk=case.pk)
    return _plan(case,new_date)[0]


def commit_change(*,actor,case_id,new_date,preview_digest,reason,key,expected_version):
    if (not isinstance(reason,str) or not 8<=len(reason.strip())<=240
            or not isinstance(preview_digest,str) or len(preview_digest)!=64
            or any(c not in '0123456789abcdef' for c in preview_digest)):
        raise CommandFailure('INVALID_DATE_CHANGE_CONFIRMATION',422)
    reason=reason.strip()
    payload={'new_joining_date':new_date.isoformat() if isinstance(new_date,date) else str(new_date),
        'preview_digest':preview_digest,'reason':reason}
    with transaction.atomic():
        set_command_timeouts()
        case,member,prior,digest=_command_case(actor,case_id,
            'm5-joining-date-commit',key,payload,expected_version,True)
        if prior is not None:
            return prior.response,prior.status_code
        # Same transaction and row lock as other case commands. A simultaneous
        # task completion/ownership edit changes the digest or case version.
        plan,tasks=_plan(case,new_date)
        if plan['preview_digest']!=preview_digest:
            raise CommandFailure('STALE_DATE_CHANGE_PREVIEW',409)
        # The forward-only M5 DB guard checks this write-once decision and
        # the precise prior/new task timestamps before permitting any task
        # schedule update. All changes are in one atomic transaction.
        old_date=case.joining_date
        case.joining_date=new_date
        case.schedule_revision+=1
        current_revision=case.schedule_revision
        case.version+=1
        case.save(update_fields=['joining_date','schedule_revision','version'])
        decision=CaseDateChange.objects.create(case=case,revision=current_revision,
            prior_date=old_date,joining_date=new_date,preview_digest=preview_digest,
            reason=reason,changed_by=actor,changes=plan['changes'],
            preserved_task_ids=plan['preserved_task_ids'])
        new_by_id={uuid.UUID(x['task_id']):x for x in plan['changes']}
        for task in tasks:
            candidate=new_by_id.get(task.pk)
            if candidate is None:
                continue
            task.available_at=__import__('datetime').datetime.fromisoformat(
                candidate['new_available_at'])
            task.due_at=__import__('datetime').datetime.fromisoformat(
                candidate['new_due_at'])
            task.version+=1
            task.save(update_fields=['available_at','due_at','version'])
        changed_states=recompute(case)
        # Old notifications MUST lose authority in this same transaction;
        # the next scheduled reconciliation emits only the new revision.
        current=ReminderIntent.objects.filter(case=case,status='DELIVERED')
        Notification.objects.filter(intent__in=current,status='ACTIVE').update(
            status='SUPERSEDED')
        retired=current.update(status='SUPERSEDED')
        audit=append_event(stream_key=f'case:{case.pk}',actor=actor,
            event_type='M5_JOINING_DATE_CHANGED',entity_id=decision.pk,
            changes={'old_date':old_date.isoformat(),
                'new_date':new_date.isoformat(),'schedule_revision':current_revision,
                'case_version':case.version,'changed_tasks':len(plan['changes']),
                'preserved_tasks':len(plan['preserved_task_ids']),
                'retired_reminders':retired,'preview_digest':preview_digest,
                'recomputed_states':len(changed_states)})
        response={'case_id':str(case.pk),'case_version':case.version,
            'result':{'decision_id':str(decision.pk),'joining_date':new_date.isoformat(),
                'schedule_revision':current_revision,'changed_tasks':len(plan['changes']),
                'preserved_tasks':len(plan['preserved_task_ids']),
                'retired_reminders':retired},'event_ids':[str(audit[0])]}
        _receipt(actor,'m5-joining-date-commit',key,digest,case,response,200)
    return response,200
