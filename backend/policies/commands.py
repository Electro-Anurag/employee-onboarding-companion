"""Case-frozen policy edition acknowledgement, never a client boolean shortcut."""
import hashlib
import hmac
import uuid
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.onboarding.commands import _task_command,_receipt
from backend.onboarding.models import TaskCompletion
from backend.onboarding.services import CommandFailure,set_command_timeouts
from backend.onboarding.state_machine import recompute,case_progress
from backend.audit.services import append_event
from backend.policies.models import PolicyAcknowledgement

def validated_policy(task):
    spec=task.evidence_spec
    if not isinstance(spec,dict) or set(spec)!=set((
       'type','policy_key','policy_version','policy_text','content_sha256')):
        raise CommandFailure('POLICY_CONTENT_NOT_ASSIGNED',409)
    body=spec['policy_text']
    version=spec['policy_version']
    digest=spec['content_sha256']
    if (spec['type']!='POLICY_ACK' or spec['policy_key']!=task.key
        or not isinstance(body,str) or not 1<=len(body)<=2000
        or not isinstance(version,str) or not 1<=len(version)<=80
        or not isinstance(digest,str) or len(digest)!=64
        or not hmac.compare_digest(hashlib.sha256(body.encode()).hexdigest(),digest)):
        raise CommandFailure('INVALID_ASSIGNED_POLICY',409)
    return {'version':version,'content_sha256':digest,'text':body,
            'policy_key':spec['policy_key']}

def acknowledge(*,actor,case_id,task_id,policy_version,content_sha256,accepted,key,expected_version):
    if (not isinstance(policy_version,str) or not isinstance(content_sha256,str)
        or type(accepted) is not bool or accepted is not True):
        raise CommandFailure('EXPLICIT_POLICY_ACCEPTANCE_REQUIRED',422)
    payload={'task_id':str(task_id),'policy_version':policy_version,
             'content_sha256':content_sha256,'accepted':True}
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,req_digest=_task_command(actor,case_id,task_id,
            'm3-policy-ack',key,payload,expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.EMPLOYEE or task.kind!='POLICY_ACK':
            raise CommandFailure('WRONG_POLICY_TASK',422)
        policy=validated_policy(task)
        if (not hmac.compare_digest(policy_version,policy['version'])
            or not hmac.compare_digest(content_sha256,policy['content_sha256'])):
            raise CommandFailure('STALE_POLICY_EDITION',409)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state not in ('READY','IN_PROGRESS'):
            raise CommandFailure('TASK_NOT_READY',409)
        if PolicyAcknowledgement.objects.filter(task=task).exists():
            raise CommandFailure('POLICY_ALREADY_ACKNOWLEDGED',409)
        evidence=PolicyAcknowledgement.objects.create(task=task,actor=actor,
            policy_version=policy['version'],content_sha256=policy['content_sha256'])
        TaskCompletion.objects.create(task=task,evidence_type='POLICY_ACK',
            policy_ack=evidence,completed_by=actor,evidence_hash=policy['content_sha256'])
        task.execution_state='COMPLETED'
        task.completed_at=timezone.now()
        task.version+=1
        task.save(update_fields=['execution_state','completed_at','version'])
        effects=recompute(case)
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='TASK_COMPLETED',
            entity_id=task.pk,changes={'kind':'POLICY_ACK','policy_version':policy['version'],
                'content_sha256':policy['content_sha256'],'case_version':case.version,
                'unlocked':len(effects)})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
            'result':{'task_id':str(task.pk),'state':'COMPLETED',
                'acknowledgement_id':str(evidence.pk),'policy_version':policy['version'],
                'content_sha256':policy['content_sha256'],'progress':case_progress(case)},
            'affected_task_ids':[str(task.pk)]+[x['task_id'] for x in effects],
            'event_ids':[str(event[0])]}
        _receipt(actor,'m3-policy-ack',key,req_digest,case,response,200)
    return response,200
