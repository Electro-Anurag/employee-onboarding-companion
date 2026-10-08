"""M2 real PostgreSQL template/case/workflow/role qualification."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
import pytest
from django.db import transaction,DatabaseError,IntegrityError,close_old_connections
from django.test import Client
from django.utils import timezone
from backend.accounts.models import User,Membership,Organization
from backend.templates.models import TemplateVersion,TemplateTask,TemplateDependency
from backend.templates.services import (TemplateFailure,create_default,edit_template,publish_template,
   next_draft,create_template)
from backend.onboarding.models import (OnboardingCase,CaseAssignment,Task,TaskDependency,
    TaskCompletion,ManagerAttestation)
from backend.onboarding.commands import create_case,activate_case,start_task,attest_manager
from backend.onboarding.services import CommandFailure,reassign_owner
from backend.audit.models import AuditEvent,CommandReceipt

@pytest.fixture
def world(db):
    org=Organization.objects.create(name='Aster Vale Labs (Synthetic)',timezone='Asia/Kolkata')
    persons={}
    for role in ('HR','EMPLOYEE','IT','MANAGER'):
        user=User.objects.create_user(email=f'{role.lower()}@astervalelabs.test',
             password='VerifiedStrongPassword!2026',display_name=f'Synthetic {role}')
        member=Membership.objects.create(user=user,organization=org,role=role,
            can_manage_templates=(role=='HR'),can_coordinate_ownership=(role=='HR'))
        persons[role]=(user,member)
    return org,persons

def published(world):
    org,p=world
    draft=create_default(actor=p['HR'][0])
    done=publish_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),revision=1)
    assert done['state']=='PUBLISHED' and len(done['tasks'])==17
    return uuid.UUID(done['version_id'])

def create(world,version,offset=28):
    org,p=world
    return create_case(actor=p['HR'][0],employee_id=p['EMPLOYEE'][1].pk,
        template_version_id=version,joining_date=timezone.localdate()+timedelta(days=offset),
        owner_ids={'IT':p['IT'][1].pk,'MANAGER':p['MANAGER'][1].pk},key=uuid.uuid4())

@pytest.mark.django_db(transaction=True)
def test_m2_default_publish_immutable_and_new_version(world):
    org,p=world
    draft=create_default(actor=p['HR'][0])
    assert len(draft['tasks'])==17 and draft['state']=='DRAFT'
    published=publish_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),revision=1)
    assert published['state']=='PUBLISHED' and len(published['dependencies'])>8
    task=TemplateTask.objects.get(version_id=published['version_id'],key='manager_preparation')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            TemplateTask.objects.filter(pk=task.pk).update(title='Unauthorized rewrite')
    with pytest.raises(TemplateFailure):
        edit_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),
            revision=1,tasks=published['tasks'],edges=published['dependencies'])
    cloned=next_draft(actor=p['HR'][0],template_id=uuid.UUID(draft['id']))
    assert cloned['version']==2 and cloned['state']=='DRAFT'
    assert cloned['tasks']==published['tasks']
    updated=edit_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),
        revision=1,tasks=[{**x,'title':x['title']+' updated'} if x['key']=='manager_preparation' else x
            for x in cloned['tasks']],edges=cloned['dependencies'])
    assert updated['revision']==2
    assert TemplateTask.objects.get(pk=task.pk).title==task.title

@pytest.mark.django_db(transaction=True)
def test_m2_invalid_cycle_optional_prerequisite_and_owner(world):
    org,p=world
    bad=[dict(key=k,kind='MANAGER_PREPARATION',owner_role='MANAGER',title=k,
              required=True,available_offset_days=-10,due_offset_days=0,
              evidence_spec={'type':'MANAGER_PREPARATION'}) for k in ('first','second')]
    with pytest.raises(TemplateFailure) as exc:
        create_template(actor=p['HR'][0],key='cycle',name='Cycle',
            tasks=bad,edges=[{'predecessor':'first','successor':'second'},
                             {'predecessor':'second','successor':'first'}])
    assert exc.value.code=='DEPENDENCY_CYCLE'
    with pytest.raises(TemplateFailure) as exc:
        create_template(actor=p['HR'][0],key='bad_owner',name='Bad owner',
            tasks=[{**bad[0],'owner_role':'IT'}],edges=[])
    assert exc.value.code=='INCOMPATIBLE_TASK_OR_EVIDENCE'
    with pytest.raises(TemplateFailure) as exc:
        create_template(actor=p['HR'][0],key='bad_optional',name='Bad optional',
            tasks=[{**bad[0],'required':False},bad[1]],
            edges=[{'predecessor':'first','successor':'second'}])
    assert exc.value.code=='MANDATORY_DEPENDS_ON_OPTIONAL'
    assert TemplateVersion.objects.count()==0

@pytest.mark.django_db(transaction=True)
def test_m2_create_activate_progress_task_dependency_and_replay(world):
    org,p=world
    v=published(world)
    result,status=create(world,v)
    assert status==201 and result['result']['status']=='CREATED'
    case=OnboardingCase.objects.get(pk=result['case_id'])
    assert case.created_by_id==p['HR'][0].pk
    assert Task.objects.count()==0
    with pytest.raises(CommandFailure):
        activate_case(actor=p['EMPLOYEE'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    key=uuid.uuid4()
    a,code=activate_case(actor=p['HR'][0],case_id=case.pk,key=key,expected_version=1)
    assert code==200 and a['result']['status']=='PRE_JOINING'
    assert a==activate_case(actor=p['HR'][0],case_id=case.pk,key=key,expected_version=1)[0]
    assert OnboardingCase.objects.get(pk=case.pk).version==2
    assert Task.objects.filter(case=case).count()==17
    assert TaskDependency.objects.filter(case=case).count()>8
    manager=Task.objects.get(case=case,key='manager_preparation')
    intro=Task.objects.get(case=case,key='team_introduction')
    access=Task.objects.get(case=case,key='workspace_access')
    personal=Task.objects.get(case=case,key='personal_details')
    assert manager.execution_state=='READY'
    assert intro.execution_state=='BLOCKED'
    assert access.execution_state=='BLOCKED'
    assert personal.execution_state=='READY'
    with pytest.raises(CommandFailure):
        start_task(actor=p['IT'][0],case_id=case.pk,task_id=access.pk,
            key=uuid.uuid4(),expected_version=2)
    assert case.tasks.filter(execution_state='COMPLETED').count()==0
    first,start_status=start_task(actor=p['MANAGER'][0],case_id=case.pk,
                                  task_id=manager.pk,key=uuid.uuid4(),expected_version=2)
    assert start_status==200
    manager.refresh_from_db()
    assert manager.execution_state=='IN_PROGRESS'
    expected=3
    typed={'first_week_plan':'Pair on first-week deliverables','buddy_name':'Synthetic Buddy',
           'workstation_ready':True}
    result,code=attest_manager(actor=p['MANAGER'][0],case_id=case.pk,task_id=manager.pk,
        fields=typed,note='Equipment checked',key=uuid.uuid4(),expected_version=expected)
    assert code==200 and result['result']['state']=='COMPLETED'
    assert result['result']['progress']['mandatory_completed']==1
    assert TaskCompletion.objects.filter(task=manager).count()==1
    assert ManagerAttestation.objects.filter(task=manager).count()==1
    intro.refresh_from_db()
    assert intro.execution_state=='NOT_STARTED' # prerequisite met, but future availability
    assert Task.objects.get(case=case,key='workspace_access').execution_state=='BLOCKED'
    with pytest.raises(CommandFailure):
        attest_manager(actor=p['HR'][0],case_id=case.pk,task_id=manager.pk,
            fields=typed,note='Wrong role',key=uuid.uuid4(),expected_version=4)
    assert AuditEvent.objects.filter(event_type='TASK_COMPLETED').count()==1

@pytest.mark.django_db(transaction=True)
def test_m2_activation_atomic_rollback_on_missing_owner(world):
    org,p=world
    v=published(world)
    created,status=create(world,v)
    case=OnboardingCase.objects.get(pk=created['case_id'])
    bad=CaseAssignment.objects.get(case=case,role='MANAGER')
    bad.member.available=False
    bad.member.save(update_fields=['available'])
    with pytest.raises(CommandFailure) as exc:
        activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    assert exc.value.code=='ASSIGNMENT_NOT_READY'
    assert Task.objects.filter(case=case).count()==0
    assert case.task_dependencies.count()==0
    assert OnboardingCase.objects.get(pk=case.pk).status=='CREATED'
    assert AuditEvent.objects.filter(event_type='CASE_ACTIVATED').count()==0

@pytest.mark.django_db(transaction=True)
def test_m2_create_one_open_case_and_no_inactive_duplicate(world):
    org,p=world
    version=published(world)
    first,status=create(world,version)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create(world,version)
    assert OnboardingCase.objects.count()==1

@pytest.mark.django_db(transaction=True)
def test_m2_cross_case_dependency_is_db_denied(world):
    org,p=world
    v=published(world)
    a,status=create(world,v)
    a_case=OnboardingCase.objects.get(pk=a['case_id'])
    activate_case(actor=p['HR'][0],case_id=a_case.pk,key=uuid.uuid4(),expected_version=1)
    second=User.objects.create_user(email='otheremp@astervalelabs.test',password='VerifiedStrongPassword!2026')
    employee=Membership.objects.create(user=second,organization=org,role='EMPLOYEE')
    b,status=create_case(actor=p['HR'][0],employee_id=employee.pk,template_version_id=v,
             joining_date=timezone.localdate()+timedelta(days=28),
             owner_ids={'IT':p['IT'][1].pk,'MANAGER':p['MANAGER'][1].pk},key=uuid.uuid4())
    b_case=OnboardingCase.objects.get(pk=b['case_id'])
    activate_case(actor=p['HR'][0],case_id=b_case.pk,key=uuid.uuid4(),expected_version=1)
    parent=Task.objects.get(case=a_case,key='manager_preparation')
    child=Task.objects.get(case=b_case,key='team_introduction')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            TaskDependency.objects.create(case=a_case,predecessor=parent,successor=child)

@pytest.mark.django_db(transaction=True)
def test_m2_hr_only_draft_and_created_case_privacy_http(world):
    org,p=world
    c=Client(enforce_csrf_checks=True)
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    def login(role):
        return c.post('/api/v1/auth/login',json.dumps({
            'email':p[role][0].email,'password':'VerifiedStrongPassword!2026'}),
            content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert login('HR').status_code==200
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    publish_resp=c.post('/api/v1/templates',json.dumps({'use_default':True}),
           content_type='application/json',HTTP_X_CSRFTOKEN=csrf,
           HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert publish_resp.status_code==201,publish_resp.content
    tmpl=publish_resp.json()
    r=c.post('/api/v1/templates/'+tmpl['id']+'/publish','{}',
          content_type='application/json',HTTP_X_CSRFTOKEN=csrf,
          HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
          HTTP_IF_MATCH=f'"template:{tmpl["id"]}:r1"')
    assert r.status_code==200,r.content
    body={'employee_id':str(p['EMPLOYEE'][1].pk),'template_version_id':tmpl['version_id'],
          'joining_date':(timezone.localdate()+timedelta(days=28)).isoformat(),
          'owners':{'IT':str(p['IT'][1].pk),'MANAGER':str(p['MANAGER'][1].pk)}}
    created=c.post('/api/v1/cases',json.dumps(body),content_type='application/json',
         HTTP_X_CSRFTOKEN=csrf,HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert created.status_code==201,created.content
    case_id=created.json()['case_id']
    assert c.get('/api/v1/cases/'+case_id).status_code==200
    assert c.post('/api/v1/auth/logout','{}',content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf).status_code==200
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    assert login('IT').status_code==200
    assert c.get('/api/v1/cases/'+case_id).status_code==404
    assert c.get('/api/v1/cases').json()['results']==[]
    assert c.get('/api/v1/workspaces/me').json()['results']==[]
    assert c.post('/api/v1/templates',json.dumps({'use_default':True}),
        content_type='application/json',HTTP_X_CSRFTOKEN=csrf,
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())).status_code==403

@pytest.mark.django_db(transaction=True)
def test_m2_reassignment_moves_incomplete_task_ownership(world):
    org,p=world
    v=published(world)
    created,status=create(world,v)
    case=OnboardingCase.objects.get(pk=created['case_id'])
    activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    new_user=User.objects.create_user(email='itreplacement@astervalelabs.test',
                                      password='VerifiedStrongPassword!2026')
    new_member=Membership.objects.create(user=new_user,organization=org,role='IT')
    _,status=reassign_owner(actor=p['HR'][0],case_id=case.pk,role='IT',
          new_member_id=new_member.pk,reason='New team IT',key=uuid.uuid4(),expected_version=2)
    assert status==200
    tasks=Task.objects.filter(case=case,owner_role='IT')
    assert tasks.count()==2
    assert all(x.owner_assignment.member_id==new_member.pk for x in tasks)
    assert Task.objects.filter(case=case,owner_role='IT',execution_state='BLOCKED').count()==2
    assert case.tasks.filter(execution_state='COMPLETED').count()==0


@pytest.mark.django_db(transaction=True)
def test_m2_db_guards_make_activated_graph_and_evidence_immutable(world):
    org,p=world
    v=published(world)
    created,_=create(world,v)
    case=OnboardingCase.objects.get(pk=created['case_id'])
    activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    manager=Task.objects.get(case=case,key='manager_preparation')
    intro=Task.objects.get(case=case,key='team_introduction')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Task.objects.filter(pk=manager.pk).update(key='silently_swapped')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            TaskDependency.objects.create(case=case,predecessor=manager,successor=intro)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            TaskDependency.objects.filter(case=case).delete()
    fields={'first_week_plan':'Attend synthetic orientation','buddy_name':'Sample Buddy',
            'workstation_ready':True}
    outcome,_=attest_manager(actor=p['MANAGER'][0],case_id=case.pk,task_id=manager.pk,
         fields=fields,note='Evidence captured by responsible manager',
         key=uuid.uuid4(),expected_version=2)
    assert outcome['result']['state']=='COMPLETED'
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Task.objects.filter(pk=manager.pk).update(execution_state='READY')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ManagerAttestation.objects.filter(task=manager).update(note='Modified later')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            TaskCompletion.objects.filter(task=manager).update(evidence_hash='f'*64)
    manager.refresh_from_db()
    assert manager.execution_state=='COMPLETED'
    assert TaskCompletion.objects.filter(task=manager).count()==1

@pytest.mark.django_db(transaction=True)
def test_m2_activated_case_role_workspaces_and_cross_employee_isolation(world):
    org,p=world
    version=published(world)
    created,_=create(world,version)
    case=OnboardingCase.objects.get(pk=created['case_id'])
    def as_actor(role):
        client=Client(enforce_csrf_checks=True)
        token=client.get('/api/v1/auth/csrf').json()['csrf_token']
        r=client.post('/api/v1/auth/login',json.dumps({
            'email':p[role][0].email,'password':'VerifiedStrongPassword!2026'}),
            content_type='application/json',HTTP_X_CSRFTOKEN=token)
        assert r.status_code==200,r.content
        return client
    for role in ('EMPLOYEE','IT','MANAGER'):
        client=as_actor(role)
        assert client.get('/api/v1/cases/'+str(case.pk)).status_code==404
    activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    for role in ('EMPLOYEE','IT','MANAGER','HR'):
        client=as_actor(role)
        assert client.get('/api/v1/cases/'+str(case.pk)).status_code==200
        payload=client.get('/api/v1/workspaces/me').json()['results']
        assert payload and all(x['case_id']==str(case.pk) and x['owner_role']==role for x in payload)
        assert client.get('/api/v1/cases/'+str(case.pk)+'/tasks').status_code==200
    other=User.objects.create_user(email='outsideremployee@astervalelabs.test',password='VerifiedStrongPassword!2026')
    Membership.objects.create(user=other,organization=org,role='EMPLOYEE',active=True)
    c=Client(enforce_csrf_checks=True);token=c.get('/api/v1/auth/csrf').json()['csrf_token']
    assert c.post('/api/v1/auth/login',json.dumps({'email':other.email,
          'password':'VerifiedStrongPassword!2026'}),content_type='application/json',
          HTTP_X_CSRFTOKEN=token).status_code==200
    assert c.get('/api/v1/cases/'+str(case.pk)).status_code==404
    assert c.get('/api/v1/cases/'+str(case.pk)+'/tasks').status_code==404
    assert c.get('/api/v1/workspaces/me').json()['results']==[]

@pytest.mark.django_db(transaction=True)
def test_m2_created_hr_reassignment_hides_from_former_owner(world):
    org,p=world
    version=published(world)
    created,_=create(world,version)
    case=OnboardingCase.objects.get(pk=created['case_id'])
    next_user=User.objects.create_user(email='newhr@astervalelabs.test',password='VerifiedStrongPassword!2026')
    next_hr=Membership.objects.create(user=next_user,organization=org,role='HR')
    _,status=reassign_owner(actor=p['HR'][0],case_id=case.pk,role='HR',
            new_member_id=next_hr.pk,reason='Owner reassigned before start',
            key=uuid.uuid4(),expected_version=1)
    assert status==200
    from backend.onboarding.services import get_authorized_case,scoped_cases
    with pytest.raises(CommandFailure):
        get_authorized_case(p['HR'][0],case.pk)
    member,current=get_authorized_case(next_user,case.pk)
    assert current.pk==case.pk
    assert scoped_cases(p['HR'][0]).filter(pk=case.pk).count()==0
    assert scoped_cases(next_user).filter(pk=case.pk).count()==1
    with pytest.raises(CommandFailure):
        activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=2)
    result,status=activate_case(actor=next_user,case_id=case.pk,key=uuid.uuid4(),expected_version=2)
    assert status==200 and result['result']['status']=='PRE_JOINING'
    assert Task.objects.filter(case=case).count()==17

@pytest.mark.django_db(transaction=True)
def test_m2_api_idempotency_and_stale_case_preconditions(world):
    org,p=world
    draft=create_default(actor=p['HR'][0])
    publish_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),revision=1)
    c=Client(enforce_csrf_checks=True)
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    assert c.post('/api/v1/auth/login',json.dumps({
            'email':p['HR'][0].email,'password':'VerifiedStrongPassword!2026'}),
            content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code==200
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    body={'employee_id':str(p['EMPLOYEE'][1].pk),'template_version_id':draft['version_id'],
          'joining_date':(timezone.localdate()+timedelta(days=28)).isoformat(),
          'owners':{'IT':str(p['IT'][1].pk),'MANAGER':str(p['MANAGER'][1].pk)}}
    key=str(uuid.uuid4())
    def create_req(k,payload=body):
        return c.post('/api/v1/cases',json.dumps(payload),content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf,HTTP_IDEMPOTENCY_KEY=k)
    first=create_req(key)
    assert first.status_code==201,first.content
    assert create_req(key).status_code==201
    assert create_req(key).json()==first.json()
    different=create_req(key,{**body,'joining_date':(timezone.localdate()+timedelta(days=29)).isoformat()})
    assert different.status_code==409 and different.json()['error']['code']=='IDEMPOTENCY_KEY_REUSED'
    case_id=first.json()['case_id']
    early=c.post('/api/v1/cases/'+case_id+'/activate','{}',content_type='application/json',
        HTTP_X_CSRFTOKEN=csrf,HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert early.status_code==428
    success=c.post('/api/v1/cases/'+case_id+'/activate','{}',content_type='application/json',
        HTTP_X_CSRFTOKEN=csrf,HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH='"case:'+case_id+':v1"')
    assert success.status_code==200,success.content
    retry=c.post('/api/v1/cases/'+case_id+'/activate','{}',content_type='application/json',
        HTTP_X_CSRFTOKEN=csrf,HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH='"case:'+case_id+':v1"')
    assert retry.status_code==409 and retry.json()['error']['code']=='STALE_VERSION'
    assert Task.objects.filter(case_id=case_id).count()==17


@pytest.mark.django_db(transaction=True)
def test_m2_case_timeline_filters_events_by_role(world):
    org,p=world
    version=published(world)
    created,_=create(world,version)
    case=OnboardingCase.objects.get(pk=created['case_id'])
    activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='manager_preparation')
    fields={'first_week_plan':'Prepare first-week goals','buddy_name':'Synthetic Partner',
            'workstation_ready':True}
    attest_manager(actor=p['MANAGER'][0],case_id=case.pk,task_id=task.pk,
        fields=fields,note='Synthetic attestation',key=uuid.uuid4(),expected_version=2)
    def read_as(role):
        client=Client(enforce_csrf_checks=True)
        csrf=client.get('/api/v1/auth/csrf').json()['csrf_token']
        login=client.post('/api/v1/auth/login',json.dumps({
            'email':p[role][0].email,'password':'VerifiedStrongPassword!2026'}),
            content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
        assert login.status_code==200
        response=client.get('/api/v1/cases/'+str(case.pk)+'/timeline')
        assert response.status_code==200,response.content
        return response.json()['results']
    hr=read_as('HR')
    assert {'CASE_CREATED','CASE_ACTIVATED','TASK_COMPLETED'}.issubset(
        {x['event_type'] for x in hr})
    assert any('actor_id' in x for x in hr)
    manager=read_as('MANAGER')
    assert [x['event_type'] for x in manager]==['TASK_COMPLETED']
    assert all('changes' not in x and 'actor_id' not in x for x in manager)
    assert read_as('IT')==[]
    assert read_as('EMPLOYEE')==[]


@pytest.mark.django_db(transaction=True)
def test_m2_activation_requires_usable_employee_login_or_pending_invite(world):
    from backend.accounts.security import issue_token
    from backend.accounts.models import OneTimeToken
    org,p=world
    version=published(world)
    employee=p['EMPLOYEE'][0]
    employee.set_unusable_password()
    employee.save(update_fields=['password'])
    created,_=create(world,version)
    case=OnboardingCase.objects.get(pk=created['case_id'])
    with pytest.raises(CommandFailure) as missing:
        activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    assert missing.value.code=='EMPLOYEE_CREDENTIAL_REQUIRED'
    assert Task.objects.filter(case=case).count()==0
    invite=issue_token(employee,OneTimeToken.INVITE,issuer=p['HR'][0])
    assert invite
    result,status=activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    assert status==200 and len(result['affected_task_ids'])==17
    assert Task.objects.filter(case=case).count()==17

@pytest.mark.django_db(transaction=True)
def test_m2_local_clock_fields_are_versioned_and_drive_case_schedule(world):
    from zoneinfo import ZoneInfo
    org,p=world
    draft=create_default(actor=p['HR'][0])
    changed=[]
    for task in draft['tasks']:
        if task['key']=='manager_preparation':
            changed.append({**task,'available_local_time':'07:15','due_local_time':'19:45'})
        else:changed.append(task)
    next_d=edit_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),
           revision=1,tasks=changed,edges=draft['dependencies'])
    assert next_d['revision']==2
    published_v=publish_template(actor=p['HR'][0],template_id=uuid.UUID(draft['id']),revision=2)
    assert published_v['tasks'][5]['available_local_time']=='07:15'
    version=uuid.UUID(published_v['version_id'])
    created,_=create(world,version)
    case=OnboardingCase.objects.get(pk=created['case_id'])
    activate_case(actor=p['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case=case,key='manager_preparation')
    assert task.available_at.astimezone(ZoneInfo('Asia/Kolkata')).strftime('%H:%M')=='07:15'
    assert task.due_at.astimezone(ZoneInfo('Asia/Kolkata')).strftime('%H:%M')=='19:45'
    assert TemplateTask.objects.get(version_id=version,key='manager_preparation').due_local_time=='19:45'
    invalid=[{**t,'available_offset_days':0,'due_offset_days':0,
              'available_local_time':'19:00','due_local_time':'09:00'}
             if t['key']=='manager_preparation' else t for t in changed]
    with pytest.raises(TemplateFailure):
        create_template(actor=p['HR'][0],key='invalid_time',name='Invalid clocks',
            tasks=invalid,edges=draft['dependencies'])
