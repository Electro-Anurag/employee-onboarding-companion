"""M5 real PostgreSQL exception journey, no UI-only status transitions."""
import json
import uuid
from datetime import timedelta
import pytest
from django.db import transaction,DatabaseError
from django.test import Client
from django.utils import timezone
from backend.accounts.models import Organization,User,Membership
from backend.onboarding.models import (OnboardingCase,Task,CaseException,
                                        CaseExceptionEvent)
from backend.onboarding.commands import activate_case,attest_manager
from backend.onboarding.exceptions import (open_exception,assign_exception,
    resolve_exception,close_exception)
from backend.onboarding.services import CommandFailure
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.audit.models import AuditEvent,CommandReceipt


def _active_case(world):
    result,_=create(world,published(world),offset=-1)
    case=OnboardingCase.objects.get(pk=result['case_id'])
    activate_case(actor=world[1]['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    case.refresh_from_db()
    return case


def _version(case):
    case.refresh_from_db()
    return case.version


def _login(user):
    c=Client(enforce_csrf_checks=True)
    token=c.get('/api/v1/auth/csrf').json()['csrf_token']
    result=c.post('/api/v1/auth/login',
        data=json.dumps({'email':user.email,'password':'VerifiedStrongPassword!2026'}),
        content_type='application/json',HTTP_X_CSRFTOKEN=token)
    assert result.status_code==200,result.content
    return c,c.get('/api/v1/auth/csrf').json()['csrf_token']


@pytest.mark.django_db(transaction=True)
def test_exception_cannot_clear_prerequisite_without_human_completion(world):
    _,people=world
    case=_active_case(world)
    intro=Task.objects.get(case=case,key='team_introduction')
    manager=Task.objects.get(case=case,key='manager_preparation')
    hr=people['HR'][0];manager_user=people['MANAGER'][0]
    key=uuid.uuid4()
    opened,code=open_exception(actor=manager_user,case_id=case.pk,task_id=intro.pk,
        cause='PREREQUISITE_BLOCKED',note='Preparation evidence missing',
        key=key,expected_version=_version(case))
    assert code==201
    ex_id=uuid.UUID(opened['result']['id'])
    assert opened==open_exception(actor=manager_user,case_id=case.pk,task_id=intro.pk,
        cause='PREREQUISITE_BLOCKED',note='Preparation evidence missing',
        key=key,expected_version=2)[0]
    assert CaseException.objects.filter(case=case,task=intro).count()==1
    with pytest.raises(CommandFailure) as err:
        open_exception(actor=manager_user,case_id=case.pk,task_id=intro.pk,
            cause='PREREQUISITE_BLOCKED',note='Duplicate blocker active',
            key=uuid.uuid4(),expected_version=_version(case))
    assert err.value.code=='EXCEPTION_ALREADY_ACTIVE'
    with pytest.raises(CommandFailure) as err:
        resolve_exception(actor=manager_user,case_id=case.pk,exception_id=ex_id,
            note='Cannot resolve without assignment',key=uuid.uuid4(),
            expected_version=_version(case))
    assert err.value.code=='EXCEPTION_NOT_ASSIGNED'
    assign_exception(actor=hr,case_id=case.pk,exception_id=ex_id,
        assignee_role='MANAGER',note='Manager owns missing preparation',
        key=uuid.uuid4(),expected_version=_version(case))
    with pytest.raises(CommandFailure) as err:
        resolve_exception(actor=manager_user,case_id=case.pk,exception_id=ex_id,
            note='Pretend preparation is done',key=uuid.uuid4(),
            expected_version=_version(case))
    assert err.value.code=='EXCEPTION_PREDICATE_STILL_ACTIVE'
    assert not hasattr(intro,'completion')
    assert intro.execution_state=='BLOCKED'
    # Real manager-preparation typed proof is required before resolution.
    attest_manager(actor=manager_user,case_id=case.pk,task_id=manager.pk,
        fields={'first_week_plan':'Pair on first-week deliverables',
            'buddy_name':'Synthetic Buddy','workstation_ready':True},
        note='Completed evidence',key=uuid.uuid4(),expected_version=_version(case))
    intro.refresh_from_db()
    assert intro.execution_state in ('READY','NOT_STARTED')
    resolved,_=resolve_exception(actor=manager_user,case_id=case.pk,
        exception_id=ex_id,note='Preparation now independently completed',
        key=uuid.uuid4(),expected_version=_version(case))
    assert resolved['result']['status']=='RESOLVED'
    close_exception(actor=hr,case_id=case.pk,exception_id=ex_id,
        note='Verified no remaining prerequisite',key=uuid.uuid4(),
        expected_version=_version(case))
    ex=CaseException.objects.get(pk=ex_id)
    assert ex.status=='CLOSED' and ex.episode==1
    assert list(ex.events.order_by('created_at').values_list('action',flat=True))==[
        'OPEN','ASSIGN','RESOLVE','CLOSE']
    assert CommandReceipt.objects.filter(case=case,
        route__startswith='m5-exception-').count()==4
    assert AuditEvent.objects.filter(event_type='M5_EXCEPTION_CLOSE',
        entity_id=ex.pk).count()==1
    evt=CaseExceptionEvent.objects.get(exception=ex,action='OPEN')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            CaseExceptionEvent.objects.filter(pk=evt.pk).update(note='Rewritten history')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            CaseExceptionEvent.objects.filter(pk=evt.pk).delete()


@pytest.mark.django_db(transaction=True)
def test_exception_owner_unavailable_reopens_new_episode_and_denies_other_tenant(world):
    org,people=world
    case=_active_case(world)
    task=Task.objects.get(case=case,key='manager_preparation')
    manager_member=people['MANAGER'][1]
    manager_member.available=False
    manager_member.save(update_fields=['available'])
    hr=people['HR'][0]
    first,_=open_exception(actor=hr,case_id=case.pk,task_id=task.pk,
        cause='OWNER_UNAVAILABLE',note='Current manager cannot work',
        key=uuid.uuid4(),expected_version=_version(case))
    ex_id=uuid.UUID(first['result']['id'])
    with pytest.raises(CommandFailure) as err:
        assign_exception(actor=hr,case_id=case.pk,exception_id=ex_id,
            assignee_role='MANAGER',note='Unavailable owner cannot be assigned',
            key=uuid.uuid4(),expected_version=_version(case))
    assert err.value.code=='EXCEPTION_ASSIGNEE_UNAVAILABLE'
    assign_exception(actor=hr,case_id=case.pk,exception_id=ex_id,
        assignee_role='HR',note='HR will coordinate recovery',
        key=uuid.uuid4(),expected_version=_version(case))
    another_org=Organization.objects.create(name='Other synthetic tenant')
    outsider=User.objects.create_user(email='outsider@another.test',
        password='VerifiedStrongPassword!2026',display_name='Outsider')
    Membership.objects.create(user=outsider,organization=another_org,role='HR')
    with pytest.raises(CommandFailure) as err:
        close_exception(actor=outsider,case_id=case.pk,exception_id=ex_id,
            note='Cross tenant request should fail',key=uuid.uuid4(),
            expected_version=_version(case))
    assert err.value.code=='NOT_FOUND'
    manager_member.available=True
    manager_member.save(update_fields=['available'])
    resolve_exception(actor=hr,case_id=case.pk,exception_id=ex_id,
        note='Owner became available again',key=uuid.uuid4(),
        expected_version=_version(case))
    close_exception(actor=hr,case_id=case.pk,exception_id=ex_id,
        note='Availability verified against owner',key=uuid.uuid4(),
        expected_version=_version(case))
    manager_member.available=False
    manager_member.save(update_fields=['available'])
    second,_=open_exception(actor=hr,case_id=case.pk,task_id=task.pk,
        cause='OWNER_UNAVAILABLE',note='New unavailability occurrence',
        key=uuid.uuid4(),expected_version=_version(case))
    assert second['result']['episode']==2
    assert CaseException.objects.filter(case=case,task=task,cause='OWNER_UNAVAILABLE').count()==2


@pytest.mark.django_db(transaction=True)
def test_exception_http_csrf_stale_version_and_reviewed_records(world):
    _,people=world
    case=_active_case(world)
    intro=Task.objects.get(case=case,key='team_introduction')
    hr,csrf=_login(people['HR'][0])
    path=f'/api/v1/cases/{case.pk}/exceptions'
    payload={'task_id':str(intro.pk),'cause':'PREREQUISITE_BLOCKED',
             'note':'Blocked by real preparation task'}
    response=hr.post(path+'/open',data=json.dumps(payload),content_type='application/json',
        HTTP_X_CSRFTOKEN=csrf,HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v{case.version}"')
    assert response.status_code==201,response.content
    ex=response.json()['result']['id']
    entries=hr.get(path).json()
    assert entries['results'][0]['id']==ex
    assert entries['results'][0]['blocking_now'] is True
    assert entries['results'][0]['events'][0]['action']=='OPEN'
    no_csrf=Client(enforce_csrf_checks=True)
    no_csrf.force_login(people['HR'][0])
    assert no_csrf.post(path+'/open',data='{}',
                        content_type='application/json').status_code==403
    stale=hr.post(path+'/'+ex+'/assign',
        data=json.dumps({'assignee_role':'HR','note':'Assign to available HR'}),
        content_type='application/json',HTTP_X_CSRFTOKEN=csrf,
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v{case.version}"')
    assert stale.status_code==409 and stale.json()['error']['code']=='STALE_VERSION'
    assert CaseExceptionEvent.objects.filter(exception_id=ex).count()==1
