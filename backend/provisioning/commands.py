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
from backend.provisioning.models import ITOperation,ITConfirmation,EquipmentReceipt,ITSimulationFailure
from backend.onboarding.models import Task,TaskDependency,TaskCompletion
from backend.onboarding.state_machine import case_progress

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

def confirm_it(*,actor,case_id,task_id,note,key,expected_version):
    """Human IT signoff is required AFTER a persisted synthetic result."""
    if not isinstance(note,str) or not 8<=len(note.strip())<=300:
        raise CommandFailure('IT_CONFIRMATION_NOTE_REQUIRED',422)
    note=note.strip()
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
            'm4-it-confirm',key,{'task_id':str(task_id),'note':note},expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.IT or task.kind not in ('ACCESS','EQUIPMENT'):
            raise CommandFailure('WRONG_IT_TASK_KIND',422)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state!='IN_PROGRESS':
            raise CommandFailure('TASK_NOT_IN_PROGRESS',409)
        op=ITOperation.objects.select_for_update().filter(task=task).first()
        if op is None or op.status!='SIMULATED_FULFILLED' or not op.simulation_digest:
            raise CommandFailure('SIMULATED_RESULT_REQUIRED',409)
        if ITConfirmation.objects.filter(operation=op).exists():
            raise CommandFailure('IT_ALREADY_CONFIRMED',409)
        record=ITConfirmation.objects.create(operation=op,confirmed_by=actor,
            simulation_digest=op.simulation_digest,note=note)
        TaskCompletion.objects.create(task=task,manager_attestation=None,form_review=None,
            it_confirmation=record,equipment_receipt=None,evidence_type='IT_CONFIRMATION',
            completed_by=actor,evidence_hash=record.simulation_digest)
        task.execution_state='COMPLETED'
        task.completed_at=timezone.now()
        task.version+=1
        task.save(update_fields=['execution_state','completed_at','version'])
        effects=recompute(case)
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='TASK_COMPLETED',
            entity_id=task.pk,changes={'kind':task.kind,'provider':'SYNTHETIC_ONLY',
                'human_it_confirmation_id':str(record.pk),'case_version':case.version,
                'unlocked':len(effects)})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
            'case_version':case.version,'result':{
                'task_id':str(task.pk),'state':'COMPLETED',
                'confirmation_id':str(record.pk),'provider':'SYNTHETIC_ONLY',
                'external_fulfillment_verified':False,'progress':case_progress(case)},
            'affected_task_ids':[str(task.pk)]+[x['task_id'] for x in effects],
            'event_ids':[str(event[0])]}
        _receipt(actor,'m4-it-confirm',key,digest,case,response,200)
    return response,200

