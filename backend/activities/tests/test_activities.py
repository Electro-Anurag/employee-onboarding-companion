"""Live PostgreSQL tests: immutable occurrence, current role, time and typed attendance."""
import json
import time as sleeping_time
import time
import uuid
from datetime import timedelta
import pytest
from django.db import DatabaseError,transaction,connection
from django.test import Client
from django.utils import timezone
from backend.onboarding.tests.test_m2_workflow import world,create
from backend.templates.services import create_template,publish_template
from backend.onboarding.commands import activate_case,start_task
from backend.onboarding.models import OnboardingCase,Task,TaskCompletion
from backend.onboarding.services import CommandFailure
from backend.activities.commands import schedule,record_attendance,cancel_occurrence
from backend.activities.models import ActivityOccurrence,ActivityAttendance,ActivityCancellation
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

@pytest.mark.django_db(transaction=True)
def test_activity_cancellation_preserves_required_work_and_revision_history(world):
    case,task,people=activity_case(world)
    first_start=timezone.now()+timedelta(hours=2)
    first_end=first_start+timedelta(minutes=40)
    first,status=schedule(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
        start=first_start,end=first_end,medium='VIDEO',
        reference='Synthetic scheduled room',reason='Initial employee orientation invitation',
        key=uuid.uuid4(),expected_version=2)
    assert status==201
    occurrence_id=uuid.UUID(first['result']['occurrence_id'])
    with pytest.raises(CommandFailure) as forbidden:
        cancel_occurrence(actor=people['EMPLOYEE'][0],case_id=case.pk,task_id=task.pk,
            occurrence_id=occurrence_id,reason='Unauthorized employee cancellation',
            key=uuid.uuid4(),expected_version=3)
    assert forbidden.value.code=='NOT_FOUND'
    with pytest.raises(CommandFailure) as wrong_manager:
        cancel_occurrence(actor=people['MANAGER'][0],case_id=case.pk,task_id=task.pk,
            occurrence_id=occurrence_id,reason='Unassigned manager cancellation attempt',
            key=uuid.uuid4(),expected_version=3)
    assert wrong_manager.value.code=='NOT_FOUND'
    key=uuid.uuid4()
    cancelled,status=cancel_occurrence(actor=people['HR'][0],case_id=case.pk,
        task_id=task.pk,occurrence_id=occurrence_id,
        reason='Orientation organizer will be unavailable',
        key=key,expected_version=3)
    assert status==201 and cancelled['result']['reschedule_required'] is True
    assert cancel_occurrence(actor=people['HR'][0],case_id=case.pk,
        task_id=task.pk,occurrence_id=occurrence_id,
        reason='Orientation organizer will be unavailable',
        key=key,expected_version=3)[0]==cancelled
    task.refresh_from_db()
    assert task.execution_state=='IN_PROGRESS'
    assert TaskCompletion.objects.count()==0
    assert ActivityCancellation.objects.count()==1
    assert OnboardingCase.objects.get(pk=case.pk).version==4
    with pytest.raises(CommandFailure) as cannot_attend:
        record_attendance(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
            occurrence_id=occurrence_id,outcome='ATTENDED',
            note='Pretend that a cancelled event happened',
            key=uuid.uuid4(),expected_version=4)
    assert cannot_attend.value.code=='ACTIVITY_OCCURRENCE_CANCELLED'
    with pytest.raises(CommandFailure) as duplicated:
        cancel_occurrence(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
            occurrence_id=occurrence_id,reason='Duplicate cancellation rejected',
            key=uuid.uuid4(),expected_version=4)
    assert duplicated.value.code=='ACTIVITY_ALREADY_CANCELLED'
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ActivityCancellation.objects.filter(occurrence_id=occurrence_id).update(reason='tampered')
    second,status=schedule(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
        start=timezone.now()+timedelta(hours=4),
        end=timezone.now()+timedelta(hours=5),medium='IN_PERSON',
        reference='New synthetic meeting room',reason='Replacement after cancellation',
        key=uuid.uuid4(),expected_version=4)
    assert status==201 and second['result']['revision']==2
    assert ActivityCancellation.objects.get(occurrence_id=occurrence_id).reason==(
        'Orientation organizer will be unavailable')
    assert TaskCompletion.objects.count()==0
    assert OnboardingCase.objects.get(pk=case.pk).version==5
    with pytest.raises(CommandFailure) as stale:
        cancel_occurrence(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
            occurrence_id=occurrence_id,reason='Cannot cancel superseded version',
            key=uuid.uuid4(),expected_version=5)
    assert stale.value.code=='CURRENT_ACTIVITY_OCCURRENCE_REQUIRED'
    assert AuditEvent.objects.filter(event_type='ACTIVITY_OCCURRENCE_CANCELLED').count()==1
    assert CommandReceipt.objects.filter(route='m4-activity-cancel').count()==1

