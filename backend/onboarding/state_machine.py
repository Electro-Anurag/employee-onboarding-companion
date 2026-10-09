"""Deterministic M2 task eligibility; no frontend-supplied status and no generic completion."""
from datetime import datetime,time,timedelta
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from django.utils import timezone
from backend.accounts.models import Membership
from backend.onboarding.models import Task,TaskDependency,CaseAssignment

def scheduled_at(joining_date,offset,zone,local_clock):
    try: tz=ZoneInfo(zone)
    except ZoneInfoNotFoundError: raise ValueError('INVALID_ORGANIZATION_TIMEZONE')
    hour,minute=[int(x) for x in local_clock.split(':')]
    return datetime.combine(joining_date+timedelta(days=offset),time(hour=hour,minute=minute),tzinfo=tz)

def current_assignments(case,now):
    current=CaseAssignment.objects.filter(case=case,effective_to__isnull=True,effective_from__lte=now)
    return {x.role:x for x in current.select_related('member__user')}

def owner_valid(task,case,assignments):
    if task.owner_role==Membership.EMPLOYEE:
        return case.employee.active and case.employee.user.is_active and case.employee.available
    assignment=assignments.get(task.owner_role)
    return bool(assignment and assignment.member.active and assignment.member.available
                and assignment.member.user.is_active and assignment.member.role==task.owner_role
                and assignment.member.organization_id==case.organization_id)

def recompute(case,*,now=None):
    """Caller owns the OnboardingCase row lock. Evaluate all <=60 descendants."""
    if case.status not in ('PRE_JOINING','ACTIVE'):
        return []
    now=now or timezone.now()
    tasks=list(Task.objects.select_for_update().filter(case=case).order_by('key'))
    if len(tasks)>60:
        raise ValueError('TASK_LIMIT_EXCEEDED')
    by_id={t.pk:t for t in tasks}
    dependencies=list(TaskDependency.objects.filter(case=case).values_list('predecessor_id','successor_id'))
    parents={t.pk:set() for t in tasks}
    for predecessor,successor in dependencies:
        if predecessor not in by_id or successor not in by_id:
            raise ValueError('CROSS_CASE_DEPENDENCY')
        parents[successor].add(predecessor)
    completed={t.pk for t in tasks if t.execution_state=='COMPLETED' and hasattr(t,'completion')}
    owners=current_assignments(case,now)
    changes=[]
    for t in tasks:
        if t.execution_state in ('COMPLETED','CANCELLED'):
            continue
        blockers=[]
        if any(parent not in completed for parent in parents[t.pk]):
            blockers.append('PREREQUISITE_INCOMPLETE')
        if not owner_valid(t,case,owners):
            blockers.append('OWNER_UNAVAILABLE')
        if blockers:
            new='BLOCKED'
        elif now<t.available_at:
            new='NOT_STARTED'
        elif t.work_started_at is not None:
            new='IN_PROGRESS'
        else:
            new='READY'
        owner=owners.get(t.owner_role)
        new_owner=(owner if t.owner_role!=Membership.EMPLOYEE else None)
        if (new!=t.execution_state or blockers!=t.blocked_reason_codes
                or t.owner_assignment_id!=(new_owner.pk if new_owner else None)):
            previous=t.execution_state
            t.execution_state=new
            t.blocked_reason_codes=blockers
            t.owner_assignment=new_owner
            t.version+=1
            t.save(update_fields=['execution_state','blocked_reason_codes','owner_assignment','version'])
            changes.append({'task_id':str(t.pk),'key':t.key,'from':previous,'to':new})
    return changes

def project_task_states(case,tasks,*,now=None):
    """Read-only time/owner projection; commands remain serialized authority.

    A GET never alters version, audit, task state, or receipts. Work becomes
    actionable on time without requiring an unrelated mutation/scheduler.
    """
    now=now or timezone.now()
    rows=list(tasks)
    if len(rows)>60:
        raise ValueError('TASK_LIMIT_EXCEEDED')
    if case.status not in ('PRE_JOINING','ACTIVE'):
        return {t.pk:{'state':t.execution_state,
                      'blocked_reason_codes':blockers,
                      'owner_assignment_id':t.owner_assignment_id} for t in rows}
    ids={t.pk for t in rows}
    parents={tid:set() for tid in ids}
    for before,after in TaskDependency.objects.filter(case=case).values_list(
            'predecessor_id','successor_id'):
        if before not in ids or after not in ids:
            raise ValueError('CROSS_CASE_DEPENDENCY')
        parents[after].add(before)
    from backend.onboarding.models import TaskCompletion
    completed=set(TaskCompletion.objects.filter(task__case=case,
            task__execution_state='COMPLETED').values_list('task_id',flat=True))
    assignments=current_assignments(case,now)
    projected={}
    for t in rows:
        assignment=assignments.get(t.owner_role)
        owner_id=(assignment.pk if assignment is not None and t.owner_role!=Membership.EMPLOYEE else None)
        if t.execution_state in ('COMPLETED','CANCELLED'):
            projected[t.pk]={'state':t.execution_state,'blocked_reason_codes':[],
                             'owner_assignment_id':owner_id}
            continue
        blocked=[]
        if any(before not in completed for before in parents[t.pk]):
            blocked.append('PREREQUISITE_INCOMPLETE')
        if not owner_valid(t,case,assignments):
            blocked.append('OWNER_UNAVAILABLE')
        if blocked:
            state='BLOCKED'
        elif now<t.available_at:
            state='NOT_STARTED'
        elif t.work_started_at is not None:
            state='IN_PROGRESS'
        else:
            state='READY'
        projected[t.pk]={'state':state,'blocked_reason_codes':blocked,
                         'owner_assignment_id':owner_id}
    return projected

def summary_task(t,member,case,projected=None):
    role=member.role
    current=(projected or {}).get(t.pk,{})
    live_state=current.get('state',t.execution_state)
    blockers=current.get('blocked_reason_codes',t.blocked_reason_codes)
    owner_id=current.get('owner_assignment_id',t.owner_assignment_id)
    ownerscope=(t.owner_role==role and (
        case.employee_id==member.pk if role==Membership.EMPLOYEE else
        case.assignments.filter(pk=owner_id,member=member,role=role,
                                effective_to__isnull=True,
                                effective_from__lte=timezone.now()).exists()))
    actions=[]
    if case.status in ('PRE_JOINING','ACTIVE') and ownerscope:
        if live_state=='READY': actions.append('START')
        if t.kind=='MANAGER_PREPARATION' and live_state in ('READY','IN_PROGRESS'):
            actions.append('ATTEST_MANAGER_PREPARATION')
    return {'id':str(t.pk),'key':t.key,'kind':t.kind,'title':t.title,
        'required':t.required,'state':live_state,'owner_role':t.owner_role,
        'available_at':t.available_at.isoformat(),'due_at':t.due_at.isoformat(),
        'overdue':live_state not in ('COMPLETED','CANCELLED') and timezone.now()>t.due_at,
        'blocked_reason_codes':t.blocked_reason_codes,'started_at':t.work_started_at.isoformat() if t.work_started_at else None,
        'completed_at':t.completed_at.isoformat() if t.completed_at else None,
        'version':t.version,'allowed_actions':actions}

def case_progress(case):
    qs=Task.objects.filter(case=case,required=True,applicable=True)
    total=qs.count()
    completed=qs.filter(execution_state='COMPLETED',completion__isnull=False).count()
    return {'mandatory_total':total,'mandatory_completed':completed,'mandatory_remaining':total-completed,
            'percent':round((completed/total)*100,1) if total else 0}