def receive_equipment(*,actor,case_id,task_id,it_confirmation_id,note,key,expected_version):
    """Employee acknowledges precisely the confirmed upstream EQUIPMENT task."""
    if (not isinstance(it_confirmation_id,uuid.UUID) or not isinstance(note,str)
            or not 8<=len(note.strip())<=300):
        raise CommandFailure('INVALID_EQUIPMENT_RECEIPT',422)
    note=note.strip()
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
            'm4-equipment-receipt',key,
            {'task_id':str(task_id),'it_confirmation_id':str(it_confirmation_id),
             'note':note},expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.EMPLOYEE or task.kind!='EQUIPMENT_RECEIPT':
            raise CommandFailure('WRONG_RECEIPT_TASK',422)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state!='READY':
            raise CommandFailure('TASK_NOT_READY',409)
        confirmed=ITConfirmation.objects.select_related('operation__task').filter(pk=it_confirmation_id).first()
        if confirmed is None or confirmed.operation.status!='SIMULATED_FULFILLED':
            raise CommandFailure('CONFIRMED_EQUIPMENT_REQUIRED',409)
        source=confirmed.operation.task
        if (source.case_id!=case.pk or source.kind!='EQUIPMENT'
                or source.execution_state!='COMPLETED'
                or not TaskCompletion.objects.filter(task=source,evidence_type='IT_CONFIRMATION',
                    it_confirmation=confirmed).exists()
                or not TaskDependency.objects.filter(case=case,
                    predecessor=source,successor=task).exists()):
            raise CommandFailure('CONFIRMED_EQUIPMENT_REQUIRED',409)
        receipt=EquipmentReceipt.objects.create(task=task,it_confirmation=confirmed,
            accepted_by=actor,note=note)
        TaskCompletion.objects.create(task=task,manager_attestation=None,form_review=None,
            it_confirmation=None,equipment_receipt=receipt,evidence_type='EQUIPMENT_RECEIPT',
            completed_by=actor,evidence_hash=confirmed.simulation_digest)
        task.execution_state='COMPLETED'
        task.completed_at=timezone.now()
        task.version+=1
        task.save(update_fields=['execution_state','completed_at','version'])
        effects=recompute(case)
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='TASK_COMPLETED',
            entity_id=task.pk,changes={'kind':'EQUIPMENT_RECEIPT','it_confirmation_id':str(confirmed.pk),
                                       'case_version':case.version,'unlocked':len(effects)})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
            'result':{'task_id':str(task.pk),'state':'COMPLETED',
                      'receipt_id':str(receipt.pk),'provider':'SYNTHETIC_ONLY',
                      'external_fulfillment_verified':False,'progress':case_progress(case)},
            'affected_task_ids':[str(task.pk)]+[x['task_id'] for x in effects],
            'event_ids':[str(event[0])]}
        _receipt(actor,'m4-equipment-receipt',key,digest,case,response,200)
    return response,200

def record_simulated_failure(*,actor,case_id,task_id,cause,note,key,expected_version):
    """Record an explicit synthetic provider failure without unlocking any task.

    Each bounded retry uses the existing operation; success remains a separate
    command followed by a separate authorized IT confirmation.
    """
    if (cause not in ('PROVIDER_UNAVAILABLE','SIMULATED_TIMEOUT','SIMULATED_REJECTION')
        or not isinstance(note,str) or not 8<=len(note.strip())<=300):
        raise CommandFailure('INVALID_SIMULATED_FAILURE',422)
    note=note.strip()
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
            'm4-it-failure',key,{'task_id':str(task_id),'cause':cause,'note':note},
            expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.IT or task.kind not in ('ACCESS','EQUIPMENT'):
            raise CommandFailure('WRONG_IT_TASK_KIND',422)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state!='IN_PROGRESS':
            raise CommandFailure('TASK_NOT_IN_PROGRESS',409)
        operation=ITOperation.objects.select_for_update().filter(task=task).first()
        if operation is None or operation.status!='REQUESTED':
            raise CommandFailure('IT_PENDING_REQUEST_REQUIRED',409)
        last=ITSimulationFailure.objects.filter(operation=operation).order_by('-sequence').first()
        sequence=last.sequence+1 if last else 1
        if sequence>5:raise CommandFailure('SIMULATED_FAILURE_LIMIT',409)
        failure=ITSimulationFailure.objects.create(operation=operation,
            sequence=sequence,reported_by=actor,cause=cause,note=note)
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
            event_type='IT_SIMULATION_FAILED',entity_id=task.pk,changes={
                'operation_id':str(operation.pk),'failure_id':str(failure.pk),
                'cause':cause,'sequence':sequence,'case_version':case.version,
                'provider':'SYNTHETIC_ONLY','task_completion':'IN_PROGRESS'})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
            'case_version':case.version,'result':{
                'task_id':str(task.pk),'operation_id':str(operation.pk),
                'failure_id':str(failure.pk),'failure_sequence':sequence,
                'state':'REQUESTED','provider':'SYNTHETIC_ONLY',
                'retry_explicitly_available':True,'task_completion':'IN_PROGRESS'},
            'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m4-it-failure',key,digest,case,response,201)
    return response,201