@pytest.mark.django_db(transaction=True)
def test_manager_owned_meeting_may_be_cancelled_by_assigned_hr_but_not_another_role(world):
    case,task,people=activity_case(world,kind='INTRODUCTION',role='MANAGER')
    first,status=schedule(actor=people['MANAGER'][0],case_id=case.pk,task_id=task.pk,
        start=timezone.now()+timedelta(hours=2),
        end=timezone.now()+timedelta(hours=3),medium='VIDEO',
        reference='Manager introduction room',
        reason='Assign a first week introduction session',
        key=uuid.uuid4(),expected_version=2)
    assert status==201
    occ=uuid.UUID(first['result']['occurrence_id'])
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ActivityCancellation.objects.create(occurrence_id=occ,
                cancelled_by=people['EMPLOYEE'][0],
                reason='Forged employee cancellation')
    assert ActivityCancellation.objects.count()==0
    cancelled,status=cancel_occurrence(actor=people['HR'][0],case_id=case.pk,
        task_id=task.pk,occurrence_id=occ,reason='HR-approved rescheduling due to conflict',
        key=uuid.uuid4(),expected_version=3)
    assert status==201 and cancelled['result']['task_completion']=='IN_PROGRESS'
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
    assert TaskCompletion.objects.count()==0
    assert ActivityCancellation.objects.get(occurrence_id=occ).cancelled_by_id==people['HR'][0].pk
    # Cancellation does not transfer manager's task ownership to HR.
    with pytest.raises(CommandFailure) as hr_schedule:
        schedule(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
            start=timezone.now()+timedelta(hours=4),
            end=timezone.now()+timedelta(hours=5),medium='VIDEO',
            reference='Forbidden HR organizer overwrite',
            reason='HR cannot take manager schedule authority',key=uuid.uuid4(),
            expected_version=4)
    assert hr_schedule.value.code=='NOT_FOUND'

@pytest.mark.django_db(transaction=True)
def test_cancel_http_and_private_history_are_consistent(world):
    case,task,people=activity_case(world)
    start=timezone.now()+timedelta(hours=2)
    initial,_=schedule(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
        start=start,end=start+timedelta(minutes=30),medium='VIDEO',
        reference='Synthetic meeting for API',reason='Initial future employee meeting',
        key=uuid.uuid4(),expected_version=2)
    occ=initial['result']['occurrence_id']
    base=f'/api/v1/cases/{case.pk}/tasks/{task.pk}/activity-occurrences'
    def client(role):
        c=Client()
        c.force_login(people[role][0])
        session=c.session
        session['m1_session_started']=time.time()
        session.save()
        return c
    hr=client('HR')
    employee=client('EMPLOYEE')
    it=client('IT')
    route=base+'/'+occ+'/cancel'
    assert it.get(base).status_code==404
    assert employee.post(route,data=json.dumps({'reason':'No authority to cancel'}),
        content_type='application/json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v3"').status_code==404
    res=hr.post(route,data=json.dumps({'reason':'Room unavailable, moving schedule'}),
        content_type='application/json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"case:{case.pk}:v3"')
    assert res.status_code==201,res.content
    saved=employee.get(base)
    assert saved.status_code==200
    body=saved.json()['results'][0]
    assert body['cancellation']['reason']=='Room unavailable, moving schedule'
    assert body['attendance'] is None
    assert employee.get(base).headers['Cache-Control']=='private, no-store'
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'

@pytest.mark.django_db(transaction=True)
def test_post_m3_migration_db_blocks_cancelled_meeting_attendance_after_end(world):
    """M3 0017 must not regress M4 0002's cancelled-occurrence DB guard.

    Create an already-started short synthetic occurrence, cancel it BEFORE
    its end, then attempt raw attendance AFTER end. The older redefined
    function would permit this insert, bypassing the safe command layer.
    """
    case,task,people=activity_case(world)
    start_task(actor=people['HR'][0],case_id=case.pk,task_id=task.pk,
        key=uuid.uuid4(),expected_version=2)
    now=timezone.now()
    occurrence=ActivityOccurrence.objects.create(task=task,revision=1,
        begins_at=now-timedelta(minutes=20),ends_at=now+timedelta(seconds=3),
        medium='VIDEO',meeting_reference='Short synthetic meeting',
        reason='Verify cancellation remains enforced after M3 migration',
        scheduled_by=people['HR'][0])
    cancelled,status=cancel_occurrence(actor=people['HR'][0],case_id=case.pk,
        task_id=task.pk,occurrence_id=occurrence.pk,
        reason='Cancelled before the occurrence could conclude',
        key=uuid.uuid4(),expected_version=3)
    assert status==201
    assert ActivityCancellation.objects.filter(occurrence=occurrence).exists()
    # Verify the actual database body, not application-side validation.
    with connection.cursor() as cursor:
        cursor.execute("""SELECT pg_get_functiondef('public.m4_guard_valid_attendance_insert()'::regprocedure)""")
        definition=cursor.fetchone()[0]
    assert 'activities_activitycancellation' in definition
    assert 'ca.occurrence_id=NEW.occurrence_id' in definition
    wait=(occurrence.ends_at-timezone.now()).total_seconds()+0.25
    if wait>0:
        sleeping_time.sleep(wait)
    assert timezone.now()>occurrence.ends_at
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            ActivityAttendance.objects.create(occurrence=occurrence,
                recorded_by=people['HR'][0],outcome='ATTENDED',
                note='Forged attendance after an earlier cancellation')
    assert ActivityAttendance.objects.filter(occurrence=occurrence).count()==0
    assert TaskCompletion.objects.filter(task=task).count()==0
    assert Task.objects.get(pk=task.pk).execution_state=='IN_PROGRESS'
