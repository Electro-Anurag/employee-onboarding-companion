"""Role-owned scheduling/rescheduling and attendance, never generic completion."""
import hashlib
import json
import uuid
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.audit.services import append_event
from backend.onboarding.commands import _task_command,_receipt
from backend.onboarding.models import TaskCompletion
from backend.onboarding.services import CommandFailure,set_command_timeouts
from backend.onboarding.state_machine import recompute,case_progress
from backend.activities.models import ActivityOccurrence,ActivityAttendance

KINDS=('ACTIVITY','INTRODUCTION','CHECK_IN')
def _eligible(task,member):
    if (task.kind not in KINDS or task.owner_role!=member.role
        or member.role not in (Membership.HR,Membership.MANAGER)):
        raise CommandFailure('WRONG_ACTIVITY_TASK_KIND',422)

def _validate_slot(task,start,end,medium,reference,now):
    if (not isinstance(start,__import__('datetime').datetime)
        or not isinstance(end,__import__('datetime').datetime)
        or timezone.is_naive(start) or timezone.is_naive(end)
        or type(reference) is not str or not 4<=len(reference.strip())<=160
        or medium not in ('VIDEO','IN_PERSON')
        or start < now+timedelta(minutes=1) or end<=start
        or end-start>timedelta(hours=4)
        or start<task.available_at or end>task.due_at):
        raise CommandFailure('INVALID_ACTIVITY_SLOT',422)
    return reference.strip()

def schedule(*,actor,case_id,task_id,start,end,medium,reference,reason,key,expected_version):
    if not isinstance(reason,str) or not 8<=len(reason.strip())<=300:
        raise CommandFailure('ACTIVITY_REASON_REQUIRED',422)
    payload={'task_id':str(task_id),'start':start.isoformat() if hasattr(start,'isoformat') else str(start),
             'end':end.isoformat() if hasattr(end,'isoformat') else str(end),
             'medium':medium,'reference':reference,'reason':reason.strip()}
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
            'm4-activity-schedule',key,payload,expected_version)
        if prior is not None:return prior.response,prior.status_code
        _eligible(task,member)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state not in ('READY','IN_PROGRESS'):
            raise CommandFailure('TASK_NOT_READY',409)
        now=timezone.now()
        reference=_validate_slot(task,start,end,medium,reference,now)
        current=ActivityOccurrence.objects.filter(task=task).order_by('-revision').first()
        if current:
            attended=ActivityAttendance.objects.filter(occurrence=current).values_list('outcome',flat=True).first()
            if attended=='ATTENDED':
                raise CommandFailure('ACTIVITY_ALREADY_ATTENDED',409)
        else:
            if task.execution_state!='READY':
                raise CommandFailure('TASK_NOT_READY',409)
        rev=current.revision+1 if current else 1
        if rev>20:raise CommandFailure('ACTIVITY_RESCHEDULE_LIMIT',409)
        occurrence=ActivityOccurrence.objects.create(task=task,revision=rev,
            begins_at=start,ends_at=end,medium=medium,meeting_reference=reference,
            reason=reason.strip(),scheduled_by=actor)
        if task.work_started_at is None:
            task.work_started_at=now
            task.execution_state='IN_PROGRESS'
            task.version+=1
            task.save(update_fields=['work_started_at','execution_state','version'])
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
            event_type='ACTIVITY_SCHEDULED' if rev==1 else 'ACTIVITY_RESCHEDULED',
            entity_id=task.pk,changes={'revision':rev,'start':start.isoformat(),
             'end':end.isoformat(),'medium':medium,'replaced_occurrence_id':str(current.pk) if current else None,
             'case_version':case.version})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
            'result':{'task_id':str(task.pk),'occurrence_id':str(occurrence.pk),
                'revision':rev,'task_completion':'IN_PROGRESS'},
            'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m4-activity-schedule',key,digest,case,response,201)
    return response,201

def record_attendance(*,actor,case_id,task_id,occurrence_id,outcome,note,key,expected_version):
    if outcome not in ('ATTENDED','MISSED') or not isinstance(note,str) or not 8<=len(note.strip())<=500:
        raise CommandFailure('INVALID_ACTIVITY_ATTENDANCE',422)
    payload={'task_id':str(task_id),'occurrence_id':str(occurrence_id),
             'outcome':outcome,'note':note.strip()}
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
            'm4-activity-attendance',key,payload,expected_version)
        if prior is not None:return prior.response,prior.status_code
        _eligible(task,member)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state!='IN_PROGRESS':
            raise CommandFailure('TASK_NOT_IN_PROGRESS',409)
        occurrence=ActivityOccurrence.objects.filter(task=task).order_by('-revision').first()
        if occurrence is None or occurrence.pk!=occurrence_id:
            raise CommandFailure('CURRENT_ACTIVITY_OCCURRENCE_REQUIRED',409)
        if ActivityAttendance.objects.filter(occurrence=occurrence).exists():
            raise CommandFailure('ATTENDANCE_ALREADY_RECORDED',409)
        if timezone.now()<occurrence.ends_at:
            raise CommandFailure('FUTURE_ATTENDANCE_FORBIDDEN',409)
        proof=hashlib.sha256(json.dumps({'occurrence_id':str(occurrence.pk),
            'outcome':outcome,'organizer':str(actor.pk),'note':note.strip()},
            sort_keys=True,separators=(',',':')).encode()).hexdigest()
        attended=ActivityAttendance.objects.create(occurrence=occurrence,recorded_by=actor,
            outcome=outcome,note=note.strip())
        effects=[]
        if outcome=='ATTENDED':
            TaskCompletion.objects.create(task=task,activity_attendance=attended,
                evidence_type='ACTIVITY_ATTENDANCE',completed_by=actor,evidence_hash=proof)
            task.execution_state='COMPLETED'
            task.completed_at=timezone.now()
            task.version+=1
            task.save(update_fields=['execution_state','completed_at','version'])
            effects=recompute(case)
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
             event_type='ACTIVITY_ATTENDANCE_RECORDED',entity_id=task.pk,
             changes={'occurrence_id':str(occurrence.pk),'revision':occurrence.revision,
                      'outcome':outcome,'case_version':case.version})
        events=[str(event[0])]
        if outcome=='ATTENDED':
            done=append_event(stream_key=f'case:{case.pk}',actor=actor,
                event_type='TASK_COMPLETED',entity_id=task.pk,
                changes={'kind':task.kind,'evidence_hash':proof,'case_version':case.version})
            events.append(str(done[0]))
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
            'case_version':case.version,'result':{'task_id':str(task.pk),
                'attendance_id':str(attended.pk),'outcome':outcome,
                'task_completion':'COMPLETED' if outcome=='ATTENDED' else 'IN_PROGRESS',
                'progress':case_progress(case)},
            'affected_task_ids':[str(task.pk)]+[x['task_id'] for x in effects],
            'event_ids':events}
        _receipt(actor,'m4-activity-attendance',key,digest,case,response,201)
    return response,201
