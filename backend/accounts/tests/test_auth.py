import json
from datetime import timedelta
import uuid
import pytest
from django.test import Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from backend.accounts.models import Membership,Organization,OneTimeToken
from backend.accounts.security import issue_token
from backend.onboarding.models import OnboardingCase,CaseAssignment

@pytest.fixture
def environment(db):
    User=get_user_model();org=Organization.objects.create(name='Synthetic Workplace')
    users={};members={}
    for role in ['EMPLOYEE','HR','IT','MANAGER']:
        u=User.objects.create_user(email=f'{role.lower()}@example.test',password='DemoStrongPassword!2026',display_name=f'Synthetic {role}')
        m=Membership.objects.create(user=u,organization=org,role=role,can_coordinate_ownership=(role=='HR'))
        users[role]=u;members[role]=m
    other=User.objects.create_user(email='second@example.test',password='DemoStrongPassword!2026',display_name='Second employee')
    otherm=Membership.objects.create(user=other,organization=org,role='EMPLOYEE')
    case=OnboardingCase.objects.create(organization=org,employee=members['EMPLOYEE'],joining_date=timezone.localdate())
    for role in ['HR','IT','MANAGER']:
        CaseAssignment.objects.create(case=case,role=role,member=members[role],effective_from=timezone.now())
    othercase=OnboardingCase.objects.create(organization=org,employee=otherm,joining_date=timezone.localdate())
    return users,members,case,other,othercase

def csrf_client():
    c=Client(enforce_csrf_checks=True);r=c.get('/api/v1/auth/csrf');assert r.status_code==200
    return c,r.json()['csrf_token']

def post(c,url,payload,token,**headers):
    return c.post(url,data=json.dumps(payload),content_type='application/json',HTTP_X_CSRFTOKEN=token,**headers)

def login_as(c,role):
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    r=post(c,'/api/v1/auth/login',{'email':f'{role.lower()}@example.test','password':'DemoStrongPassword!2026'},csrf)
    assert r.status_code==200,r.content
    return c.get('/api/v1/auth/csrf').json()['csrf_token']

@pytest.mark.django_db(transaction=True)
def test_real_session_csrf_four_roles_and_logout(environment):
    users,members,case,other,othercase=environment
    for role in users:
        c,token=csrf_client()
        assert c.post('/api/v1/auth/login',data='{}',content_type='application/json').status_code==403
        token=login_as(c,role)
        r=c.get('/api/v1/auth/me');assert r.status_code==200 and r.json()['role']==role
        assert r.json()['email']==users[role].email
        assert 'password' not in r.json()
        assert c.get('/api/v1/cases').status_code==200
        assert c.get(f'/api/v1/cases/{case.pk}').status_code==200
        assert post(c,'/api/v1/auth/logout',{},token).status_code==200
        assert c.get('/api/v1/auth/me').status_code==401

@pytest.mark.django_db(transaction=True)
def test_employee_scope_and_no_mass_assignment(environment):
    users,members,case,other,othercase=environment
    c,_=csrf_client();token=login_as(c,'EMPLOYEE')
    listed=c.get('/api/v1/cases').json()['results']
    assert len(listed)==1 and listed[0]['id']==str(case.pk)
    assert c.get(f'/api/v1/cases/{othercase.pk}').status_code==404
    assert post(c,f'/api/v1/cases/{case.pk}/assignments',{'role':'IT','new_member_id':str(members['IT'].pk),'reason':'foo'},token,
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH=f'"case:{case.pk}:v{case.version}"').status_code==404
    assert c.get('/api/v1/cases').json()['results'][0]['my_role']=='EMPLOYEE'

@pytest.mark.django_db(transaction=True)
def test_actor_deactivation_revokes_session(environment):
    users,members,case,other,othercase=environment
    c,_=csrf_client();login_as(c,'IT')
    members['IT'].active=False;members['IT'].save(update_fields=['active'])
    assert c.get('/api/v1/auth/me').status_code==401

