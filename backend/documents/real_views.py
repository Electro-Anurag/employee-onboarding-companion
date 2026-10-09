"""Case-authorized proxied S3 upload, scan-state read, HR review and download."""
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET,require_POST
from backend.accounts.models import Membership
from backend.common.http import error,InputError,json_payload,transient_db_response
from backend.onboarding.api_m2 import command,headers
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.models import Task
from backend.documents import real_commands as commands,storage
from backend.documents.real_models import (SecureUpload,StoredQuarantineObject,
    SecureCleanObject,SecureScanAttempt,SecureHRReview)

def _scope(request,case_id,task_id):
    member,case=get_authorized_case(request.user,case_id)
    if member.role not in (Membership.EMPLOYEE,Membership.HR):
        raise CommandFailure('NOT_FOUND',404)
    task=Task.objects.filter(pk=task_id,case=case,kind='DOCUMENT').first()
    if task is None:raise CommandFailure('NOT_FOUND',404)
    return member,case,task

@csrf_protect
@require_POST
def prepare(request,case_id,task_id):
    def run():
        data=json_payload(request,1024,{'sha256','size','filename'})
        if set(data)!={'sha256','size','filename'}:raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return commands.prepare(actor=request.user,case_id=case_id,
            task_id=task_id,sha256=data['sha256'],size=data['size'],
            filename=data['filename'],key=key,expected_version=version)
    return command(run)

@csrf_protect
@require_POST
def receive(request,case_id,task_id,upload_id):
    def run():
        if not request.content_type.startswith('multipart/form-data'):
            raise InputError('MULTIPART_REQUIRED',415)
        if set(request.POST) or set(request.FILES)!={'file'}:
            raise InputError('SINGLE_DOCUMENT_REQUIRED',422)
        file=request.FILES['file']
        if file.size>storage.MAX_FILE:raise InputError('DOCUMENT_TOO_LARGE',413)
        if file.content_type!='application/pdf':
            raise InputError('PDF_ONLY',415)
        key,version=headers(request,case_id)
        return commands.receive(actor=request.user,case_id=case_id,
            task_id=task_id,upload_id=upload_id,raw=file.read(storage.MAX_FILE+1),
            key=key,expected_version=version)
    return command(run)

@require_GET
def history(request,case_id,task_id):
    try:
        member,case,task=_scope(request,case_id,task_id)
        output=[]
        for upload in SecureUpload.objects.filter(task=task).order_by('revision'):
            clean=SecureCleanObject.objects.filter(upload=upload).first()
            review=SecureHRReview.objects.filter(clean=clean).first() if clean else None
            attempts=list(SecureScanAttempt.objects.filter(upload=upload).order_by('number')
                          .values('number','outcome','scanned_at'))
            output.append({'id':str(upload.pk),'revision':upload.revision,
                'filename':upload.filename,'size':upload.byte_length,'sha256':upload.sha256,
                'state':commands._status(upload),'quarantine_stored':StoredQuarantineObject.objects.filter(upload=upload).exists(),
                'scan_attempts':[{'number':a['number'],'outcome':a['outcome'],
                                  'at':a['scanned_at'].isoformat()} for a in attempts],
                'clean_version_verified':bool(clean),
                'review':None if review is None else {'id':str(review.pk),
                    'decision':review.decision,'note':review.note},
                'download_available':bool(clean)})
        response=JsonResponse({'case_id':str(case.pk),'task_id':str(task.pk),
            'enabled':storage.configured(),'task_state':task.execution_state,
            'results':output,'synthetic_fixtures_separate':True})
        response['Cache-Control']='private, no-store'
        return response
    except (PermissionDenied,CommandFailure):return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@require_GET
def download(request,case_id,task_id,upload_id):
    try:
        member,case,task=_scope(request,case_id,task_id)
        upload=SecureUpload.objects.filter(pk=upload_id,task=task).first()
        if not upload:return error('NOT_FOUND',404)
        clean=SecureCleanObject.objects.select_related('upload').filter(upload=upload).first()
        if not clean:return error('NOT_FOUND',404)
        body=storage.download(clean)
        response=HttpResponse(body,content_type='application/pdf')
        response['Content-Disposition']='attachment; filename="'+upload.filename+'"'
        response['Cache-Control']='private, no-store'
        response['X-Content-Type-Options']='nosniff'
        response['Content-Security-Policy']='sandbox'
        return response
    except (PermissionDenied,CommandFailure):return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)

@csrf_protect
@require_POST
def review(request,case_id,task_id,upload_id):
    def run():
        data=json_payload(request,1024,{'decision','note'})
        if set(data)!={'decision','note'}:raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return commands.review(actor=request.user,case_id=case_id,
            task_id=task_id,upload_id=upload_id,decision=data['decision'],
            note=data['note'],key=key,expected_version=version)
    return command(run)
