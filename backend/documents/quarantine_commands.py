"""Bounded local quarantine: no accepted document revision, no task completion."""
import hashlib
import hmac
import uuid
from django.conf import settings
from django.db import transaction
from backend.accounts.models import Membership
from backend.onboarding.commands import _task_command,_receipt
from backend.onboarding.services import CommandFailure,set_command_timeouts
from backend.audit.services import append_event
from backend.documents.quarantine_models import QuarantinedDocument,QuarantineScanAttempt
from backend.documents.scanner import clamav_scan,ScannerUnavailable

MAX_BYTES=262144

def enabled():
    # Both explicit opt-in and a concrete scanner endpoint are needed.
    return (getattr(settings,'M3_QUARANTINE_INTAKE_ENABLED',False)
        and bool(getattr(settings,'M3_CLAMAV_HOST','')))

def submit(*,actor,case_id,task_id,raw,declared_type,key,expected_version):
    if not enabled():
        raise CommandFailure('QUARANTINE_INTAKE_DISABLED',404)
    if (not isinstance(raw,bytes) or not 16<=len(raw)<=MAX_BYTES
        or declared_type!='application/pdf' or not raw.startswith(b'%PDF-')):
        raise CommandFailure('INVALID_QUARANTINED_UPLOAD',422)
    digest=hashlib.sha256(raw).hexdigest()
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,request_hash=_task_command(
            actor,case_id,task_id,'m3-quarantine-intake',key,
            {'task_id':str(task_id),'sha256':digest,'byte_length':len(raw),
             'declared_type':declared_type},expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.EMPLOYEE or task.kind!='DOCUMENT':
            raise CommandFailure('NOT_FOUND',404)
        if task.execution_state not in ('READY','IN_PROGRESS'):
            raise CommandFailure('TASK_NOT_READY',409)
        if QuarantinedDocument.objects.filter(task=task).count()>=3:
            raise CommandFailure('QUARANTINE_UPLOAD_LIMIT',409)
        upload=QuarantinedDocument.objects.create(task=task,uploaded_by=actor,
            quarantined_bytes=raw,content_sha256=digest,
            byte_length=len(raw),declared_type=declared_type)
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
            event_type='QUARANTINE_UPLOAD_RECEIVED',entity_id=task.pk,
            changes={'quarantine_id':str(upload.pk),'sha256':digest,
                'byte_length':len(raw),'case_version':case.version,
                'reviewable':False,'task_completion':False})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
            'case_version':case.version,'result':{'task_id':str(task.pk),
                'quarantine_id':str(upload.pk),'state':'QUARANTINED',
                'malware_scanned':False,'reviewable':False,
                'task_completion':'NOT_COMPLETED'},
            'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m3-quarantine-intake',key,request_hash,case,response,201)
    return response,201

def scan_upload(upload_id,scanner=clamav_scan):
    """Durably scan a quarantine record. Local worker/management command only.

    The lock prevents concurrent attempt duplication. Socket is bounded to
    two seconds and no HR acceptance or download path is created.
    """
    if not enabled():
        raise CommandFailure('QUARANTINE_INTAKE_DISABLED',404)
    with transaction.atomic():
        set_command_timeouts()
        upload=QuarantinedDocument.objects.select_for_update().filter(pk=upload_id).first()
        if upload is None:raise CommandFailure('NOT_FOUND',404)
        last=QuarantineScanAttempt.objects.filter(upload=upload).order_by('-attempt').first()
        if last and last.outcome in ('CLEAN','MALWARE'):
            return {'upload_id':str(upload.pk),'attempt':last.attempt,
                'outcome':last.outcome,'reviewable':False}
        number=last.attempt+1 if last else 1
        if number>3:raise CommandFailure('SCAN_ATTEMPT_LIMIT',409)
        raw=bytes(upload.quarantined_bytes)
        if (len(raw)!=upload.byte_length
                or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(),upload.content_sha256)):
            result,detail='ERROR','QUARANTINE_INTEGRITY_MISMATCH'
        else:
            try:
                result,detail=scanner(raw)
                if result not in ('CLEAN','MALWARE'):
                    result,detail='ERROR','INVALID_SCANNER_RESULT'
            except ScannerUnavailable as exc:
                result,detail='ERROR',str(exc)[:80]
            except Exception:
                # Do not record exception details or document bytes.
                result,detail='ERROR','SCANNER_EXCEPTION'
        QuarantineScanAttempt.objects.create(upload=upload,attempt=number,
            outcome=result,detail=detail[:80],engine='CLAMAV_INSTREAM')
        return {'upload_id':str(upload.pk),'attempt':number,
            'outcome':result,'reviewable':False}