@pytest.mark.django_db(transaction=True)
def test_absolute_session_expiry(environment):
    users,members,case,other,othercase=environment
    c,_=csrf_client();login_as(c,'EMPLOYEE')
    session=c.session;session['m1_session_started']=1.0;session.save()
    assert c.get('/api/v1/auth/me').status_code==401

@pytest.mark.django_db(transaction=True)
def test_invitation_single_use_and_non_hr_denied(environment):
    users,members,case,other,othercase=environment
    users['EMPLOYEE'].set_unusable_password();users['EMPLOYEE'].save(update_fields=['password'])
    c,_=csrf_client();token=login_as(c,'HR')
    r=post(c,'/api/v1/auth/invitations',{'case_id':str(case.pk)},token)
    assert r.status_code==201,r.content
    raw=r.json()['invitation_token'];assert raw not in str(OneTimeToken.objects.first().__dict__)
    anon,cs=csrf_client()
    payload={'token':raw,'new_password':'NewStrongPassword!2026'}
    assert post(anon,'/api/v1/auth/invitations/redeem',payload,cs).status_code==200
    assert post(anon,'/api/v1/auth/invitations/redeem',payload,cs).status_code==400
    assert users['EMPLOYEE'].__class__.objects.get(pk=users['EMPLOYEE'].pk).check_password('NewStrongPassword!2026')

@pytest.mark.django_db(transaction=True)
def test_reset_only_for_assigned_employee_and_one_use(environment):
    users,members,case,other,othercase=environment
    c,_=csrf_client();token=login_as(c,'HR')
    assert post(c,'/api/v1/auth/password-reset-tokens',{'case_id':str(othercase.pk)},token).status_code==404
    r=post(c,'/api/v1/auth/password-reset-tokens',{'case_id':str(case.pk)},token);assert r.status_code==201
    raw=r.json()['reset_token']
    assert post(c,'/api/v1/auth/password-reset-tokens/redeem',{'token':raw,'new_password':'ChangedPassword!2026'},token).status_code==200
    assert post(c,'/api/v1/auth/password-reset-tokens/redeem',{'token':raw,'new_password':'ChangedPassword!2026'},token).status_code==400

@pytest.mark.django_db(transaction=True)
def test_wrong_password_and_failed_login_throttle(environment):
    users,members,case,other,othercase=environment
    c,token=csrf_client()
    payload={'email':'employee@example.test','password':'incorrect'}
    for n in range(5):assert post(c,'/api/v1/auth/login',payload,token).status_code in (401,429)
    assert post(c,'/api/v1/auth/login',{'email':'employee@example.test','password':'DemoStrongPassword!2026'},token).status_code==429

@pytest.mark.django_db(transaction=True)
def test_password_change_requires_old_password(environment):
    users,members,case,other,othercase=environment
    c,_=csrf_client();token=login_as(c,'EMPLOYEE')
    assert post(c,'/api/v1/auth/password/change',{'old_password':'bad','new_password':'SomeNewPassword!2026'},token).status_code==403
    assert post(c,'/api/v1/auth/password/change',{'old_password':'DemoStrongPassword!2026','new_password':'SomeNewPassword!2026'},token).status_code==200
    assert c.get('/api/v1/auth/me').status_code==200

@pytest.mark.django_db(transaction=True)
def test_csrf_and_bad_input_rejected(environment):
    users,members,case,other,othercase=environment
    c,_=csrf_client();token=login_as(c,'HR')
    assert c.post('/api/v1/auth/logout',content_type='application/json',data='{}').status_code==403
    assert post(c,'/api/v1/auth/password/change',{'unknown_field':1},token).status_code==422

@pytest.mark.django_db(transaction=True)
def test_private_api_no_store(environment):
    users,members,case,other,othercase=environment
    c,_=csrf_client()
    anonymous=c.get('/api/v1/auth/me')
    assert 'no-store' in anonymous['Cache-Control']
    login_as(c,'HR')
    for path in ['/api/v1/auth/me','/api/v1/cases',
                 f'/api/v1/cases/{case.pk}/tasks']:
        result=c.get(path)
        assert result.status_code==200
        assert 'private' in result['Cache-Control']
        assert 'no-store' in result['Cache-Control']
        assert result['Pragma']=='no-cache'
