"""Case creation, activation and permitted task transitions.

All case mutations are atomic under the case row lock, with idempotent receipts,
typed evidence and append-only audit in the SAME transaction.
"""
import hashlib
import json
import uuid
from datetime import date
from django.db import transaction,connection
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from backend.accounts.models import User,Membership,OneTimeToken
from backend.accounts.security import actor_context
from backend.onboarding.models import (OnboardingCase,CaseAssignment,Task,TaskDependency,
    ManagerAttestation,TaskCompletion)
from backend.onboarding.services import (CommandFailure,authorize_case,set_command_timeouts,_lock_case_authority)
from backend.onboarding.state_machine import scheduled_at,recompute,case_progress,current_assignments
from backend.templates.models import TemplateVersion
from backend.templates.services import _validate_graph,_snapshot
from backend.audit.models import CommandReceipt
from backend.audit.services import append_event

def _digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _lock_receipt(actor,route,key,case_id,normalized_payload):
    if not isinstance(key,uuid.UUID):
        raise CommandFailure('INVALID_IDEMPOTENCY_KEY',422)
    raw=f'{actor.pk}:{route}:{key}'.encode()
    advisory=int.from_bytes(hashlib.sha256(raw).digest()[:8],'big',signed=True)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s)',[advisory])
    existing=CommandReceipt.objects.filter(actor=actor,route=route,idempotency_key=key).first()
    digest=_digest(normalized_payload)
    if existing is not None:
        if existing.request_hash!=digest or (case_id is not None and existing.case_id!=case_id):
            raise CommandFailure('IDEMPOTENCY_KEY_REUSED',409)
        return existing,digest
    return None,digest

def _receipt(actor,route,key,digest,case,response,status=200):
    CommandReceipt.objects.create(actor=actor,route=route,idempotency_key=key,
                                  request_hash=digest,case=case,response=response,status_code=status)

def _case_actor(case,actor):
    member=actor_context(actor,locked=True)
    if not authorize_case(member,case):
        raise CommandFailure('NOT_FOUND',404)
    return member

def create_case(*,actor,employee_id,template_version_id,joining_date,owner_ids,key):
    if type(joining_date) is not date or not isinstance(owner_ids,dict) or set(owner_ids)!=set(('IT','MANAGER')):
        raise CommandFailure('INVALID_CASE_SETUP',422)
    if not isinstance(employee_id,uuid.UUID) or not isinstance(template_version_id,uuid.UUID):
        raise CommandFailure('INVALID_CASE_SETUP',422)
    if not all(isinstance(x,uuid.UUID) for x in owner_ids.values()):
        raise CommandFailure('INVALID_CASE_SETUP',422)
    payload={'employee':str(employee_id),'template_version':str(template_version_id),
             'date':joining_date.isoformat(),'owners':{k:str(v) for k,v in owner_ids.items()}}
    with transaction.atomic():
        set_command_timeouts()
        member=actor_context(actor,locked=True)
        if member.role!=Membership.HR or not member.available:
            raise PermissionDenied()
        existing,digest=_lock_receipt(actor,'m2-create-case',key,None,payload)
        if existing is not None:
            return existing.response,existing.status_code
        v=TemplateVersion.objects.select_related('template').filter(pk=template_version_id,
            template__organization_id=member.organization_id,state=TemplateVersion.PUBLISHED).first()
        if v is None:
            raise CommandFailure('PUBLISHED_TEMPLATE_REQUIRED',422)
        owners={'HR':member.pk,'IT':owner_ids['IT'],'MANAGER':owner_ids['MANAGER'],'EMPLOYEE':employee_id}
        hints={role:Membership.objects.filter(pk=mid).values('user_id').first() for role,mid in owners.items()}
        if any(h is None for h in hints.values()):
            raise CommandFailure('INVALID_CASE_OWNER',422)
        user_ids=sorted(set(h['user_id'] for h in hints.values()),key=str)
        users={i:User.objects.select_for_update().filter(pk=i,is_active=True).first() for i in user_ids}
        mids={}
        for mid in sorted(set(owners.values()),key=str):
            mids[mid]=Membership.objects.select_for_update().filter(pk=mid).first()
        for role,mid in owners.items():
            row=mids.get(mid)
            if (row is None or row.role!=role or not row.active or not row.available
                    or row.organization_id!=member.organization_id or
                    row.user_id!=hints[role]['user_id'] or users[row.user_id] is None):
                raise CommandFailure('INVALID_CASE_OWNER',422)
        case=OnboardingCase.objects.create(organization=member.organization,employee=mids[employee_id],
                    template_version=v,joining_date=joining_date,created_by=actor,status='CREATED')
        now=timezone.now()
        for role in ('HR','IT','MANAGER'):
            CaseAssignment.objects.create(case=case,role=role,member=mids[owners[role]],
                       effective_from=now,assigned_by=member,reason='M2 case setup')
        command_id=uuid.uuid4()
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='CASE_CREATED',
            entity_id=case.pk,command_id=command_id,changes={'template_version_id':str(v.pk),
            'employee_member_id':str(employee_id),'case_version':case.version})
        response={'command_id':str(command_id),'case_id':str(case.pk),'case_version':case.version,
                  'result':{'status':'CREATED','template_version_id':str(v.pk)},'affected_task_ids':[],
                  'event_ids':[str(event[0])]}
        _receipt(actor,'m2-create-case',key,digest,case,response,201)
    return response,201

