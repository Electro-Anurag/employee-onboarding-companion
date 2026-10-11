"""Read-only, HR-isolated mandatory case dashboard on real PostgreSQL."""
import uuid
import time
import pytest
from django.test import Client
from backend.accounts.models import Membership,User
from backend.audit.models import AuditEvent
from backend.onboarding.commands import activate_case,attest_manager
from backend.onboarding.dashboard import case_dashboard
from backend.onboarding.models import OnboardingCase,Task,TaskCompletion
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.onboarding.services import CommandFailure


@pytest.mark.django_db(transaction=True)
def test_m7_case_dashboard_counts_only_verified_mandatory_evidence(world):
    _,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    case.refresh_from_db()
    version=case.version
    before_audit=AuditEvent.objects.count()
    before_completions=TaskCompletion.objects.count()
    result=case_dashboard(actors['HR'][0],case.pk)
    assert result['case_version']==version
    assert result['case_status']=='PRE_JOINING'
    assert result['scope']=='REQUIRED_APPLICABLE_TASKS_ONLY'
    assert result['progress']['mandatory_total']==17
    assert result['progress']['mandatory_completed']==0
    assert result['unclosed_exceptions']==0
    assert sum(r['mandatory_total'] for r in result['by_role'].values())==17
    assert sum(r['mandatory_completed'] for r in result['by_role'].values())==0
    assert sum(result['states'].values())==17
    assert AuditEvent.objects.count()==before_audit
    assert TaskCompletion.objects.count()==before_completions
    case.refresh_from_db()
    assert case.version==version

    task=Task.objects.get(case=case,key='manager_preparation')
    attest_manager(actor=actors['MANAGER'][0],case_id=case.pk,task_id=task.pk,
                   fields={'first_week_plan':'Synthetic preparation',
                           'buddy_name':'Synthetic mentor','workstation_ready':True},
                   note='Typed preparation completed',key=uuid.uuid4(),
                   expected_version=case.version)
    newer=case_dashboard(actors['HR'][0],case.pk)
    assert newer['progress']['mandatory_completed']==1
    assert newer['by_role']['MANAGER']['mandatory_completed']==1
    assert sum(r['mandatory_completed'] for r in newer['by_role'].values())==1


@pytest.mark.django_db(transaction=True)
def test_m7_case_dashboard_http_scoped_to_current_hr_only(world):
    _,actors=world
    made,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    path=f'/api/v1/cases/{case.pk}/dashboard'
    hr=Client();hr.force_login(actors['HR'][0])
    session=hr.session
    session['m1_session_started']=time.time()
    session.save()
    ok=hr.get(path)
    assert ok.status_code==200,ok.content
    assert ok['Cache-Control']=='private, no-store'
    assert ok.json()['case_id']==str(case.pk)
    assert ok.json()['progress']['mandatory_total']==17
    assert hr.post(path,data='{}',content_type='application/json').status_code==405
    manager=Client();manager.force_login(actors['MANAGER'][0])
    manager_session=manager.session
    manager_session['m1_session_started']=time.time()
    manager_session.save()
    employee=Client();employee.force_login(actors['EMPLOYEE'][0])
    employee_session=employee.session
    employee_session['m1_session_started']=time.time()
    employee_session.save()
    assert manager.get(path).status_code==404
    assert employee.get(path).status_code==404
    assert hr.get(f'/api/v1/cases/{uuid.uuid4()}/dashboard').status_code==404
    assert Client().get(path).status_code in (401,403,404)
