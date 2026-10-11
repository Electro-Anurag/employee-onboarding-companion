"""Read-only, HR-scoped M7 case dashboard from authoritative typed evidence.

Advisory snapshot only. No completion commands, email, notifications or
materialized/fabricated progress. The case command rechecks evidence on write.
"""
from django.utils import timezone
from backend.accounts.models import Membership
from backend.onboarding.models import Task,TaskCompletion,CaseException
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.state_machine import preview_task_state,case_progress

OWNER_ROLES=("EMPLOYEE","HR","IT","MANAGER")


def case_dashboard(actor,case_id):
    member,case=get_authorized_case(actor,case_id)
    if member.role != Membership.HR or not member.available:
        raise CommandFailure("NOT_FOUND",404)
    tasks=list(Task.objects.filter(case=case).order_by("key")[:61])
    if len(tasks)>60:
        raise CommandFailure("DASHBOARD_TASK_LIMIT",409)
    now=timezone.now()
    completed=set(TaskCompletion.objects.filter(
        task__case=case,task__required=True,task__applicable=True
    ).values_list("task_id",flat=True))
    roles={role:{"mandatory_total":0,"mandatory_completed":0,
                 "actionable":0,"blocked":0,"overdue":0}
           for role in OWNER_ROLES}
    states={"READY":0,"IN_PROGRESS":0,"BLOCKED":0,
            "NOT_STARTED":0,"NEEDS_CLARIFICATION":0,
            "COMPLETED":0,"CANCELLED":0}
    for task in tasks:
        if not (task.required and task.applicable):
            continue
        state,_=preview_task_state(task,case,now)
        verified=state=="COMPLETED" and task.pk in completed
        role=roles.get(task.owner_role)
        if role is None:
            raise CommandFailure("DASHBOARD_INVALID_OWNER_ROLE",409)
        role["mandatory_total"]+=1
        role["mandatory_completed"]+=int(verified)
        states[state]=states.get(state,0)+1
        if not verified:
            if state in ("READY","IN_PROGRESS"):
                role["actionable"]+=1
            if state=="BLOCKED":
                role["blocked"]+=1
            if now>task.due_at and state not in ("CANCELLED",):
                role["overdue"]+=1
    active=CaseException.objects.filter(
        case=case,status__in=("OPEN","ASSIGNED","RESOLVED"))
    return {
        "case_id":str(case.pk),"case_version":case.version,
        "case_status":case.status,"as_of":now.isoformat(),
        "progress":case_progress(case),"by_role":roles,
        "states":states,"unclosed_exceptions":active.count(),
        "open_exceptions":active.filter(status__in=("OPEN","ASSIGNED")).count(),
        "resolved_pending_hr_close":active.filter(status="RESOLVED").count(),
        "scope":"REQUIRED_APPLICABLE_TASKS_ONLY",
    }