def _command_case(actor,case_id,route,key,payload,expected_version,require_hr=False):
    if not isinstance(expected_version,int) or isinstance(expected_version,bool) or expected_version<1:
        raise CommandFailure('INVALID_CASE_VERSION',422)
    case=OnboardingCase.objects.select_for_update(of=('self',)).select_related(
        'employee__user','organization').filter(pk=case_id).first()
    if case is None:
        raise CommandFailure('NOT_FOUND',404)
    # Match the independently qualified M1 case -> sorted Users -> sorted
    # Memberships authority lock sequence. Root revocation is rechecked.
    member,root,_=_lock_case_authority(case,actor)
    if not authorize_case(member,case):
        raise CommandFailure('NOT_FOUND',404)
    if require_hr and member.role!=Membership.HR:
        raise CommandFailure('NOT_FOUND',404)
    prior,digest=_lock_receipt(actor,route,key,case_id,payload)
    if prior is not None:
        return case,member,prior,digest
    if case.version!=expected_version:
        raise CommandFailure('STALE_VERSION',409)
    return case,member,None,digest

def activate_case(*,actor,case_id,key,expected_version):
    with transaction.atomic():
        set_command_timeouts()
        case,member,prior,digest=_command_case(actor,case_id,'m2-activate',key,{},expected_version,True)
        if prior is not None:
            return prior.response,prior.status_code
        if case.status!='CREATED' or case.template_version_id is None:
            raise CommandFailure('INVALID_CASE_STATE',409)
        v=TemplateVersion.objects.select_related('template').get(pk=case.template_version_id)
        if v.state!=TemplateVersion.PUBLISHED or v.template.organization_id!=case.organization_id:
            raise CommandFailure('PUBLISHED_TEMPLATE_REQUIRED',422)
        entries,edges=_snapshot(v)
        ordered=_validate_graph(entries,edges)
        if Task.objects.filter(case=case).exists():
            raise CommandFailure('TASKS_ALREADY_INSTANTIATED',409)
        assigned=current_assignments(case,timezone.now())
        for role in ('HR','IT','MANAGER'):
            a=assigned.get(role)
            if (a is None or a.member.role!=role or a.member.organization_id!=case.organization_id
                    or not a.member.active or not a.member.available or not a.member.user.is_active):
                raise CommandFailure('ASSIGNMENT_NOT_READY',422)
        if not case.employee.active or not case.employee.available or not case.employee.user.is_active:
            raise CommandFailure('EMPLOYEE_NOT_READY',422)
        if (not case.employee.user.has_usable_password()
                and not OneTimeToken.objects.filter(user=case.employee.user,purpose='INVITE',
                   used_at__isnull=True,expires_at__gt=timezone.now()).exists()):
            raise CommandFailure('EMPLOYEE_CREDENTIAL_REQUIRED',422)
        instance={}
        for keyname in ordered:
            row=next(x for x in entries if x['key']==keyname)
            template_task=v.tasks.get(key=keyname)
            instance[keyname]=Task.objects.create(
                case=case,template_task=template_task,key=keyname,kind=row['kind'],
                title=row['title'],description=row['description'],owner_role=row['owner_role'],
                required=row['required'],evidence_spec=row['evidence_spec'],
                owner_assignment=assigned.get(row['owner_role']),
                available_at=scheduled_at(case.joining_date,row['available_offset_days'],case.organization.timezone,row['available_local_time']),
                due_at=scheduled_at(case.joining_date,row['due_offset_days'],case.organization.timezone,row['due_local_time']))
        for edge in edges:
            TaskDependency.objects.create(case=case,
                predecessor=instance[edge['predecessor']],successor=instance[edge['successor']])
        today=timezone.localdate(timezone=__import__('zoneinfo').ZoneInfo(case.organization.timezone))
        case.status='ACTIVE' if case.joining_date<=today else 'PRE_JOINING'
        case.activated_at=timezone.now()
        changes=recompute(case)
        case.version+=1
        case.save(update_fields=['status','activated_at','version'])
        event_id=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='CASE_ACTIVATED',
            entity_id=case.pk,changes={'status':case.status,'template_hash':v.content_hash,
            'task_count':len(entries),'case_version':case.version,'ready_tasks':sum(x['to']=='READY' for x in changes)})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
            'result':{'status':case.status,'progress':case_progress(case)},'affected_task_ids':[str(t.pk) for t in instance.values()],
            'event_ids':[str(event_id[0])]}
        _receipt(actor,'m2-activate',key,digest,case,response)
    return response,200

