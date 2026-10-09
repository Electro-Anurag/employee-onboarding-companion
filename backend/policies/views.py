"""Explicit policy read/ack endpoints scoped to the authorized onboarding case."""
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET,require_POST
from backend.accounts.models import Membership
from backend.onboarding.models import Task
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.api_m2 import headers,command
from backend.common.http import error,InputError,json_payload,transient_db_response
from backend.policies.commands import validated_policy,acknowledge

@require_GET
def assigned_policy(request,case_id,task_id):
    try:
        member,case=get_authorized_case(request.user,case_id)
        if member.role not in (Membership.HR,Membership.EMPLOYEE):
            return error('NOT_FOUND',404)
        task=Task.objects.filter(pk=task_id,case=case,kind='POLICY_ACK').first()
        if task is None:return error('NOT_FOUND',404)
        policy=validated_policy(task)
        return JsonResponse({'task_id':str(task.pk),'case_id':str(case.pk),
            'policy':policy,'acknowledged':task.execution_state=='COMPLETED'})
    except CommandFailure as exc:return error(exc.code,exc.status)
    except PermissionDenied:return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@csrf_protect
@require_POST
def acknowledge_policy(request,case_id,task_id):
    def execute():
        data=json_payload(request,1024,{'policy_version','content_sha256','accepted'})
        if set(data)!={'policy_version','content_sha256','accepted'}:
            raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return acknowledge(actor=request.user,case_id=case_id,task_id=task_id,
            policy_version=data['policy_version'],content_sha256=data['content_sha256'],
            accepted=data['accepted'],key=key,expected_version=version)
    return command(execute)
