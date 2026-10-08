"""Authenticated M2 case/task API: no direct client status writes."""
from datetime import date
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError,IntegrityError
from django.http import JsonResponse,HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET,require_POST
from backend.accounts.models import Membership
from backend.accounts.security import actor_context
from backend.common.http import error,InputError,json_payload,required_uuid,transient_db_response
from backend.onboarding import views as m1
from backend.onboarding import commands
from backend.onboarding.services import CommandFailure,get_authorized_case,scoped_cases
from backend.onboarding.models import Task
from backend.onboarding.state_machine import summary_task,case_progress

@csrf_protect
def cases_collection(request):
    if request.method=='GET':return m1.cases(request)
    if request.method=='POST':return create_case(request)
    return HttpResponseNotAllowed(['GET','POST'])

def headers(request,case_id):
    key=required_uuid(request.headers.get('Idempotency-Key',''))
    prefix=f'"case:{case_id}:v'
    match=request.headers.get('If-Match','')
    if not match.startswith(prefix) or not match.endswith('"'):
        raise InputError('PRECONDITION_REQUIRED',428)
    try:version=int(match[len(prefix):-1])
    except ValueError:raise InputError('INVALID_ETAG',422)
    if version<1:raise InputError('INVALID_ETAG',422)
    return key,version

def command(execute):
    try:
        result,status=execute()
        return JsonResponse(result,status=status)
    except CommandFailure as exc:return error(exc.code,exc.status)
    except InputError as exc:return error(exc.code,exc.status)
    except PermissionDenied:return error('NOT_FOUND',404)
    except IntegrityError:return error('CONFLICTING_DOMAIN_STATE',409,retryable=False)
    except DatabaseError as exc:return transient_db_response(exc,idempotent=True)

@require_POST
def create_case(request):
    def execute():
        data=json_payload(request,4096,{'employee_id','template_version_id','joining_date','owners'})
        if set(data)!=set(('employee_id','template_version_id','joining_date','owners')):
            raise InputError('MISSING_FIELD',422)
        raw_date=data.get('joining_date')
        if not isinstance(raw_date,str) or len(raw_date)!=10:raise InputError('INVALID_DATE',422)
        try: joining=date.fromisoformat(raw_date)
        except ValueError:raise InputError('INVALID_DATE',422)
        if not isinstance(data['owners'],dict) or set(data['owners'])!=set(('IT','MANAGER')):
            raise InputError('INVALID_CASE_OWNERS',422)
        owners={k:required_uuid(v) for k,v in data['owners'].items()}
        key=required_uuid(request.headers.get('Idempotency-Key',''))
        return commands.create_case(actor=request.user,employee_id=required_uuid(data['employee_id']),
                  template_version_id=required_uuid(data['template_version_id']),joining_date=joining,
                  owner_ids=owners,key=key)
    return command(execute)

@csrf_protect
@require_POST
def activate(request,case_id):
    def execute():
        json_payload(request,1024,set())
        key,version=headers(request,case_id)
        return commands.activate_case(actor=request.user,case_id=case_id,key=key,expected_version=version)
    return command(execute)

@require_GET
def tasks(request,case_id):
    try:
        member,case=get_authorized_case(request.user,case_id)
        qs=Task.objects.filter(case=case).select_related('owner_assignment').order_by('due_at','key')[:100]
        return JsonResponse({'case_id':str(case.pk),'case_status':case.status,
            'case_version':case.version,'progress':case_progress(case),
            'tasks':[summary_task(t,member,case) for t in qs]})
    except CommandFailure as exc:return error(exc.code,exc.status)
    except PermissionDenied:return error('UNAUTHENTICATED',401)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@require_GET
def task_detail(request,case_id,task_id):
    try:
        member,case=get_authorized_case(request.user,case_id)
        task=Task.objects.filter(case=case,pk=task_id).first()
        if task is None:return error('NOT_FOUND',404)
        return JsonResponse({'case_id':str(case.pk),'case_version':case.version,
                             'task':summary_task(task,member,case)})
    except CommandFailure as exc:return error(exc.code,exc.status)
    except PermissionDenied:return error('UNAUTHENTICATED',401)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@csrf_protect
