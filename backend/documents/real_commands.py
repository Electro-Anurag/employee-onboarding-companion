"""End-to-end version-pinned document saga, with no false trust shortcuts.

Use only synthetic/anonymized PDFs in the demo. Genuine private employee data
requires approved hosting, retention and an independently verified deployment.
"""
import hashlib
import re
import uuid
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.audit.services import append_event
from backend.onboarding.commands import _task_command,_command_case,_receipt
from backend.onboarding.models import Task,TaskCompletion
from backend.onboarding.services import CommandFailure,set_command_timeouts,get_authorized_case
from backend.onboarding.state_machine import recompute,case_progress
from backend.documents.real_models import (SecureUpload,StoredQuarantineObject,
    SecureScanAttempt,SecureCleanObject,SecureHRReview)
from backend.documents import storage
from backend.documents.pdf_validation import validate_pdf
from backend.documents.scanner import clamav_scan,ScannerUnavailable,clamav_signature_provenance

SHA=re.compile(r'^[0-9a-f]{64}$')
FILENAME=re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9 _.()-]{0,115}\.pdf$')

def _enabled():
    if not storage.configured():raise CommandFailure('REAL_DOCUMENT_STORAGE_DISABLED',404)

def _latest_upload(task):
    return SecureUpload.objects.filter(task=task).order_by('-revision').first()

def _status(upload):
    if not upload:return 'NOT_SUBMITTED'
    if not StoredQuarantineObject.objects.filter(upload=upload).exists():return 'AWAITING_CONTENT'
    clean=SecureCleanObject.objects.filter(upload=upload).first()
    if clean:
        review=SecureHRReview.objects.filter(clean=clean).first()
        return review.decision if review else 'AWAITING_HR_REVIEW'
    last=SecureScanAttempt.objects.filter(upload=upload).order_by('-number').first()
    if last:
        return {'MALWARE':'REJECTED_SECURITY','ERROR':'SCAN_FAILED','CLEAN':'PROMOTION_PENDING'}[last.outcome]
    return 'QUARANTINED'

def prepare(*,actor,case_id,task_id,sha256,size,filename,key,expected_version):
    _enabled()
    if (not isinstance(sha256,str) or not SHA.fullmatch(sha256)
        or type(size) is not int or not 40<=size<=storage.MAX_FILE
        or not isinstance(filename,str) or not FILENAME.fullmatch(filename)):
        raise CommandFailure('INVALID_DOCUMENT_INTENT',422)
    # Fail before modifying the case if storage is absent/nonversioned.
    storage.buckets(storage.client())
    payload={'task_id':str(task_id),'sha256':sha256,'size':size,'filename':filename}
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(
            actor,case_id,task_id,'m3-secure-prepare',key,payload,expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.EMPLOYEE or task.kind!='DOCUMENT':
            raise CommandFailure('NOT_FOUND',404)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state not in ('READY','IN_PROGRESS'):
            raise CommandFailure('TASK_NOT_READY',409)
        last=_latest_upload(task)
        if last and _status(last) not in (
            'REJECTED','NEEDS_CLARIFICATION','REJECTED_SECURITY'):
            raise CommandFailure('DOCUMENT_REVISION_NOT_REPLACEABLE',409)
        # Legacy synthetic accepted revisions also forbid replacement.
        if task.execution_state=='COMPLETED':
            raise CommandFailure('TASK_ALREADY_COMPLETED',409)
        number=last.revision+1 if last else 1
        if number>20:raise CommandFailure('DOCUMENT_REVISION_LIMIT',409)
        upload_id=uuid.uuid4()
        obj_key='quarantine/'+str(case.organization_id)+'/'+str(case.pk)+'/'+str(upload_id)+'.pdf'
        obj=SecureUpload.objects.create(id=upload_id,task=task,revision=number,
            employee=actor,sha256=sha256,byte_length=size,filename=filename,
            object_key=obj_key)
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
            event_type='DOCUMENT_UPLOAD_INTENT',entity_id=task.pk,
            changes={'upload_id':str(obj.pk),'revision':number,
                'sha256':sha256,'case_version':case.version})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
            'case_version':case.version,'result':{
                'upload_id':str(obj.pk),'revision':number,'state':'AWAITING_CONTENT'},
            'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m3-secure-prepare',key,digest,case,response,201)
    return response,201

