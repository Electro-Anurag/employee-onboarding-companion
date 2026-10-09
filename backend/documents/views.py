"""Explicitly synthetic document upload, retrieval and HR review API."""
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse,HttpResponse,FileResponse,HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST,require_GET
from backend.accounts.models import Membership
from backend.common.http import error,InputError,required_uuid,transient_db_response,json_payload
from backend.onboarding.api_m2 import headers,command
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.models import Task
from backend.documents import commands
from backend.documents.fixtures import sample_for
from backend.documents.models import DocumentRevision

def _scoped(request,case_id,task_id):
    member,case=get_authorized_case(request.user,case_id)
    if member.role not in (Membership.EMPLOYEE,Membership.HR):
        raise CommandFailure('NOT_FOUND',404)
    task=Task.objects.filter(pk=task_id,case=case,kind='DOCUMENT').first()
    if task is None:raise CommandFailure('NOT_FOUND',404)
    return member,case,task

@csrf_protect
def revisions(request,case_id,task_id):
    if request.method=='POST':
        def execute():
            if not request.content_type.startswith('multipart/form-data'):
                raise InputError('MULTIPART_REQUIRED',415)
            if set(request.POST) or set(request.FILES)!=set(('file',)):
                raise InputError('SINGLE_DOCUMENT_FILE_REQUIRED',422)
            doc=request.FILES['file']
            if doc.size>4096:raise InputError('DOCUMENT_UPLOAD_LIMIT',413)
            if doc.content_type!='text/plain':raise InputError('SYNTHETIC_TEXT_ONLY',415)
            raw=doc.read(4097)
            key,version=headers(request,case_id)
            return commands.upload(actor=request.user,case_id=case_id,
               task_id=task_id,raw=raw,key=key,expected_version=version)
        return command(execute)
    if request.method!='GET':
        return HttpResponseNotAllowed(['GET','POST'])
    try:
        member,case,task=_scoped(request,case_id,task_id)
        records=[]
        for r in DocumentRevision.objects.filter(task=task).select_related('review').order_by('revision'):
            decision=getattr(r,'review',None)
            records.append({'id':str(r.pk),'revision':r.revision,
                'filename':r.filename,'content_sha256':r.content_sha256,
                'byte_length':r.byte_length,'uploaded_at':r.uploaded_at.isoformat(),
                'scan_status':r.scan_status,'scan_profile':r.scan_profile,'malware_scanned':False,
                'review':None if decision is None else {
                   'id':str(decision.pk),'decision':decision.decision,
                   'note':decision.note,'reviewed_at':decision.reviewed_at.isoformat()}})
        response=JsonResponse({'case_id':str(case.pk),'task_id':str(task.pk),
             'synthetic_only':True,'malware_scanned':False,
             'results':records,'task_completion':task.execution_state})
        response['Cache-Control']='private, no-store'
        return response
    except (PermissionDenied,CommandFailure):return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@require_GET
def sample(request,case_id,task_id):
    try:
        member,case,task=_scoped(request,case_id,task_id)
        content=sample_for(task)
        response=HttpResponse(content,content_type='text/plain; charset=utf-8')
        response['Content-Disposition']='attachment; filename="synthetic_'+task.key+'.txt"'
        response['Cache-Control']='private, no-store'
        response['X-Content-Type-Options']='nosniff'
        return response
    except (PermissionDenied,CommandFailure):return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@require_GET
def download(request,case_id,task_id,revision_id):
    try:
        member,case,task=_scoped(request,case_id,task_id)
        record=DocumentRevision.objects.filter(pk=revision_id,task=task).first()
        if record is None:return error('NOT_FOUND',404)
        response=HttpResponse(bytes(record.content),content_type='text/plain; charset=utf-8')
        response['Content-Disposition']='attachment; filename="'+record.filename+'"'
        response['Cache-Control']='private, no-store'
        response['X-Content-Type-Options']='nosniff'
        response['Content-Security-Policy']='sandbox'
        return response
    except (PermissionDenied,CommandFailure):return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@csrf_protect
@require_POST
def review(request,case_id,task_id,revision_id):
    def execute():
        data=json_payload(request,1024,{'decision','note'})
        if set(data)!=set(('decision','note')):
            raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return commands.review(actor=request.user,case_id=case_id,task_id=task_id,
            revision_id=revision_id,decision=data['decision'],note=data['note'],
            key=key,expected_version=version)
    return command(execute)
