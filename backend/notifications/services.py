"""M5 bounded current-state reconciliation, never blind clock-tick replay.

Review handoffs require the current immutable form submission or exact
document revision. No private answers, filenames or document bytes leave
the evidence domain; no email or calendar delivery is claimed.
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


HANDOFF_RULES=frozenset({
    'FORM_HR_REVIEW','FORM_CORRECTION',
    'DOCUMENT_HR_REVIEW','DOCUMENT_CORRECTION'
})


def _eligible_actor(case,role,now):
    """Resolve a *current* available role, never a historical task owner."""
    if role==Membership.EMPLOYEE:
        member=case.employee
    else:
        assignment=current_assignments(case,now).get(role)
        member=assignment.member if assignment is not None else None
    if (member is None or member.organization_id!=case.organization_id
            or member.role!=role or not member.active or not member.available
            or not member.user.is_active):
        return None
    return member.user


def current_handoff_candidate(task,case,now):
    """Exact current workflow handoff or None; never guess pending review.

    Return recipient, rule, immutable source-revision UUID. The UUID fits the
    existing <=40-character reminder bucket and cannot expose form answers,
    PDF names, uploaded bytes, or reviewer notes.
    """
    if case.status not in ACTIVE_CASES or task.kind not in ('FORM','DOCUMENT'):
        return None
    if task.execution_state in ('COMPLETED','CANCELLED'):
        return None
    state,_=preview_task_state(task,case,now)
    if state!='IN_PROGRESS':
        return None
    if task.kind=='FORM':
        from backend.forms.models import FormSubmission,FormReview
        latest=FormSubmission.objects.filter(task=task).order_by('-revision').first()
        if latest is None:
            return None
        decision=FormReview.objects.filter(submission=latest).values_list(
            'decision',flat=True).first()
        if decision=='ACCEPTED':
            return None
        role=Membership.EMPLOYEE if decision=='CHANGES_REQUESTED' else Membership.HR
        rule='FORM_CORRECTION' if decision=='CHANGES_REQUESTED' else 'FORM_HR_REVIEW'
        source_id=latest.pk
    else:
        from backend.documents.real_models import SecureUpload,SecureCleanObject,SecureHRReview
        from backend.documents.models import DocumentRevision,DocumentReview
        upload=SecureUpload.objects.filter(task=task).order_by('-revision').first()
        if upload is not None:
            # A quarantined/unscanned PDF MUST NEVER trigger HR review.
            clean=SecureCleanObject.objects.filter(upload=upload,
                scan__outcome='CLEAN').first()
            if clean is None:
                return None
            decision=SecureHRReview.objects.filter(clean=clean).values_list(
                'decision',flat=True).first()
            source_id=upload.pk
        else:
            latest=DocumentRevision.objects.filter(task=task).order_by('-revision').first()
            if latest is None or latest.scan_status!='VALIDATED_SYNTHETIC':
                return None
            decision=DocumentReview.objects.filter(revision=latest).values_list(
                'decision',flat=True).first()
            source_id=latest.pk
        if decision=='ACCEPTED':
            return None
        correction=decision in ('REJECTED','NEEDS_CLARIFICATION')
        role=Membership.EMPLOYEE if correction else Membership.HR
        rule='DOCUMENT_CORRECTION' if correction else 'DOCUMENT_HR_REVIEW'
    person=_eligible_actor(case,role,now)
    return (person,rule,str(source_id)) if person is not None else None


def _summary_for(task,rule):
    # No employee answers, document names, reviewer messages or PHI/PII.
    action=('HR review required' if rule.endswith('HR_REVIEW')
            else 'Correction required' if rule.endswith('CORRECTION')
            else 'Overdue' if rule=='OVERDUE_DAILY' else 'Due soon')
    return (action+': '+task.title)[:200]


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
            candidate=(current_handoff_candidate(task,case,now)
                       if task.kind in ('FORM','DOCUMENT') else
                       _candidate(task,case,now) if case.status in ACTIVE_CASES
                       else None)
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
                    recipient=person,summary=_summary_for(task,rule))
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
