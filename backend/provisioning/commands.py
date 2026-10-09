"""IT request + simulated fulfillment: real persistence, no fabricated external outcome."""
import hashlib
import uuid
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.onboarding.commands import _task_command,_receipt
from backend.onboarding.services import CommandFailure,set_command_timeouts
from backend.onboarding.state_machine import recompute
from backend.audit.services import append_event
from backend.provisioning.models import ITOperation

def request_it(*,actor,case_id,task_id,key,expected_version):
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
            'm4-it-request',key,{'task_id':str(task_id)},expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.IT or task.kind not in ('ACCESS','EQUIPMENT'):
            raise CommandFailure('WRONG_IT_TASK_KIND',422)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state!='READY':
            raise CommandFailure('TASK_NOT_READY',409)
        if ITOperation.objects.filter(task=task).exists():
            raise CommandFailure('IT_OPERATION_EXISTS',409)
        operation=ITOperation.objects.create(task=task,requested_by=actor)
        task.work_started_at=timezone.now()
        task.execution_state='IN_PROGRESS'
        task.version+=1
        task.save(update_fields=['work_started_at','execution_state','version'])
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='IT_REQUESTED',
            entity_id=task.pk,changes={'operation_id':str(operation.pk),'case_version':case.version,
                                       'provider':'SYNTHETIC_ONLY'})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
                  'result':{'task_id':str(task.pk),'operation_id':str(operation.pk),
                            'state':'REQUESTED','provider':'SYNTHETIC_ONLY',
                            'task_completion':'NOT_YET_SUPPORTED'},
                  'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m4-it-request',key,digest,case,response,201)
    return response,201

def simulate_fulfillment(*,actor,case_id,task_id,note,key,expected_version):
    if not isinstance(note,str) or len(note.strip())>300:
        raise CommandFailure('INVALID_SIMULATION_NOTE',422)
    note=note.strip()
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
            'm4-it-simulate',key,{'task_id':str(task_id),'note':note},expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.IT or task.kind not in ('ACCESS','EQUIPMENT'):
            raise CommandFailure('WRONG_IT_TASK_KIND',422)
        operation=ITOperation.objects.select_for_update().filter(task=task).first()
        if operation is None:raise CommandFailure('IT_REQUEST_REQUIRED',409)
        if operation.status!='REQUESTED':raise CommandFailure('IT_ALREADY_SIMULATED',409)
        if task.execution_state!='IN_PROGRESS':raise CommandFailure('TASK_NOT_IN_PROGRESS',409)
        operation.status='SIMULATED_FULFILLED'
        operation.simulated_by=actor
        operation.simulated_at=timezone.now()
        operation.note=note
        operation.simulation_digest=hashlib.sha256(
            ('synthetic:'+str(operation.pk)+':'+str(task.pk)).encode()).hexdigest()
        operation.save(update_fields=['status','simulated_by','simulated_at','note','simulation_digest'])
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='IT_SIMULATED',
            entity_id=task.pk,changes={'operation_id':str(operation.pk),
                                       'simulation_digest':operation.simulation_digest,
                                       'case_version':case.version,'provider':'SYNTHETIC_ONLY'})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
                  'result':{'task_id':str(task.pk),'operation_id':str(operation.pk),
                            'state':'SIMULATED_FULFILLED','provider':'SYNTHETIC_ONLY',
                            'task_completion':'NOT_YET_SUPPORTED'},
                  'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m4-it-simulate',key,digest,case,response,200)
    return response,200
