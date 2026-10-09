"""Live PostgreSQL tests: immutable occurrence, current role, time and typed attendance."""
import json
import time
import uuid
from datetime import timedelta
import pytest
from django.db import DatabaseError,transaction
from django.test import Client
from django.utils import timezone
from backend.onboarding.tests.test_m2_workflow import world,create
from backend.templates.services import create_template,publish_template
from backend.onboarding.commands import activate_case,start_task
from backend.onboarding.models import OnboardingCase,Task,TaskCompletion
from backend.onboarding.services import CommandFailure
from backend.activities.commands import schedule,record_attendance
from backend.activities.models import ActivityOccurrence,ActivityAttendance
from backend.audit.models import AuditEvent,CommandReceipt

def activity_case(world,kind='ACTIVITY',role='HR',with_successor=False):
    org,people=world
    tasks=[dict(key='orientation',kind=kind,owner_role=role,
       title='Synthetic orientation',required=True,available_offset_days=-30,
       due_offset_days=0,evidence_spec={'type':kind})]
    edges=[]
    if with_successor:
        tasks.append(dict(key='follow_up',kind='CHECK_IN',owner_role='MANAGER',
            title='Synthetic follow up',required=True,
            available_offset_days=-30,due_offset_days=1,
            evidence_spec={'type':'CHECK_IN'}))
        edges=[{'predecessor':'orientation','successor':'follow_up'}]
    draft=create_template(actor=people['HR'][0],key='activity_'+str(uuid.uuid4())[:8],
        name='Synthetic activity scheduling',tasks=tasks,edges=edges)
    version=publish_template(actor=people['HR'][0],
        template_id=uuid.UUID(draft['id']),revision=1)
    made,_=create(world,uuid.UUID(version['version_id']))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=people['HR'][0],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
    return case,Task.objects.get(case=case,key='orientation'),people

@pytest.mark.django_db(transaction=True)
def test_schedule_is_organizer_owned_append_only_and_never_self_completes(world):
    case,task,people=activity_case(world)
    now=timezone.now()
    start=now+timedelta(hours=2)
    end=start+timedelta(minutes=45)
    base=dict(case_id=case.pk,task_id=task.pk,start=start,end=end,
        medium='VIDEO',reference='Synthetic meeting room',
        reason='Arrange a synthetic orientation for the employee',expected_version=2)
    with pytest.raises(CommandFailure) as unauthorized:
        schedule(**{**base,'actor':people['IT'][0]},key=uuid.uuid4())
    assert unauthorized.value.code=='NOT_FOUND'
    k=uuid.uuid4()
    created,status=schedule(**{**base,'actor':people['HR'][0]},key=k)
    assert status==201 and created['result']['revision']==1
    assert schedule(**{**base,'actor':people['HR'][0]},key=k)[0]==created
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    assert TaskCompletion.objects.count()==0
    occ=ActivityOccurrence.objects.get(pk=created['result']['occurrence_id'])
    with pytest.raises(CommandFailure) as future:
        record_attendance(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
            occurrence_id=occ.pk,outcome='ATTENDED',note='Invalid early attendance',
            key=uuid.uuid4(),expected_version=3)
    assert future.value.code=='FUTURE_ATTENDANCE_FORBIDDEN'
    # Direct ORM insertion must also fail: API validation is not enough.
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ActivityAttendance.objects.create(occurrence=occ,
                recorded_by=people['HR'][0],outcome='ATTENDED',
                note='Forged event that has not happened')
    assert ActivityAttendance.objects.count()==0
    changed,code=schedule(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
        start=now+timedelta(hours=4),end=now+timedelta(hours=5),
        medium='IN_PERSON',reference='Synthetic conference room',
        reason='Reschedule due to organizer availability',key=uuid.uuid4(),
        expected_version=3)
    assert code==201 and changed['result']['revision']==2
    assert ActivityOccurrence.objects.filter(task=task).count()==2
    assert TaskCompletion.objects.count()==0
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ActivityOccurrence.objects.filter(pk=occ.pk).update(meeting_reference='tampered')
    assert ActivityOccurrence.objects.get(pk=occ.pk).meeting_reference=='Synthetic meeting room'
    assert AuditEvent.objects.filter(event_type='ACTIVITY_RESCHEDULED').count()==1