def receive(*,actor,case_id,task_id,upload_id,raw,key,expected_version):
    _enabled()
    if not isinstance(raw,bytes) or len(raw)>storage.MAX_FILE:
        raise CommandFailure('DOCUMENT_SIZE_LIMIT',413)
    # READ authorization first; never upload unauthenticated material to S3.
    member,case=get_authorized_case(actor,case_id)
    if member.role!=Membership.EMPLOYEE:
        raise CommandFailure('NOT_FOUND',404)
    upload=SecureUpload.objects.select_related('task').filter(
        pk=upload_id,task_id=task_id,task__case=case,employee=actor).first()
    if not upload:
        raise CommandFailure('NOT_FOUND',404)
    # An authorized historical receipt must be replayable even after a
    # replacement revision supersedes this upload; NEW writes are checked
    # against the latest revision below, after the receipt preflight.
    if len(raw)!=upload.byte_length or hashlib.sha256(raw).hexdigest()!=upload.sha256:
        raise CommandFailure('UPLOAD_CONTENT_MISMATCH',422)
    validate_pdf(raw)
    # A same-key replay after an uncertain COMMIT (or later HR acceptance)
    # must return its durable receipt BEFORE the 'already received' guard.
    # The short preflight transaction holds no locks during S3 network I/O.
    payload={'upload_id':str(upload_id),'sha256':upload.sha256}
    with transaction.atomic():
        set_command_timeouts()
        _,member,_,prior,_=_task_command(actor,case_id,task_id,
            'm3-secure-receive',key,payload,expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.EMPLOYEE:
            raise CommandFailure('NOT_FOUND',404)
    if _latest_upload(upload.task).pk!=upload.pk:
        raise CommandFailure('UPLOAD_NOT_CURRENT',409)
    if upload.task.execution_state not in ('READY','IN_PROGRESS'):
        raise CommandFailure('TASK_NOT_READY',409)
    # Write outside the DB transaction: no socket or S3 I/O while holding case
    # or identity row locks. An interrupted storage write stays undisclosed.
    existing=StoredQuarantineObject.objects.filter(upload=upload).first()
    if existing:raise CommandFailure('CONTENT_ALREADY_RECEIVED',409)
    version=storage.put_quarantine(upload,raw)
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
            'm3-secure-receive',key,{'upload_id':str(upload_id),
                'sha256':upload.sha256},expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.EMPLOYEE or task.kind!='DOCUMENT':
            raise CommandFailure('NOT_FOUND',404)
        if _latest_upload(task).pk!=upload_id or StoredQuarantineObject.objects.filter(upload=upload).exists():
            raise CommandFailure('UPLOAD_NOT_CURRENT',409)
        obj=StoredQuarantineObject.objects.create(upload=upload,version_id=version)
        if task.work_started_at is None:
            task.work_started_at=timezone.now()
            task.execution_state='IN_PROGRESS'
            task.version+=1
            task.save(update_fields=['work_started_at','execution_state','version'])
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
            event_type='DOCUMENT_QUARANTINED',entity_id=task.pk,
            changes={'upload_id':str(upload.pk),'quarantine_version_id':version,
                     'case_version':case.version})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
            'case_version':case.version,'result':{
                'upload_id':str(upload.pk),'state':'QUARANTINED','reviewable':False},
            'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m3-secure-receive',key,digest,case,response,201)
        # Durable PostgreSQL-backed job enqueued within case transaction.
        from backend.jobs.tasks import scan_secure_document
        scan_secure_document.defer(upload_id=str(upload.id))
    return response,201

