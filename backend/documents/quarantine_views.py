"""Optional local-only quarantine intake. No document release endpoints."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET,require_POST
from backend.accounts.models import Membership
from backend.common.http import error,InputError,transient_db_response
from backend.onboarding.api_m2 import headers,command
from backend.onboarding.services import CommandFailure,get_authorized_case
from backend.onboarding.models import Task
from backend.documents.quarantine_models import QuarantinedDocument
from backend.documents import quarantine_commands as operations

def scoped(request,case_id,task_id):
    if not operations.enabled():raise CommandFailure('NOT_FOUND',404)
    member,case=get_authorized_case(request.user,case_id)
    if member.role not in (Membership.EMPLOYEE,Membership.HR):
        raise CommandFailure('NOT_FOUND',404)
    task=Task.objects.filter(case=case,pk=task_id,kind='DOCUMENT').first()
    if task is None:raise CommandFailure('NOT_FOUND',404)
    return member,case,task

@csrf_protect
@require_POST
def intake(request,case_id,task_id):
    def execute():
        if not operations.enabled():raise CommandFailure('NOT_FOUND',404)
        if not request.content_type.startswith('multipart/form-data'):
            raise InputError('MULTIPART_REQUIRED',415)
        if set(request.POST) or set(request.FILES)!={'file'}:
            raise InputError('SINGLE_FILE_REQUIRED',422)
        file=request.FILES['file']
        if file.size>operations.MAX_BYTES:raise InputError('QUARANTINE_FILE_TOO_LARGE',413)
        # Browser MIME is only a filter, never an antivirus decision.
        if file.content_type!='application/pdf':
            raise InputError('PDF_ONLY',415)
        key,version=headers(request,case_id)
        return operations.submit(actor=request.user,case_id=case_id,
            task_id=task_id,raw=file.read(operations.MAX_BYTES+1),
            declared_type='application/pdf',key=key,expected_version=version)
    return command(execute)

@require_GET
def status(request,case_id,task_id):
    try:
        member,case,task=scoped(request,case_id,task_id)
        uploads=[]
        for upload in QuarantinedDocument.objects.filter(task=task).order_by('uploaded_at'):
            attempts=[{'number':a.attempt,'outcome':a.outcome,'scanned_at':a.scanned_at.isoformat()}
                for a in upload.scan_attempts.order_by('attempt')]
            uploads.append({'id':str(upload.pk),'byte_length':upload.byte_length,
                'sha256':upload.content_sha256,'scan_attempts':attempts,
                'reviewable':False,'task_completion':False})
        response=JsonResponse({'synthetic_fixture_path_unchanged':True,
            'quarantine_isolation':True,'release_supported':False,
            'records':uploads})
        response['Cache-Control']='private, no-store'
        return response
    except (PermissionDenied,CommandFailure):return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)
