"""Version-pinned employee quiz, graded only by frozen server-side answers."""
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
from backend.training.models import TrainingAttempt
from backend.training.definitions import validate_spec

def attempt(*,actor,case_id,task_id,module_version,content_sha256,answers,key,expected_version):
    if (not isinstance(module_version,str) or not isinstance(content_sha256,str)
            or not isinstance(answers,dict)):
        raise CommandFailure('INVALID_TRAINING_ATTEMPT',422)
    payload={'task_id':str(task_id),'module_version':module_version,
             'content_sha256':content_sha256,'answers':answers}
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,req_hash=_task_command(actor,case_id,task_id,
            'm4-training-attempt',key,payload,expected_version)
        if prior is not None:return prior.response,prior.status_code
        if member.role!=Membership.EMPLOYEE or task.kind!='TRAINING':
            raise CommandFailure('WRONG_TRAINING_TASK',422)
        spec=validate_spec(task.evidence_spec)
        if (not hmac.compare_digest(module_version,spec['module_version'])
                or not hmac.compare_digest(content_sha256,spec['content_sha256'])):
            raise CommandFailure('STALE_TRAINING_MODULE',409)
        expected={q['key'] for q in spec['questions']}
        valid={q['key']:{a['value'] for a in q['options']} for q in spec['questions']}
        if (set(answers)!=expected or
            any(not isinstance(answers[k],str) or answers[k] not in valid[k] for k in expected)):
            raise CommandFailure('INVALID_TRAINING_ANSWERS',422)
        recompute(case)
        task.refresh_from_db()
        if task.execution_state not in ('READY','IN_PROGRESS'):
            raise CommandFailure('TASK_NOT_READY',409)
        last=TrainingAttempt.objects.filter(task=task).order_by('-attempt_number').first()
        attempt_number=last.attempt_number+1 if last else 1
        if attempt_number>10:
            raise CommandFailure('TRAINING_ATTEMPT_LIMIT',409)
        score=sum(answers[q['key']]==q['answer'] for q in spec['questions'])
        passed=score>=spec['passing_score']
        row=TrainingAttempt.objects.create(task=task,attempt_number=attempt_number,
            actor=actor,module_version=module_version,content_sha256=content_sha256,
            answers=answers,score=score,passing_score=spec['passing_score'],passed=passed)
        effects=[]
        if passed:
            TaskCompletion.objects.create(task=task,evidence_type='TRAINING',
                training_attempt=row,completed_by=actor,evidence_hash=content_sha256)
            task.execution_state='COMPLETED'
            task.completed_at=timezone.now()
            task.version+=1
            task.save(update_fields=['execution_state','completed_at','version'])
            effects=recompute(case)
        elif task.work_started_at is None:
            task.work_started_at=timezone.now()
            task.execution_state='IN_PROGRESS'
            task.version+=1
            task.save(update_fields=['work_started_at','execution_state','version'])
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
            event_type='TRAINING_ATTEMPT_GRADED',entity_id=task.pk,
            changes={'attempt_number':attempt_number,'score':score,
                     'passing_score':spec['passing_score'],'passed':passed,
                     'module_version':module_version,'case_version':case.version})
        ids=[str(event[0])]
        if passed:
            completed=append_event(stream_key=f'case:{case.pk}',actor=actor,
                event_type='TASK_COMPLETED',entity_id=task.pk,
                changes={'kind':'TRAINING','content_sha256':content_sha256,
                         'module_version':module_version,'case_version':case.version})
            ids.append(str(completed[0]))
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
            'case_version':case.version,'result':{'task_id':str(task.pk),
               'attempt_id':str(row.pk),'attempt_number':attempt_number,
               'passed':passed,'score':score,'passing_score':spec['passing_score'],
               'task_completion':'COMPLETED' if passed else 'IN_PROGRESS',
               'progress':case_progress(case)},
            'affected_task_ids':[str(task.pk)]+[x['task_id'] for x in effects],
            'event_ids':ids}
        _receipt(actor,'m4-training-attempt',key,req_hash,case,response,200)
    return response,200
