"""Astra follow-up R2/R3/R5/R8: real Postgres and HTTP boundary regressions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from unittest.mock import patch
import importlib
import json
import uuid
import pytest
from django.db import DatabaseError, OperationalError, connection, transaction, close_old_connections
from django.test import Client
from django.utils import timezone
from backend.accounts.models import User, Organization, Membership, LoginThrottle
from backend.accounts.security import admit_attempt
from backend.onboarding.models import OnboardingCase, CaseAssignment
from backend.onboarding.services import reassign_owner,set_command_timeouts,CommandFailure
from backend.audit.models import AuditEvent,CommandReceipt

@pytest.fixture
def case_context(db):
    org=Organization.objects.create(name='Closure review')
    employee_user=User.objects.create_user(email='empclosure@example.test',password='StrongSecretPassword!2026')
    employee=Membership.objects.create(user=employee_user,organization=org,role='EMPLOYEE')
    case=OnboardingCase.objects.create(organization=org,employee=employee,joining_date=timezone.localdate())
    hr_user=User.objects.create_user(email='hrclosure@example.test',password='StrongSecretPassword!2026')
    hr=Membership.objects.create(user=hr_user,organization=org,role='HR',can_coordinate_ownership=True)
    CaseAssignment.objects.create(case=case,role='HR',member=hr,effective_from=timezone.now())
    return org,employee_user,employee,case,hr_user,hr

@pytest.mark.django_db(transaction=True)
def test_r3_case_root_change_denied_even_when_new_root_valid(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    foreign=Organization.objects.create(name='Foreign org')
    foreign_user=User.objects.create_user(email='externalclosure@example.test',password='StrongSecretPassword!2026')
    foreign_member=Membership.objects.create(user=foreign_user,organization=foreign,role='EMPLOYEE')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            OnboardingCase.objects.filter(pk=case.pk).update(
                organization=foreign,employee=foreign_member)
    case.refresh_from_db()
    assert case.organization_id==org.pk and case.employee_id==employee.pk

@pytest.mark.django_db(transaction=True)
def test_r3_issuer_only_membership_cannot_change_identity(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    original=User.objects.create_user(email='issuerclosure@example.test',password='StrongSecretPassword!2026')
    issuer=Membership.objects.create(user=original,organization=org,role='IT')
    assigned_user=User.objects.create_user(email='itclosure@example.test',password='StrongSecretPassword!2026')
    assignee=Membership.objects.create(user=assigned_user,organization=org,role='IT')
    CaseAssignment.objects.create(case=case,role='IT',member=assignee,assigned_by=issuer,
        effective_from=timezone.now())
    foreign=Organization.objects.create(name='Foreign org')
    other=User.objects.create_user(email='issuerother@example.test',password='StrongSecretPassword!2026')
    for kwargs in ({'organization':foreign},{'user':other},{'role':'MANAGER'}):
        with pytest.raises(DatabaseError):
            with transaction.atomic():
                Membership.objects.filter(pk=issuer.pk).update(**kwargs)
    issuer.refresh_from_db()
    assert issuer.organization_id==org.pk and issuer.user_id==original.pk and issuer.role=='IT'

@pytest.mark.django_db(transaction=True)
def test_r3_migration_preflight_rejects_legacy_malformed_root(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    foreign=Organization.objects.create(name='Old invalid org')
    migration=importlib.import_module('backend.onboarding.migrations.0004_immutable_roots_and_issuer_guard')
    # Simulate a malformed 0001 legacy row using the schema-owner privilege in
    # an isolated rollback-only test transaction. Normal web roles cannot do this.
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('ALTER TABLE public.onboarding_onboardingcase DISABLE TRIGGER m1_case_root_immutable')
                cursor.execute('ALTER TABLE public.onboarding_onboardingcase DISABLE TRIGGER m1_case_links')
                cursor.execute('UPDATE public.onboarding_onboardingcase SET organization_id=%s WHERE id=%s',
                    [foreign.pk,case.pk])
                cursor.execute('ALTER TABLE public.onboarding_onboardingcase ENABLE TRIGGER m1_case_links')
                cursor.execute('ALTER TABLE public.onboarding_onboardingcase ENABLE TRIGGER m1_case_root_immutable')
                cursor.execute(migration.PREFLIGHT_SQL)
    case.refresh_from_db()
    assert case.organization_id==org.pk

@pytest.mark.django_db(transaction=True)
def test_r5_denied_login_identifiers_create_no_persistent_rows():
    ip='198.51.100.200'
    for i in range(30):
        assert admit_attempt('login',f'allowed{i}@example.test',ip)
    start=LoginThrottle.objects.count()
    for i in range(120):
        assert not admit_attempt('login',f'unseen{i}@example.test',ip)
    assert LoginThrottle.objects.count()==start
    assert not admit_attempt('login','allowed0@example.test',ip)
    assert admit_attempt('login','new@example.test','198.51.100.201')

@pytest.mark.django_db(transaction=True)
def test_r5_expired_window_recovery_and_full_http_redemption_limit():
    ip='203.0.113.54'
    for i in range(5):
        assert admit_attempt('login','window@example.test',ip)
    assert not admit_attempt('login','window@example.test',ip)
    LoginThrottle.objects.filter(bucket__startswith='login:').update(
        window_start=timezone.now()-timedelta(minutes=16))
    assert admit_attempt('login','window@example.test',ip)
    c=Client(enforce_csrf_checks=True)
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    for i in range(11):
        response=c.post('/api/v1/auth/password-reset-tokens/redeem',
            json.dumps({'token':f'{i:04d}'+'x'*35,'new_password':'StrongPassword!2026'}),
            content_type='application/json',HTTP_X_CSRFTOKEN=csrf,REMOTE_ADDR='203.0.113.76')
        assert response.status_code==(400 if i<10 else 429),response.content

@pytest.mark.django_db(transaction=True)
def test_r2_reciprocal_hr_reassignments_avoid_user_deadlock():
    org=Organization.objects.create(name='Opposite HR owners')
    users=[];members=[];cases=[]
    for i in range(2):
        h=User.objects.create_user(email=f'hr{i}@opposite.test',password='StrongPassword!2026')
        hm=Membership.objects.create(user=h,organization=org,role='HR',can_coordinate_ownership=True)
        e=User.objects.create_user(email=f'emp{i}@opposite.test',password='StrongPassword!2026')
        em=Membership.objects.create(user=e,organization=org,role='EMPLOYEE')
        case=OnboardingCase.objects.create(organization=org,employee=em,joining_date=timezone.localdate())
        CaseAssignment.objects.create(case=case,member=hm,role='HR',effective_from=timezone.now())
        users.append(h);members.append(hm);cases.append(case)
    # Internal boundary hook proves both case locks are held before trying
    # the opposing HR User locks. No sleeps and no mocked database locks.
    barrier=Barrier(2)
    def work(i):
        close_old_connections()
        try:
            return reassign_owner(actor=users[i],case_id=cases[i].pk,role='HR',
                new_member_id=members[1-i].pk,expected_version=1,reason='Mutual rotation',
                key=uuid.uuid4(),_test_after_case_lock=lambda:barrier.wait(timeout=8))
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1=pool.submit(work,0);f2=pool.submit(work,1)
        a,b=f1.result(timeout=15),f2.result(timeout=15)
    assert a[1]==b[1]==200
    assert AuditEvent.objects.filter(event_type='OWNER_REASSIGNED').count()==2
    assert CommandReceipt.objects.count()==2
    assert all(OnboardingCase.objects.get(pk=c.pk).version==2 for c in cases)

@pytest.mark.django_db(transaction=True)
def test_r8_database_timeout_settings_are_transaction_local():
    with connection.cursor() as cursor:
        cursor.execute("SHOW lock_timeout")
        before_lock=cursor.fetchone()[0]
        cursor.execute("SHOW statement_timeout")
        before_statement=cursor.fetchone()[0]
    with transaction.atomic():
        set_command_timeouts()
        with connection.cursor() as cursor:
            cursor.execute("SHOW lock_timeout")
            assert cursor.fetchone()[0]=='2s'
            cursor.execute("SHOW statement_timeout")
            assert cursor.fetchone()[0]=='5s'
    with connection.cursor() as cursor:
        cursor.execute("SHOW lock_timeout")
        assert cursor.fetchone()[0]==before_lock
        cursor.execute("SHOW statement_timeout")
        assert cursor.fetchone()[0]==before_statement

@pytest.mark.django_db(transaction=True)
def test_r8_preflight_db_failure_is_controlled_not_500(case_context):
    from backend.accounts import views as account_views
    org,employee_user,employee,case,hr_user,hr=case_context
    c=Client(enforce_csrf_checks=True)
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    login=c.post('/api/v1/auth/login',
        json.dumps({'email':hr_user.email,'password':'StrongSecretPassword!2026'}),
        content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert login.status_code==200
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    with patch.object(account_views,'actor_context',side_effect=OperationalError('simulated preflight outage')):
        for method,path,data in (
            ('get','/api/v1/auth/me',None),
            ('post','/api/v1/auth/password/change',{'old_password':'x','new_password':'y'}),
            ('post','/api/v1/auth/password-reset-tokens',{'case_id':str(case.pk)}),
        ):
            if method=='get':
                response=c.get(path)
            else:
                response=c.post(path,json.dumps(data),content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
            assert response.status_code==503,response.content
            assert response.json()['error']['code']=='DATABASE_UNAVAILABLE'
    assert AuditEvent.objects.count()==0

@pytest.mark.django_db(transaction=True)
def test_r8_live_session_membership_db_failure_fails_closed(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    c=Client(enforce_csrf_checks=True)
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    r=c.post('/api/v1/auth/login',
        json.dumps({'email':hr_user.email,'password':'StrongSecretPassword!2026'}),
        content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code==200
    with patch('backend.accounts.middleware.Membership.objects.filter',side_effect=OperationalError('offline')):
        blocked=c.get('/api/v1/auth/me')
    assert blocked.status_code==503 and blocked.json()['error']['code']=='DATABASE_UNAVAILABLE'

@pytest.mark.django_db(transaction=True)
def test_c3_missing_role_is_bounded_4xx_without_effect(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    c=Client(enforce_csrf_checks=True)
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    assert c.post('/api/v1/auth/login',json.dumps({
        'email':hr_user.email,'password':'StrongSecretPassword!2026'}),
        content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code==200
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    response=c.post(f'/api/v1/cases/{case.pk}/assignments',
       json.dumps({'new_member_id':str(hr.pk),'reason':'no role'}),
       content_type='application/json',HTTP_X_CSRFTOKEN=csrf,
       HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH=f'"case:{case.pk}:v1"')
    assert response.status_code in (400,422),response.content
    assert OnboardingCase.objects.get(pk=case.pk).version==1
    assert CommandReceipt.objects.count()==0 and AuditEvent.objects.count()==0
