"""Bounded synthetic document intake and independent HR evidence review.

Arbitrary user uploads must NEVER be marked clean by this implementation.
Production file storage, scanners, and generalized formats remain unimplemented.
"""
import hashlib
import uuid
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.onboarding.commands import _task_command,_command_case,_receipt
from backend.onboarding.models import Task,TaskCompletion
from backend.onboarding.services import CommandFailure,set_command_timeouts
from backend.onboarding.state_machine import recompute,case_progress
from backend.audit.services import append_event
from backend.documents.fixtures import validate_document,PROFILE,sample_for
from backend.documents.models import DocumentRevision,DocumentReview

def upload(*,actor,case_id,task_id,raw,key,expected_version):
    if not isinstance(raw,bytes) or len(raw)>4096:
        raise CommandFailure('DOCUMENT_UPLOAD_LIMIT',413)
    digest=hashlib.sha256(raw).hexdigest()
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,request_hash=_task_command(actor,case_id,task_id,
            'm3-document-upload',key,
            {'task_id':str(task_id),'sha256':digest,'byte_length':len(raw)},expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.EMPLOYEE or task.kind!='DOCUMENT':
            raise CommandFailure('WRONG_DOCUMENT_TASK',422)
        validate_document(task,raw)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state not in ('READY','IN_PROGRESS'):
            raise CommandFailure('TASK_NOT_READY',409)
        last=DocumentRevision.objects.filter(task=task).order_by('-revision').first()
        if last:
            outcome=DocumentReview.objects.filter(revision=last).values_list('decision',flat=True).first()
            if outcome not in ('REJECTED','NEEDS_CLARIFICATION'):
                raise CommandFailure('DOCUMENT_REVIEW_PENDING_OR_ACCEPTED',409)
        number=last.revision+1 if last else 1
        row=DocumentRevision.objects.create(task=task,revision=number,uploaded_by=actor,
            content=raw,content_sha256=digest,byte_length=len(raw),
            filename='synthetic_'+task.key+'.txt',content_type='text/plain',
            scan_status='VALIDATED_SYNTHETIC',scan_profile=PROFILE)
        if task.work_started_at is None:
            task.work_started_at=timezone.now()
            task.execution_state='IN_PROGRESS'
            task.version+=1
            task.save(update_fields=['work_started_at','execution_state','version'])
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
           event_type='SYNTHETIC_DOCUMENT_SUBMITTED',entity_id=task.pk,
           changes={'revision':number,'content_sha256':digest,'profile':PROFILE,
                    'case_version':case.version})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
            'result':{'task_id':str(task.pk),'document_revision_id':str(row.pk),
                'revision':number,'review_state':'PENDING_HR_REVIEW',
                'security_state':'VALIDATED_SYNTHETIC','malware_scanned':False,
                'task_completion':'PENDING_HR_REVIEW'},
            'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m3-document-upload',key,request_hash,case,response,201)
    return response,201

def review(*,actor,case_id,task_id,revision_id,decision,note,key,expected_version):
    if (decision not in ('ACCEPTED','REJECTED','NEEDS_CLARIFICATION') or not isinstance(note,str)
        or not 1<=len(note.strip())<=500):
        raise CommandFailure('DOCUMENT_REVIEW_NOTE_REQUIRED',422)
    note=note.strip()
    payload={'task_id':str(task_id),'revision_id':str(revision_id),
             'decision':decision,'note':note}
    with transaction.atomic():
        set_command_timeouts()
        case,member,prior,request_hash=_command_case(actor,case_id,
            'm3-document-review',key,payload,expected_version,require_hr=True)
        if prior is not None:return prior.response,prior.status_code
        task=Task.objects.select_for_update().filter(pk=task_id,case=case,kind='DOCUMENT').first()
        if task is None:raise CommandFailure('NOT_FOUND',404)
        row=DocumentRevision.objects.select_for_update().filter(pk=revision_id,task=task).first()
        if row is None or DocumentRevision.objects.filter(task=task,revision__gt=row.revision).exists():
            raise CommandFailure('NOT_FOUND',404)
        if DocumentReview.objects.filter(revision=row).exists():
            raise CommandFailure('DOCUMENT_ALREADY_REVIEWED',409)
        if task.execution_state!='IN_PROGRESS':
            raise CommandFailure('TASK_NOT_IN_PROGRESS',409)
        # Revalidate the exact bytes at HR acceptance, not merely a client-provided
        # scan-state label. Synthetic fixture check is NOT general malware scanning.
        if (row.scan_status!='VALIDATED_SYNTHETIC' or row.scan_profile!=PROFILE
                or validate_document(task,bytes(row.content))!=row.content_sha256):
            raise CommandFailure('DOCUMENT_SECURITY_NOT_VERIFIED',409)
        entry=DocumentReview.objects.create(revision=row,reviewed_by=actor,decision=decision,note=note)
        affected=[str(task.pk)]
        if decision=='ACCEPTED':
            TaskCompletion.objects.create(task=task,document_review=entry,
                evidence_type='DOCUMENT',completed_by=actor,evidence_hash=row.content_sha256)
            task.execution_state='COMPLETED'
            task.completed_at=timezone.now()
            task.version+=1
            task.save(update_fields=['execution_state','completed_at','version'])
            affected += [d['task_id'] for d in recompute(case)]
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
            event_type='SYNTHETIC_DOCUMENT_REVIEWED',entity_id=task.pk,
            changes={'revision':row.revision,'decision':decision,
                     'content_sha256':row.content_sha256,'case_version':case.version,
                     'accepted_as_synthetic':decision=='ACCEPTED'})
        ids=[str(event[0])]
        if decision=='ACCEPTED':
            completed=append_event(stream_key=f'case:{case.pk}',actor=actor,
               event_type='TASK_COMPLETED',entity_id=task.pk,
               changes={'kind':'DOCUMENT','security_profile':PROFILE,'malware_scanned':False,
                        'case_version':case.version,'content_sha256':row.content_sha256})
            ids.append(str(completed[0]))
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
            'case_version':case.version,'result':{
                'task_id':str(task.pk),'document_review_id':str(entry.pk),
                'decision':decision,'revision':row.revision,
                'task_completion':'COMPLETED' if decision=='ACCEPTED' else 'PENDING_CORRECTION',
                'malware_scanned':False,
                'progress':case_progress(case)},
            'affected_task_ids':affected,'event_ids':ids}
        _receipt(actor,'m3-document-review',key,request_hash,case,response,201)
    return response,201