def begin_day_one(*,actor,case_id,key,expected_version):
    """Explicit, date-checked PRE_JOINING -> ACTIVE transition.

    Scheduled automation is deliberately not claimed in M2. The same
    idempotency and current-authorization guarantees apply as activation.
    """
    from zoneinfo import ZoneInfo
    with transaction.atomic():
        set_command_timeouts()
        case,member,prior,digest=_command_case(actor,case_id,'m2-begin-day-one',
                     key,{},expected_version,True)
        if prior is not None:
            return prior.response,prior.status_code
        if case.status!='PRE_JOINING':
            raise CommandFailure('INVALID_CASE_STATE',409)
        today=timezone.localdate(timezone=ZoneInfo(case.organization.timezone))
        if today<case.joining_date:
            raise CommandFailure('JOIN_DATE_NOT_REACHED',409)
        case.status='ACTIVE'
        affected=recompute(case)
        case.version+=1
        case.save(update_fields=['status','version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,
                 event_type='CASE_DAY_ONE_STARTED',entity_id=case.pk,
                 changes={'status':'ACTIVE','case_version':case.version,
                          'task_state_changes':len(affected)})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),
                  'case_version':case.version,
                  'result':{'status':'ACTIVE','progress':case_progress(case)},
                  'affected_task_ids':[x['task_id'] for x in affected],
                  'event_ids':[str(event[0])]}
        _receipt(actor,'m2-begin-day-one',key,digest,case,response)
    return response,200


def _task_command(actor,case_id,task_id,route,key,payload,expected_version):
    case,member,prior,digest=_command_case(actor,case_id,route,key,payload,expected_version)
    if prior is not None:
        return case,member,None,prior,digest
    if case.status not in ('PRE_JOINING','ACTIVE'):
        raise CommandFailure('CASE_NOT_ACTIVE',409)
    task=Task.objects.select_for_update().filter(pk=task_id,case=case).first()
    if task is None:
        raise CommandFailure('NOT_FOUND',404)
    if task.owner_role!=member.role:
        raise CommandFailure('NOT_FOUND',404)
    if member.role==Membership.EMPLOYEE:
        if member.pk!=case.employee_id:
            raise CommandFailure('NOT_FOUND',404)
    elif not case.assignments.filter(pk=task.owner_assignment_id,member=member,role=member.role,
                                      effective_to__isnull=True).exists():
        raise CommandFailure('NOT_FOUND',404)
    return case,member,task,None,digest