def scan_one(upload_id,scanner=None):
    """Content-worker operation: only verified bytes of an immutable S3 version.

    Writes outcomes idempotently and allows at most three transient retries.
    """
    _enabled()
    with transaction.atomic():
        set_command_timeouts()
        upload=SecureUpload.objects.select_for_update().filter(pk=upload_id).first()
        if not upload:raise CommandFailure('NOT_FOUND',404)
        stored=StoredQuarantineObject.objects.filter(upload=upload).first()
        if not stored:raise CommandFailure('CONTENT_NOT_STORED',409)
        previous=SecureScanAttempt.objects.filter(upload=upload).order_by('-number').first()
        if SecureCleanObject.objects.filter(upload=upload).exists():
            return {'outcome':'CLEAN','state':'AWAITING_HR_REVIEW'}
        if previous and previous.outcome=='MALWARE':
            return {'outcome':'MALWARE','state':'REJECTED_SECURITY'}
        if previous and previous.outcome=='CLEAN':
            # Reconcile a prior clean verdict after object promotion failure.
            verdict,detail='CLEAN','Prior verified clean verdict'
            number=previous.number
        else:
            number=previous.number+1 if previous else 1
            if number>3:raise CommandFailure('SCAN_RETRY_LIMIT',409)
            try:
                raw=storage.read_exact(storage.buckets(storage.client())[0],
                    upload.object_key,stored.version_id,upload.sha256)
                validate_pdf(raw)
                scanner_info='TEST_SCANNER_OVERRIDE'
                if scanner is None:
                    scanner_info=clamav_signature_provenance()
                verdict,detail=(scanner or clamav_scan)(raw)
                if verdict not in ('CLEAN','MALWARE'):
                    verdict,detail='ERROR','SCANNER_INDETERMINATE'
            except (CommandFailure,ScannerUnavailable):
                verdict,detail='ERROR','SCANNER_OR_VALIDATION_ERROR'
            except Exception:
                verdict,detail='ERROR','SCANNER_UNEXPECTED_ERROR'
            previous=SecureScanAttempt.objects.create(upload=upload,number=number,
                outcome=verdict,detail=str(detail)[:120],
                scanner_version=locals().get('scanner_info','SCANNER_UNAVAILABLE'))
        if verdict=='CLEAN':
            try:
                obj_key,version=storage.promote(upload,stored.version_id)
                SecureCleanObject.objects.create(upload=upload,scan=previous,
                    object_key=obj_key,version_id=version)
            except Exception:
                # A clean scan can be safely re-promoted using exact source version.
                return {'outcome':'CLEAN','state':'PROMOTION_PENDING'}
            return {'outcome':'CLEAN','state':'AWAITING_HR_REVIEW'}
        return {'outcome':verdict,'state':'REJECTED_SECURITY' if verdict=='MALWARE' else 'SCAN_FAILED'}

def review(*,actor,case_id,task_id,upload_id,decision,note,key,expected_version):
    _enabled()
    if (decision not in ('ACCEPTED','REJECTED','NEEDS_CLARIFICATION')
        or not isinstance(note,str) or not 1<=len(note.strip())<=500):
        raise CommandFailure('INVALID_DOCUMENT_REVIEW',422)
    payload={'upload_id':str(upload_id),'decision':decision,'note':note.strip()}
    with transaction.atomic():
        set_command_timeouts()
        case,member,prior,digest=_command_case(actor,case_id,'m3-secure-review',
            key,payload,expected_version,require_hr=True)
        if prior is not None:return prior.response,prior.status_code
        task=Task.objects.select_for_update().filter(pk=task_id,case=case,kind='DOCUMENT').first()
        if not task:raise CommandFailure('NOT_FOUND',404)
        upload=SecureUpload.objects.filter(pk=upload_id,task=task).first()
        if not upload or _latest_upload(task).pk!=upload.id:raise CommandFailure('NOT_FOUND',404)
        clean=SecureCleanObject.objects.filter(upload=upload,scan__outcome='CLEAN').first()
        if not clean:raise CommandFailure('CLEAN_SCAN_REQUIRED',409)
        if SecureHRReview.objects.filter(clean=clean).exists():
            raise CommandFailure('ALREADY_REVIEWED',409)
        if task.execution_state!='IN_PROGRESS':
            raise CommandFailure('TASK_NOT_IN_PROGRESS',409)
        row=SecureHRReview.objects.create(clean=clean,reviewer=actor,
            decision=decision,note=note.strip())
        affected=[str(task.pk)]
        if decision=='ACCEPTED':
            TaskCompletion.objects.create(task=task,evidence_type='SECURE_DOCUMENT',
                secure_review=row,completed_by=actor,evidence_hash=upload.sha256)
            task.execution_state='COMPLETED'
            task.completed_at=timezone.now()
            task.version+=1
            task.save(update_fields=['execution_state','completed_at','version'])
            affected += [t['task_id'] for t in recompute(case)]
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
            event_type='DOCUMENT_SECURE_REVIEWED',entity_id=task.pk,
            changes={'upload_id':str(upload.pk),'decision':decision,
                     'clean_version_id':clean.version_id,'case_version':case.version})
        events=[str(event[0])]
        if decision=='ACCEPTED':
            completion=append_event(stream_key=f'case:{case.pk}',actor=actor,
                event_type='TASK_COMPLETED',entity_id=task.pk,
                changes={'kind':'DOCUMENT','evidence_type':'SECURE_DOCUMENT',
                         'case_version':case.version})
            events.append(str(completion[0]))
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
            'case_version':case.version,'result':{'upload_id':str(upload.pk),
                'decision':decision,'task_completion':'COMPLETED' if decision=='ACCEPTED'
                    else 'PENDING_CORRECTION','progress':case_progress(case)},
            'affected_task_ids':affected,'event_ids':events}
        _receipt(actor,'m3-secure-review',key,digest,case,response,201)
    return response,201
