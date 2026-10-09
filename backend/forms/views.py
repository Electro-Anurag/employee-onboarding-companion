"""M3 case- and role-scoped form endpoints."""
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse,HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from backend.accounts.models import Membership
from backend.common.http import error,InputError,json_payload,transient_db_response
from backend.onboarding.api_m2 import headers,command
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.models import Task
from backend.forms import commands
from backend.forms.models import FormSubmission

@csrf_protect
def submissions(request,case_id,task_id):
    if request.method=='POST':
        def execute():
            data=json_payload(request,5000,{'answers'})
            if set(data)!={'answers'}:raise InputError('MISSING_FIELD',422)
            key,version=headers(request,case_id)
            return commands.submit(actor=request.user,case_id=case_id,task_id=task_id,
                                   answers=data['answers'],key=key,expected_version=version)
        return command(execute)
    if request.method!='GET':return HttpResponseNotAllowed(['GET','POST'])
    try:
        member,case=get_authorized_case(request.user,case_id)
        if member.role not in (Membership.EMPLOYEE,Membership.HR):
            return error('NOT_FOUND',404)
        task=Task.objects.filter(pk=task_id,case=case,kind='FORM').first()
        if task is None:return error('NOT_FOUND',404)
        results=[]
        for item in FormSubmission.objects.filter(task=task).select_related('review').order_by('revision'):
            decision=getattr(item,'review',None)
            results.append({'id':str(item.pk),'revision':item.revision,'answers':item.answers,
                'submitted_at':item.submitted_at.isoformat(),'content_hash':item.content_hash,
                'review':None if decision is None else {'decision':decision.decision,
                    'note':decision.note,'reviewed_at':decision.reviewed_at.isoformat()}})
        return JsonResponse({'case_id':str(case.pk),'task_id':str(task.pk),'results':results,
                            'task_completion':'NOT_YET_SUPPORTED'})
    except (PermissionDenied,CommandFailure):return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@csrf_protect
@require_POST
def review_submission(request,case_id,task_id,submission_id):
    def execute():
        data=json_payload(request,1024,{'decision','note'})
        if set(data)!={'decision','note'}:raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return commands.review(actor=request.user,case_id=case_id,task_id=task_id,
            submission_id=submission_id,decision=data['decision'],note=data['note'],
            key=key,expected_version=version)
    return command(execute)
