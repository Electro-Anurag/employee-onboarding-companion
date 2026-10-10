"""M5 bounded current-state reconciliation, never blind clock-tick replay.

Initial supported action kinds are owned typed tasks, not document/form review
handoffs. Unsupported handoffs must not receive incorrectly addressed alerts.
No external email/calendar sending is performed.
"""
import uuid
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.onboarding.models import OnboardingCase,Task
from backend.onboarding.state_machine import current_assignments,preview_task_state
from backend.notifications.models import ReminderIntent,Notification

REMINDABLE_KINDS=frozenset({
    'MANAGER_PREPARATION','ACCESS','EQUIPMENT','ACTIVITY',
    'INTRODUCTION','CHECK_IN','TRAINING','POLICY_ACK'
})
ACTIVE_CASES=('PRE_JOINING','ACTIVE')


def current_recipient(task,case,now):
    """Current assigned action-owner or None; never use stale FK on task."""
    if task.kind not in REMINDABLE_KINDS:
        return None
    state,_=preview_task_state(task,case,now)
    if state not in ('READY','IN_PROGRESS'):
        return None
    if task.owner_role==Membership.EMPLOYEE:
        member=case.employee
    else:
        assignment=current_assignments(case,now).get(task.owner_role)
        member=assignment.member if assignment is not None else None
    if (member is None or member.role!=task.owner_role
            or member.organization_id!=case.organization_id
            or not member.active or not member.available
            or not member.user.is_active):
        return None
    return member.user


def _candidate(task,case,now):
    person=current_recipient(task,case,now)
    if not person:
        return None
    if now>=task.due_at:
        local_date=now.astimezone(ZoneInfo(case.organization.timezone)).date().isoformat()
        return person,'OVERDUE_DAILY',local_date
    if task.due_at-timedelta(hours=24)<=now<task.due_at:
        return person,'DUE_SOON','due:'+task.due_at.isoformat()
    return None


def reconcile_case(case_id,*,now=None):
    """Idempotently reconcile one case under its row lock in the same DB txn.

    Intended for control-worker work only; no untrusted request controls now.
    External notification sending cannot occur in this function.
    """
    now=now or timezone.now()
    made=0
    retired=0
    with transaction.atomic():
        case=OnboardingCase.objects.select_for_update(of=('self',)).select_related(
            'organization','employee__user').filter(pk=case_id).first()
        if case is None:
            return {'created':0,'retired':0}
        assignments=list(case.assignments.filter(effective_to__isnull=True,
            effective_from__lte=now).select_related('member__user'))
        by_role={a.role:a for a in assignments}
        tasks=list(Task.objects.filter(case=case).order_by('key'))
        for task in tasks:
            candidate=(_candidate(task,case,now)
                       if case.status in ACTIVE_CASES else None)
            active=list(ReminderIntent.objects.filter(case=case,task=task,
                status='DELIVERED'))
            current_identities=set()
            if candidate:
                person,rule,bucket=candidate
                current_identities.add((str(person.pk),case.schedule_revision,
                                        task.version,rule,bucket))
            for intent in active:
                identity=(str(intent.recipient_id),intent.schedule_revision,
                          intent.action_revision,intent.rule_code,intent.time_bucket)
                if (identity not in current_identities
                        or intent.due_at!=task.due_at):
                    intent.status='SUPERSEDED'
                    intent.save(update_fields=['status'])
                    notice=Notification.objects.filter(intent=intent).first()
                    if notice is not None and notice.status=='ACTIVE':
                        notice.status=('RESOLVED' if task.execution_state=='COMPLETED'
                                       else 'SUPERSEDED')
                        notice.save(update_fields=['status'])
                    retired+=1
            if not candidate:
                continue
            person,rule,bucket=candidate
            reminder,created=ReminderIntent.objects.get_or_create(
                subject_type='TASK',task=task,schedule_revision=case.schedule_revision,
                action_revision=task.version,recipient=person,
                rule_code=rule,time_bucket=bucket,
                defaults={'case':case,'due_at':task.due_at})
            if created:
                Notification.objects.create(intent=reminder,case=case,task=task,
                    recipient=person,
                    summary=('Overdue: ' if rule=='OVERDUE_DAILY' else 'Due soon: ')+task.title)
                made+=1
            elif reminder.status!='DELIVERED':
                # An old revision/rule identity cannot be silently revived.
                pass
    return {'created':made,'retired':retired}


def reconcile_batch(*,now=None,after=None,limit=100):
    """Deterministic, bounded cursor; caller owns continuation scheduling."""
    if type(limit) is not int or not 1<=limit<=100:
        raise ValueError('INVALID_RECONCILIATION_LIMIT')
    now=now or timezone.now()
    qs=OnboardingCase.objects.order_by('id').values_list('id',flat=True)
    if after is not None:
        qs=qs.filter(pk__gt=uuid.UUID(str(after)))
    ids=list(qs[:limit+1])
    more=len(ids)>limit
    totals={'created':0,'retired':0}
    for case_id in ids[:limit]:
        result=reconcile_case(case_id,now=now)
        for field in totals:totals[field]+=result[field]
    return {**totals,'processed':min(len(ids),limit),
            'next_cursor':str(ids[limit-1]) if more else None}