@pytest.mark.django_db(transaction=True)
def test_current_elapsed_organizer_attendance_missed_then_passed_unlocks_dependency(world):
    case,task,people=activity_case(world,kind='INTRODUCTION',role='MANAGER',with_successor=True)
    successor=Task.objects.get(case=case,key='follow_up')
    assert successor.execution_state=='BLOCKED'
    start_task(actor=people['MANAGER'][0],case_id=case.pk,task_id=task.pk,
        key=uuid.uuid4(),expected_version=2)
    # Setup-only completed occurrences represent meetings that happened yesterday.
    # The production scheduling command independently forbids scheduling in the past.
    start=timezone.now()-timedelta(hours=2)
    first=ActivityOccurrence.objects.create(task=task,revision=1,
        begins_at=start,ends_at=start+timedelta(minutes=30),
        medium='VIDEO',meeting_reference='Synthetic past meeting',
        reason='Setup-only elapsed occurrence for attendance test',
        scheduled_by=people['MANAGER'][0])
    with pytest.raises(CommandFailure) as wrong_role:
        record_attendance(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
            occurrence_id=first.pk,outcome='ATTENDED',note='Not the assigned manager',
            key=uuid.uuid4(),expected_version=3)
    assert wrong_role.value.code=='NOT_FOUND'
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ActivityAttendance.objects.create(occurrence=first,
                recorded_by=people['HR'][0],outcome='ATTENDED',
                note='Direct database spoof of manager authority')
    assert ActivityAttendance.objects.count()==0
    missed,status=record_attendance(actor=people['MANAGER'][0],
        case_id=case.pk,task_id=task.pk,occurrence_id=first.pk,
        outcome='MISSED',note='Employee did not attend this time',
        key=uuid.uuid4(),expected_version=3)
    assert status==201 and missed['result']['task_completion']=='IN_PROGRESS'
    assert TaskCompletion.objects.count()==0
    # A later previously-occurred meeting is inserted as controlled fixture.
    second=ActivityOccurrence.objects.create(task=task,revision=2,
        begins_at=timezone.now()-timedelta(hours=1),
        ends_at=timezone.now()-timedelta(minutes=15),
        medium='IN_PERSON',meeting_reference='Synthetic past meeting two',
        reason='Setup-only elapsed reschedule fixture',
        scheduled_by=people['MANAGER'][0])
    with pytest.raises(CommandFailure) as stale:
        record_attendance(actor=people['MANAGER'][0],case_id=case.pk,
            task_id=task.pk,occurrence_id=first.pk,outcome='ATTENDED',
            note='Cannot alter the old occurrence',
            key=uuid.uuid4(),expected_version=4)
    assert stale.value.code=='CURRENT_ACTIVITY_OCCURRENCE_REQUIRED'
    key=uuid.uuid4()
    result,status=record_attendance(actor=people['MANAGER'][0],
        case_id=case.pk,task_id=task.pk,occurrence_id=second.pk,
        outcome='ATTENDED',note='Employee attended and organizer confirmed',
        key=key,expected_version=4)
    assert status==201 and result['result']['task_completion']=='COMPLETED'
    assert record_attendance(actor=people['MANAGER'][0],
        case_id=case.pk,task_id=task.pk,occurrence_id=second.pk,
        outcome='ATTENDED',note='Employee attended and organizer confirmed',
        key=key,expected_version=4)[0]==result
    assert Task.objects.get(pk=task.pk).execution_state=='COMPLETED'
    completion=TaskCompletion.objects.get(task=task)
    assert completion.evidence_type=='ACTIVITY_ATTENDANCE'
    assert completion.activity_attendance_id==uuid.UUID(result['result']['attendance_id'])
    assert Task.objects.get(pk=successor.pk).execution_state=='READY'
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ActivityAttendance.objects.filter(pk=completion.activity_attendance_id).update(outcome='MISSED')
    assert CommandReceipt.objects.filter(route='m4-activity-attendance').count()==2
    assert OnboardingCase.objects.get(pk=case.pk).version==5

@pytest.mark.django_db(transaction=True)
def test_schedule_http_roles_and_history_security(world):
    case,task,people=activity_case(world)
    base=f'/api/v1/cases/{case.pk}/tasks/{task.pk}/activity-occurrences'
    def client(role):
        c=Client()
        c.force_login(people[role][0])
        s=c.session
        s['m1_session_started']=time.time()
        s.save()
        return c
    hr=client('HR')
    emp=client('EMPLOYEE')
    assert emp.get(base).status_code==200
    assert client('IT').get(base).status_code==404
    assert client('MANAGER').get(base).status_code==404
    start=timezone.now()+timedelta(hours=2)
    end=start+timedelta(minutes=45)
    posted=hr.post(base+'/schedule',data=json.dumps({
        'start':start.isoformat(),'end':end.isoformat(),'medium':'VIDEO',
        'meeting_reference':'Synthetic onboarding room',
        'reason':'Arrange a synthetic onboarding session'}),
        content_type='application/json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v2"')
    assert posted.status_code==201,posted.content
    data=emp.get(base).json()
    assert data['current_revision']==1 and len(data['results'])==1
    assert data['results'][0]['attendance'] is None
    assert data['results'][0]['medium']=='VIDEO'
    assert client('MANAGER').post(base+'/schedule',data='{}',content_type='application/json').status_code in (400,404,422,428)
    with pytest.raises(CommandFailure) as future:
        record_attendance(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
            occurrence_id=uuid.UUID(data['results'][0]['id']),outcome='MISSED',
            note='Future attendance cannot be recorded',key=uuid.uuid4(),
            expected_version=3)
    assert future.value.code=='FUTURE_ATTENDANCE_FORBIDDEN'
