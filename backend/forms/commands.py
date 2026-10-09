"""M3 case-locked typed submissions, independent HR review and durable receipts."""
import hashlib
import json
import re
import uuid
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.onboarding.commands import _task_command,_command_case,_receipt
from backend.onboarding.models import Task
from backend.onboarding.services import CommandFailure,set_command_timeouts
from backend.onboarding.state_machine import recompute
from backend.audit.services import append_event
from backend.forms.models import FormSubmission,FormReview

FIELD=re.compile(r'^[a-z][a-z0-9_]{1,63}$')
# Explicit compatibility for already-published synthetic M2 default templates.
LEGACY_SYNTHETIC={'personal_details':['preferred_name','contact_email']}

def normalize_answers(task,answers):
    schema=task.evidence_spec.get('fields') if isinstance(task.evidence_spec,dict) else None
    if schema is None and task.key in LEGACY_SYNTHETIC:
        schema=LEGACY_SYNTHETIC[task.key]
    if (not isinstance(schema,list) or not 1<=len(schema)<=12
            or any(not isinstance(k,str) or not FIELD.fullmatch(k) for k in schema)
            or len(set(schema))!=len(schema)):
        raise CommandFailure('FORM_SCHEMA_NOT_CONFIGURED',422)
    if (not isinstance(answers,dict) or set(answers)!=set(schema)
            or any(not isinstance(v,str) or not 1<=len(v.strip())<=200 for v in answers.values())):
        raise CommandFailure('INVALID_FORM_ANSWERS',422)
    result={k:answers[k].strip() for k in schema}
    if len(json.dumps(result,ensure_ascii=False).encode())>4096:
        raise CommandFailure('FORM_TOO_LARGE',413)
    return result

def submit(*,actor,case_id,task_id,answers,key,expected_version):
    if not isinstance(answers,dict):
        raise CommandFailure('INVALID_FORM_ANSWERS',422)
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
            'm3-form-submit',key,{'task_id':str(task_id),'answers':answers},expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.EMPLOYEE or task.kind!='FORM':
            raise CommandFailure('WRONG_EVIDENCE_KIND',422)
        normalized=normalize_answers(task,answers)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state not in ('READY','IN_PROGRESS'):
            raise CommandFailure('TASK_NOT_READY',409)
        last=FormSubmission.objects.filter(task=task).order_by('-revision').first()
        if last is not None:
            prior_decision=FormReview.objects.filter(submission=last).values_list('decision',flat=True).first()
            if prior_decision!='CHANGES_REQUESTED':
                raise CommandFailure('FORM_REVIEW_PENDING_OR_ACCEPTED',409)
        revision=last.revision+1 if last else 1
        proof=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        record=FormSubmission.objects.create(task=task,revision=revision,answers=normalized,
                                             content_hash=proof,submitted_by=actor)
        if task.work_started_at is None:
            task.work_started_at=timezone.now()
            task.execution_state='IN_PROGRESS'
            task.version+=1
            task.save(update_fields=['work_started_at','execution_state','version'])
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='FORM_SUBMITTED',
            entity_id=task.pk,changes={'revision':revision,'hash':proof,'case_version':case.version})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
                  'result':{'task_id':str(task.pk),'submission_id':str(record.pk),
                            'revision':revision,'review_state':'PENDING_HR_REVIEW',
                            'task_completion':'NOT_YET_SUPPORTED'},
                  'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m3-form-submit',key,digest,case,response,201)
    return response,201

def review(*,actor,case_id,task_id,submission_id,decision,note,key,expected_version):
    if (decision not in ('ACCEPTED','CHANGES_REQUESTED') or not isinstance(note,str)
            or len(note.strip())>500 or (decision=='CHANGES_REQUESTED' and not note.strip())):
        raise CommandFailure('INVALID_FORM_REVIEW',422)
    note=note.strip()
    payload={'task_id':str(task_id),'submission_id':str(submission_id),'decision':decision,'note':note}
    with transaction.atomic():
        set_command_timeouts()
        case,member,prior,digest=_command_case(actor,case_id,'m3-form-review',
            key,payload,expected_version,require_hr=True)
        if prior is not None:return prior.response,prior.status_code
        task=Task.objects.select_for_update().filter(pk=task_id,case=case,kind='FORM').first()
        if task is None:raise CommandFailure('NOT_FOUND',404)
        record=FormSubmission.objects.select_for_update().filter(pk=submission_id,task=task).first()
        if record is None or FormSubmission.objects.filter(task=task,revision__gt=record.revision).exists():
            raise CommandFailure('NOT_FOUND',404)
        if FormReview.objects.filter(submission=record).exists():
            raise CommandFailure('FORM_ALREADY_REVIEWED',409)
        evidence=FormReview.objects.create(submission=record,reviewed_by=actor,
                                           decision=decision,note=note)
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='FORM_REVIEWED',
            entity_id=task.pk,changes={'revision':record.revision,'decision':decision,
                                       'case_version':case.version})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
                  'result':{'task_id':str(task.pk),'review_id':str(evidence.pk),'revision':record.revision,
                            'decision':decision,'task_completion':'NOT_YET_SUPPORTED'},
                  'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m3-form-review',key,digest,case,response,201)
    return response,201
