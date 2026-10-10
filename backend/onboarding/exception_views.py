"""M5 case-scoped exception journeys with real session, CSRF and version gates."""
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET,require_POST
from backend.common.http import error,InputError,json_payload,required_uuid,transient_db_response
from backend.onboarding.api_m2 import command,headers
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.models import CaseException
from backend.onboarding import exceptions as domain


@require_GET
def list_exceptions(request,case_id):
    try:
        member,case=get_authorized_case(request.user,case_id)
        rows=CaseException.objects.filter(case=case).select_related(
            'task','assignee').prefetch_related('events__actor').order_by('opened_at','id')[:150]
        results=[]
        for row in rows:
            entries=[{'id':str(evt.pk),'action':evt.action,
                'previous_status':evt.previous_status,'status':evt.status,
                'note':evt.note,'created_at':evt.created_at.isoformat()}
                for evt in row.events.all()]
            results.append({'id':str(row.pk),'task_id':str(row.task_id),
                'task_title':row.task.title,'cause':row.cause,'episode':row.episode,
                'status':row.status,'assignee_role':row.assignee.role if row.assignee_id else None,
                'reason':row.reason,'blocking_now':domain.predicate_active(
                    row.task,case,row.cause),
                'opened_at':row.opened_at.isoformat(),
                'resolved_at':row.resolved_at.isoformat() if row.resolved_at else None,
                'closed_at':row.closed_at.isoformat() if row.closed_at else None,
                'events':entries})
        result=JsonResponse({'case_id':str(case.pk),'case_version':case.version,
            'results':results})
        result['Cache-Control']='private, no-store'
        return result
    except (CommandFailure,PermissionDenied):
        return error('NOT_FOUND',404)
    except DatabaseError as exc:
        return transient_db_response(exc,preflight=True)


@csrf_protect
@require_POST
def open_exception(request,case_id):
    def run():
        body=json_payload(request,1200,{'task_id','cause','note'})
        if set(body)!={'task_id','cause','note'}:raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return domain.open_exception(actor=request.user,case_id=case_id,
            task_id=required_uuid(body['task_id']),cause=body['cause'],
            note=body['note'],key=key,expected_version=version)
    return command(run)


@csrf_protect
@require_POST
def transition(request,case_id,exception_id,action):
    def run():
        allowed={'assign':{'assignee_role','note'},
                 'resolve':{'note'},'close':{'note'}}
        if action not in allowed:raise InputError('INVALID_EXCEPTION_ACTION',422)
        body=json_payload(request,1200,allowed[action])
        if set(body)!=allowed[action]:raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        values={'actor':request.user,'case_id':case_id,
                'exception_id':exception_id,'note':body['note'],
                'key':key,'expected_version':version}
        if action=='assign':
            return domain.assign_exception(assignee_role=body['assignee_role'],**values)
        if action=='resolve':return domain.resolve_exception(**values)
        return domain.close_exception(**values)
    return command(run)
