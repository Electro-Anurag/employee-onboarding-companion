"""M7 portfolio is paginated and scoped to currently assigned HR only."""
import time
import uuid
import pytest
from datetime import timedelta
from django.test import Client
from django.utils import timezone
from backend.accounts.models import User,Membership
from backend.audit.models import AuditEvent
from backend.onboarding.commands import create_case,activate_case
from backend.onboarding.models import OnboardingCase
from backend.onboarding.tests.test_m2_workflow import world,published,create
from backend.onboarding.portfolio import portfolio_page
from backend.onboarding.services import CommandFailure


def session_client(user):
    client=Client()
    client.force_login(user)
    session=client.session
    session['m1_session_started']=time.time()
    session.save()
    return client


@pytest.mark.django_db(transaction=True)
def test_current_hr_portfolio_is_cursor_paginated_and_read_only(world):
    organization,actors=world
    version=published(world)
    first,_=create(world,version)
    second_user=User.objects.create_user(
        email='second.employee@astervalelabs.test',
        password='VerifiedStrongPassword!2026',display_name='Second Synthetic Employee')
    second_member=Membership.objects.create(
        user=second_user,organization=organization,role='EMPLOYEE')
    second,_=create_case(actor=actors['HR'][0],employee_id=second_member.pk,
        template_version_id=version,joining_date=timezone.localdate()+timedelta(days=20),
        owner_ids={'IT':actors['IT'][1].pk,'MANAGER':actors['MANAGER'][1].pk},
        key=uuid.uuid4())
    # A CREATED case has no activated task snapshot. Only the first case
    # acquires its 17 mandatory tasks; never invent progress on the second.
    activate_case(actor=actors['HR'][0],case_id=uuid.UUID(first['case_id']),
                  key=uuid.uuid4(),expected_version=1)
    before=AuditEvent.objects.count()
    client=session_client(actors['HR'][0])
    path='/api/v1/portfolio'
    page1=client.get(path+'?limit=1')
    assert page1.status_code==200,page1.content
    assert page1['Cache-Control']=='private, no-store'
    data=page1.json()
    assert data['scope']=='CURRENT_HR_ASSIGNMENTS_PAGE'
    assert data['page_count']==1 and data['has_more']
    assert data['next_cursor']==data['results'][0]['case_id']
    page2=client.get(path+'?limit=1&after='+data['next_cursor'])
    assert page2.status_code==200,page2.content
    last=page2.json()
    assert last['page_count']==1 and not last['has_more']
    assert last['next_cursor'] is None
    seen={data['results'][0]['case_id'],last['results'][0]['case_id']}
    assert seen=={first['case_id'],second['case_id']}
    by_id={row['case_id']:row for row in (
        data['results'][0],last['results'][0])}
    assert by_id[first['case_id']]['progress']['mandatory_total']==17
    assert by_id[first['case_id']]['status']=='PRE_JOINING'
    assert by_id[second['case_id']]['progress']['mandatory_total']==0
    assert by_id[second['case_id']]['status']=='CREATED'
    assert AuditEvent.objects.count()==before
    assert client.post(path,data='{}',content_type='application/json').status_code==405
    assert client.get(path+'?limit=0').status_code==422
    assert client.get(path+'?limit=26').status_code==422
    assert client.get(path+'?after=invalid').status_code==422


@pytest.mark.django_db(transaction=True)
def test_portfolio_denies_other_roles_and_hides_unassigned_hr_cases(world):
    organization,actors=world
    created,_=create(world,published(world))
    not_assigned=User.objects.create_user(
        email='portfolio.hr.unassigned@astervalelabs.test',
        password='VerifiedStrongPassword!2026',display_name='Unassigned HR')
    Membership.objects.create(user=not_assigned,organization=organization,
        role='HR',available=True)
    client=session_client(not_assigned)
    result=client.get('/api/v1/portfolio')
    assert result.status_code==200
    assert result.json()['results']==[]
    assert created['case_id'] not in str(result.content)
    for role in ('EMPLOYEE','IT','MANAGER'):
        assert session_client(actors[role][0]).get('/api/v1/portfolio').status_code==404
    assert Client().get('/api/v1/portfolio').status_code in (401,403,404)
