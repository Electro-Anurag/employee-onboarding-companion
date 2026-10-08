"""Scoped template HTTP endpoints. No publish, update or clone bypasses service authority."""
from django.core.exceptions import PermissionDenied
from django.db import transaction,DatabaseError,IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods,require_POST
from backend.accounts.security import actor_context
from backend.common.http import error,InputError,json_payload,required_uuid,transient_db_response
from backend.onboarding.services import set_command_timeouts
from backend.onboarding.commands import _lock_receipt,_receipt
from backend.templates import services

def _apply(request,route,tag,payload,execute,success=200):
    try:
        actor_context(request.user)
        key=required_uuid(request.headers.get('Idempotency-Key',''))
        with transaction.atomic():
            set_command_timeouts()
            previous,digest=_lock_receipt(request.user,route,key,None,{'tag':tag,'data':payload})
            if previous:
                return JsonResponse(previous.response,status=previous.status_code)
            result=execute()
            _receipt(request.user,route,key,digest,None,result,success)
        return JsonResponse(result,status=success)
    except services.TemplateFailure as exc: return error(exc.code,exc.status)
    except InputError as exc:return error(exc.code,exc.status)
    except PermissionDenied:return error('FORBIDDEN',403)
    except IntegrityError:return error('CONFLICTING_TEMPLATE_STATE',409)
    except DatabaseError as exc:return transient_db_response(exc,idempotent=True)

@csrf_protect
@require_http_methods(['GET','POST'])
def collection(request):
    if request.method=='GET':
        try:return JsonResponse({'results':services.list_templates(request.user)})
        except PermissionDenied:return error('FORBIDDEN',403)
        except DatabaseError as exc:return transient_db_response(exc,preflight=True)
    try:data=json_payload(request,65536,{'key','name','tasks','dependencies','use_default'})
    except InputError as exc:return error(exc.code,exc.status)
    if data.get('use_default') is True:
        if set(data)!={'use_default'}:return error('UNKNOWN_FIELD',422)
        return _apply(request,'m2-template-create','default',data,
                      lambda:services.create_default(actor=request.user),201)
    if set(data)!=set(('key','name','tasks','dependencies')):
        return error('INVALID_TEMPLATE',422)
    return _apply(request,'m2-template-create',data.get('key'),data,
        lambda:services.create_template(actor=request.user,key=data['key'],name=data['name'],
                                        tasks=data['tasks'],edges=data['dependencies']),201)

@require_http_methods(['GET'])
def detail(request,template_id):
    try:return JsonResponse(services.read_template(actor=request.user,template_id=template_id))
    except services.TemplateFailure as exc:return error(exc.code,exc.status)
    except PermissionDenied:return error('FORBIDDEN',403)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

def _revision(request,template_id):
    match=request.headers.get('If-Match','')
    prefix=f'"template:{template_id}:r'
    if not match.startswith(prefix) or not match.endswith('"'):
        raise InputError('PRECONDITION_REQUIRED',428)
    try:revision=int(match[len(prefix):-1])
    except ValueError:raise InputError('INVALID_ETAG',422)
    if revision<1:raise InputError('INVALID_ETAG',422)
    return revision

@csrf_protect
@require_http_methods(['PATCH'])
def draft(request,template_id):
    try:
        revision=_revision(request,template_id)
        data=json_payload(request,65536,{'tasks','dependencies'})
        if set(data)!=set(('tasks','dependencies')):raise InputError('INVALID_TEMPLATE',422)
    except InputError as exc:return error(exc.code,exc.status)
    return _apply(request,'m2-template-edit',str(template_id),{'revision':revision,**data},
        lambda:services.edit_template(actor=request.user,template_id=template_id,
            revision=revision,tasks=data['tasks'],edges=data['dependencies']))

@csrf_protect
@require_POST
def publish(request,template_id):
    try:
        revision=_revision(request,template_id)
        json_payload(request,1024,set())
    except InputError as exc:return error(exc.code,exc.status)
    return _apply(request,'m2-template-publish',str(template_id),{'revision':revision},
        lambda:services.publish_template(actor=request.user,template_id=template_id,revision=revision))

@csrf_protect
@require_POST
def clone(request,template_id):
    try:json_payload(request,1024,set())
    except InputError as exc:return error(exc.code,exc.status)
    return _apply(request,'m2-template-clone',str(template_id),{},
        lambda:services.next_draft(actor=request.user,template_id=template_id),201)
