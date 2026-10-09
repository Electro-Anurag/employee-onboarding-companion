"""IT-only commands; HR/IT case-authorized read of synthetic operations."""
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET,require_POST
from backend.accounts.models import Membership
from backend.common.http import error,InputError,json_payload,transient_db_response
from backend.onboarding.api_m2 import headers,command
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.models import Task
from backend.provisioning import commands
from backend.provisioning.models import ITOperation

@csrf_protect
@require_POST
def request_it(request,case_id,task_id):
    def execute():
        json_payload(request,1024,set())
        key,version=headers(request,case_id)
        return commands.request_it(actor=request.user,case_id=case_id,task_id=task_id,
                                   key=key,expected_version=version)
    return command(execute)

@csrf_protect
@require_POST
def simulate_it(request,case_id,task_id):
    def execute():
        data=json_payload(request,1024,{'note'})
        if set(data)!={'note'}:raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return commands.simulate_fulfillment(actor=request.user,case_id=case_id,
                 task_id=task_id,note=data['note'],key=key,expected_version=version)
    return command(execute)

@require_GET
def operation_detail(request,case_id,task_id):
    try:
        member,case=get_authorized_case(request.user,case_id)
        if member.role not in (Membership.IT,Membership.HR):
            return error('NOT_FOUND',404)
        task=Task.objects.filter(pk=task_id,case=case,kind__in=['ACCESS','EQUIPMENT']).first()
        if task is None:return error('NOT_FOUND',404)
        if member.role==Membership.IT and not case.assignments.filter(
                member=member,role='IT',effective_to__isnull=True).exists():
            return error('NOT_FOUND',404)
        operation=ITOperation.objects.filter(task=task).first()
        if operation is None:return error('NOT_FOUND',404)
        return JsonResponse({'task_id':str(task.pk),'operation_id':str(operation.pk),
            'state':operation.status,'provider':'SYNTHETIC_ONLY',
            'simulation_digest':operation.simulation_digest or None,
            'task_completion':'NOT_YET_SUPPORTED'})
    except (PermissionDenied,CommandFailure):return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)
