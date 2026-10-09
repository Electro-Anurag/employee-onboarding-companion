"""Case-scoped activity history and versioned organizer commands."""
from datetime import datetime
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET,require_POST
from backend.accounts.models import Membership
from backend.common.http import error,InputError,json_payload,required_uuid,transient_db_response
from backend.onboarding.api_m2 import command,headers
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.models import Task
from backend.activities.models import ActivityOccurrence
from backend.activities import commands

@require_GET
def history(request,case_id,task_id):
    try:
        member,case=get_authorized_case(request.user,case_id)
        if member.role==Membership.IT:return error('NOT_FOUND',404)
        task=Task.objects.filter(case=case,pk=task_id,
            kind__in=['ACTIVITY','INTRODUCTION','CHECK_IN']).first()
        if task is None:return error('NOT_FOUND',404)
        if member.role==Membership.MANAGER and (task.owner_role!=Membership.MANAGER
             or not case.assignments.filter(pk=task.owner_assignment_id,
                 member=member,role=Membership.MANAGER,effective_to__isnull=True).exists()):
            return error('NOT_FOUND',404)
        if member.role==Membership.EMPLOYEE and case.employee_id!=member.pk:
            return error('NOT_FOUND',404)
        result=[]
        for occ in ActivityOccurrence.objects.filter(task=task).order_by('revision'):
            attendance=getattr(occ,'attendance',None)
            result.append({'id':str(occ.pk),'revision':occ.revision,
                'start':occ.begins_at.isoformat(),'end':occ.ends_at.isoformat(),
                'medium':occ.medium,'meeting_reference':occ.meeting_reference,
                'reason':occ.reason,
                'attendance':None if attendance is None else {
                    'id':str(attendance.pk),'outcome':attendance.outcome,
                    'note':attendance.note}})
        response=JsonResponse({'case_id':str(case.pk),'task_id':str(task.pk),
            'task_state':task.execution_state,'current_revision':result[-1]['revision'] if result else None,
            'results':result})
        response['Cache-Control']='private, no-store'
        return response
    except (PermissionDenied,CommandFailure):return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@csrf_protect
@require_POST
def schedule(request,case_id,task_id):
    def execute():
        data=json_payload(request,2048,{'start','end','medium','meeting_reference','reason'})
        if set(data)!=set(('start','end','medium','meeting_reference','reason')):
            raise InputError('MISSING_FIELD',422)
        def iso(value):
            if not isinstance(value,str):raise InputError('INVALID_TIMESTAMP',422)
            try:return datetime.fromisoformat(value.replace('Z','+00:00'))
            except ValueError:raise InputError('INVALID_TIMESTAMP',422)
        key,version=headers(request,case_id)
        return commands.schedule(actor=request.user,case_id=case_id,task_id=task_id,
            start=iso(data['start']),end=iso(data['end']),medium=data['medium'],
            reference=data['meeting_reference'],reason=data['reason'],
            key=key,expected_version=version)
    return command(execute)

@csrf_protect
@require_POST
def attendance(request,case_id,task_id,occurrence_id):
    def execute():
        data=json_payload(request,1024,{'outcome','note'})
        if set(data)!=set(('outcome','note')):raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return commands.record_attendance(actor=request.user,case_id=case_id,task_id=task_id,
             occurrence_id=occurrence_id,outcome=data['outcome'],note=data['note'],
             key=key,expected_version=version)
    return command(execute)