def start_task(*,actor,case_id,task_id,key,expected_version):
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,'m2-task-start',key,
                                                     {'task_id':str(task_id)},expected_version)
        if prior is not None: return prior.response,prior.status_code
        recompute(case)
        task.refresh_from_db()
        if task.execution_state!='READY':
            raise CommandFailure('TASK_NOT_READY',409)
        task.work_started_at=timezone.now()
        task.execution_state='IN_PROGRESS'
        task.version+=1
        task.save(update_fields=['work_started_at','execution_state','version'])
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='TASK_STARTED',
            entity_id=task.pk,changes={'task_key':task.key,'case_version':case.version})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
                  'result':{'task_id':str(task.pk),'state':'IN_PROGRESS'},
                  'affected_task_ids':[str(task.pk)],'event_ids':[str(event[0])]}
        _receipt(actor,'m2-task-start',key,digest,case,response)
    return response,200

def attest_manager(*,actor,case_id,task_id,fields,note,key,expected_version):
    if not isinstance(fields,dict) or set(fields)!=set(('first_week_plan','buddy_name','workstation_ready')):
        raise CommandFailure('INVALID_ATTESTATION',422)
    if (not isinstance(fields['first_week_plan'],str) or not 8<=len(fields['first_week_plan'])<=300
            or not isinstance(fields['buddy_name'],str) or not 2<=len(fields['buddy_name'])<=100
            or type(fields['workstation_ready']) is not bool
            or not isinstance(note,str) or not 1<=len(note.strip())<=500):
        raise CommandFailure('INVALID_ATTESTATION',422)
    payload={'task_id':str(task_id),'fields':fields,'note':note}
    with transaction.atomic():
        set_command_timeouts()
        case,member,task,prior,digest=_task_command(actor,case_id,task_id,
                     'm2-attest-manager',key,payload,expected_version)
        if prior is not None:return prior.response,prior.status_code
        recompute(case)
        task.refresh_from_db()
        if task.kind!='MANAGER_PREPARATION' or member.role!=Membership.MANAGER:
            raise CommandFailure('WRONG_EVIDENCE_KIND',422)
        if task.execution_state not in ('READY','IN_PROGRESS'):
            raise CommandFailure('TASK_NOT_READY',409)
        if not fields['workstation_ready']:
            raise CommandFailure('PREPARATION_INCOMPLETE',422)
        att=ManagerAttestation.objects.create(task=task,actor=actor,prepared_fields=fields,note=note)
        proof=hashlib.sha256(json.dumps({'fields':fields,'note':note,'actor':str(actor.pk)},
                           sort_keys=True).encode()).hexdigest()
        TaskCompletion.objects.create(task=task,manager_attestation=att,
                                      evidence_type='MANAGER_PREPARATION',completed_by=actor,evidence_hash=proof)
        task.execution_state='COMPLETED'
        task.completed_at=timezone.now()
        task.version+=1
        task.save(update_fields=['execution_state','completed_at','version'])
        effects=recompute(case)
        case.version+=1
        case.save(update_fields=['version'])
        event=append_event(stream_key=f'case:{case.pk}',actor=actor,event_type='TASK_COMPLETED',
            entity_id=task.pk,changes={'kind':task.kind,'evidence_hash':proof,
            'case_version':case.version,'unlocked':len(effects)})
        response={'command_id':str(uuid.uuid4()),'case_id':str(case.pk),'case_version':case.version,
            'result':{'task_id':str(task.pk),'state':'COMPLETED','evidence_id':str(att.pk),
                      'progress':case_progress(case)},
            'affected_task_ids':[str(task.pk)]+[e['task_id'] for e in effects],
            'event_ids':[str(event[0])]}
        _receipt(actor,'m2-attest-manager',key,digest,case,response)
    return response,200