@require_POST
def task_start(request,case_id,task_id):
    def execute():
        json_payload(request,1024,set())
        key,version=headers(request,case_id)
        return commands.start_task(actor=request.user,case_id=case_id,task_id=task_id,key=key,
                                   expected_version=version)
    return command(execute)

@csrf_protect
@require_POST
def manager_attest(request,case_id,task_id):
    def execute():
        data=json_payload(request,4096,{'prepared_fields','note'})
        if set(data)!=set(('prepared_fields','note')):raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return commands.attest_manager(actor=request.user,case_id=case_id,task_id=task_id,
                 fields=data['prepared_fields'],note=data['note'],key=key,expected_version=version)
    return command(execute)

@require_GET
def workspaces_me(request):
    try:
        member=actor_context(request.user)
        cases=scoped_cases(request.user).filter(status__in=['PRE_JOINING','ACTIVE'])
        if member.role==Membership.EMPLOYEE:
            qs=Task.objects.filter(case__in=cases,owner_role='EMPLOYEE',case__employee=member)
        else:
            qs=Task.objects.filter(case__in=cases,owner_role=member.role,
                 owner_assignment__member=member,owner_assignment__effective_to__isnull=True)
        qs=qs.select_related('case','case__employee__user','owner_assignment').order_by('due_at','id')[:100]
        return JsonResponse({'role':member.role,'results':[
            {'case_id':str(t.case_id),'employee_name':t.case.employee.user.display_name,
             **summary_task(t,member,t.case)} for t in qs]})
    except PermissionDenied:return error('UNAUTHENTICATED',401)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@require_GET
def available_owners(request):
    try:
        member=actor_context(request.user)
        if member.role!=Membership.HR:return error('FORBIDDEN',403)
        role=request.GET.get('role','')
        if role not in ('EMPLOYEE','HR','IT','MANAGER'):
            return error('INVALID_ROLE',422)
        qs=Membership.objects.select_related('user').filter(
            organization_id=member.organization_id,role=role,active=True,available=True,
            user__is_active=True).order_by('user__display_name','pk')[:100]
        return JsonResponse({'role':role,'results':[{'id':str(x.pk),'name':x.user.display_name} for x in qs]})
    except PermissionDenied:return error('UNAUTHENTICATED',401)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)


@require_GET
def case_timeline(request,case_id):
    """Case-scoped events; IT/manager see only their own task events."""
    try:
        member,case=get_authorized_case(request.user,case_id)
        from backend.audit.models import AuditEvent
        stream='case:'+str(case.pk)
        qs=AuditEvent.objects.filter(stream_id=stream).select_related('actor').order_by('sequence')[:100]
        role=member.role
        if role in ('IT','MANAGER'):
            task_ids=list(Task.objects.filter(case=case,owner_role=role,
                owner_assignment__member=member,owner_assignment__effective_to__isnull=True)
                .values_list('pk',flat=True))
            qs=qs.filter(entity_id__in=task_ids,event_type__in=['TASK_STARTED','TASK_COMPLETED'])
        elif role=='EMPLOYEE':
            task_ids=list(Task.objects.filter(case=case,owner_role='EMPLOYEE').values_list('pk',flat=True))
            qs=qs.filter(entity_id__in=task_ids,event_type__in=['TASK_STARTED','TASK_COMPLETED'])
        payload=[]
        for event in qs:
            row={'id':str(event.pk),'sequence':event.sequence,'event_type':event.event_type,
                 'created_at':event.created_at.isoformat()}
            if role=='HR':
                row.update(entity_id=str(event.entity_id) if event.entity_id else None,
                           reason=event.reason,changes=event.sanitized_change,
                           actor_id=str(event.actor_id) if event.actor_id else None)
            payload.append(row)
        return JsonResponse({'case_id':str(case.pk),'results':payload})
    except CommandFailure as exc:return error(exc.code,exc.status)
    except PermissionDenied:return error('UNAUTHENTICATED',401)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)
