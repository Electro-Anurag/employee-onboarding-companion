"""Recipient-only inbox. Reading never grants case access or mutates status."""
import uuid
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET,require_POST
from django.views.decorators.csrf import csrf_protect
from backend.accounts.security import actor_context
from backend.onboarding.services import get_authorized_case,CommandFailure
from backend.notifications.models import Notification
from backend.notifications.services import (_candidate,current_handoff_candidate,
    escalation_candidate,HANDOFF_RULES)
from backend.notifications.policy import (BASE_POLICY_VERSION,
    ESCALATION_POLICY_VERSION,ESCALATION_RULE)


def _visible(user,notice,now):
    try:
        member,case=get_authorized_case(user,notice.case_id)
    except CommandFailure:
        return False
    if notice.recipient_id!=user.pk or case.pk!=notice.task.case_id:
        return False
    # Recipients lose private case access immediately after reassignment.
    if notice.intent.status!='DELIVERED' or notice.status!='ACTIVE':
        return False
    if case.status not in ('PRE_JOINING','ACTIVE'):
        return False
    if notice.intent.schedule_revision!=case.schedule_revision:
        return False
    if notice.task.version!=notice.intent.action_revision:
        return False
    if notice.task.due_at!=notice.intent.due_at:
        return False
    if notice.intent.rule_code in HANDOFF_RULES:
        if notice.intent.policy_version!=BASE_POLICY_VERSION:
            return False
        current=current_handoff_candidate(notice.task,case,now)
        return bool(current and current[0].pk==user.pk
            and current[1]==notice.intent.rule_code
            and current[2]==notice.intent.time_bucket)
    if notice.intent.rule_code==ESCALATION_RULE:
        if notice.intent.policy_version!=ESCALATION_POLICY_VERSION:
            return False
        current=escalation_candidate(notice.task,case,now)
        return bool(current and current[0].pk==user.pk
            and current[1]==notice.intent.rule_code
            and current[2]==notice.intent.time_bucket
            and current[3]==notice.intent.policy_version)
    if (notice.intent.rule_code not in ('DUE_SOON','OVERDUE_DAILY')
            or notice.intent.policy_version!=BASE_POLICY_VERSION):
        return False
    current=_candidate(notice.task,case,now)
    return bool(current and current[0].pk==user.pk
        and current[1]==notice.intent.rule_code
        and current[2]==notice.intent.time_bucket)


@require_GET
def inbox(request):
    try:
        actor_context(request.user)
        now=timezone.now()
        results=[]
        # Exclude retired or revision-stale history before the 100-item
        # result limit; otherwise it can crowd out an older live action.
        # _visible remains authoritative for role/assignment and time windows.
        qs=Notification.objects.filter(
            recipient=request.user,status='ACTIVE',intent__status='DELIVERED',
            case__status__in=('PRE_JOINING','ACTIVE'),
            intent__schedule_revision=F('case__schedule_revision'),
            intent__action_revision=F('task__version'),
            intent__due_at=F('task__due_at'),
        ).select_related('intent','task','case','case__organization','case__employee__user')
        for row in qs.order_by('-created_at')[:100]:
            if not _visible(request.user,row,now):
                continue
            results.append({'id':str(row.pk),'case_id':str(row.case_id),
                'task_id':str(row.task_id),'summary':row.summary,
                'rule_code':row.intent.rule_code,
                'policy_version':row.intent.policy_version,
                'created_at':row.created_at.isoformat(),
                'read_at':row.read_at.isoformat() if row.read_at else None,
                'status':'ACTIVE'})
        response=JsonResponse({'results':results,'delivery':'IN_APP_ONLY'})
        response['Cache-Control']='private, no-store'
        return response
    except (CommandFailure,ValueError):
        return JsonResponse({'error':{'code':'NOT_FOUND'}},status=404)


@csrf_protect
@require_POST
def mark_read(request,notification_id):
    try:
        actor_context(request.user)
        if request.body not in (b'',b'{}'):
            return JsonResponse({'error':{'code':'INVALID_BODY'}},status=422)
        with transaction.atomic():
            row=Notification.objects.select_for_update().select_related(
                'intent','task','case','case__organization','case__employee__user').filter(
                pk=notification_id,recipient=request.user).first()
            if row is None or not _visible(request.user,row,timezone.now()):
                raise CommandFailure('NOT_FOUND',404)
            if row.read_at is None:
                row.read_at=timezone.now()
                row.save(update_fields=['read_at'])
            response=JsonResponse({'id':str(row.pk),'read_at':row.read_at.isoformat()})
            response['Cache-Control']='private, no-store'
            return response
    except CommandFailure:
        return JsonResponse({'error':{'code':'NOT_FOUND'}},status=404)
