"""Read-only public quiz (answers hidden) and authenticated server grading."""
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET,require_POST
from backend.accounts.models import Membership
from backend.common.http import error,InputError,json_payload,transient_db_response
from backend.onboarding.api_m2 import command,headers
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.models import Task
from backend.training.models import TrainingAttempt
from backend.training.definitions import public_spec
from backend.training import commands

@require_GET
def module(request,case_id,task_id):
    try:
        member,case=get_authorized_case(request.user,case_id)
        if member.role not in (Membership.HR,Membership.EMPLOYEE):
            return error('NOT_FOUND',404)
        task=Task.objects.filter(case=case,pk=task_id,kind='TRAINING').first()
        if task is None:return error('NOT_FOUND',404)
        spec=public_spec(task.evidence_spec)
        attempts=TrainingAttempt.objects.filter(task=task).order_by('attempt_number').values(
            'attempt_number','passed','score','passing_score','submitted_at')
        response=JsonResponse({'case_id':str(case.pk),'task_id':str(task.pk),'module':spec,
            'attempts':[{'number':r['attempt_number'],'passed':r['passed'],'score':r['score'],
                         'passing_score':r['passing_score'],
                         'submitted_at':r['submitted_at'].isoformat()} for r in attempts],
            'task_state':task.execution_state})
        response['Cache-Control']='private, no-store'
        return response
    except PermissionDenied:return error('NOT_FOUND',404)
    except CommandFailure as exc:return error(exc.code,exc.status)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@csrf_protect
@require_POST
def submit_attempt(request,case_id,task_id):
    def execute():
        data=json_payload(request,4096,{'module_version','content_sha256','answers'})
        if set(data)!=set(('module_version','content_sha256','answers')):
            raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return commands.attempt(actor=request.user,case_id=case_id,task_id=task_id,
             module_version=data['module_version'],content_sha256=data['content_sha256'],
             answers=data['answers'],key=key,expected_version=version)
    return command(execute)
