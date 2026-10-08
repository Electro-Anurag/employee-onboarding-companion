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
    # All fixture DDL/DML MUST succeed. Re-enabling triggers before commit
    # would itself fail on pending FK events, masking the intended preflight.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE public.onboarding_onboardingcase DISABLE TRIGGER m1_case_root_immutable')
            cursor.execute('ALTER TABLE public.onboarding_onboardingcase DISABLE TRIGGER m1_case_links')
            cursor.execute('UPDATE public.onboarding_onboardingcase SET organization_id=%s WHERE id=%s',
                           [foreign.pk,case.pk])
        with pytest.raises(DatabaseError) as failure:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(migration.PREFLIGHT_SQL)
        assert getattr(failure.value.__cause__,'sqlstate',None)=='23514'
        assert 'M1 migration blocked: invalid legacy case employee/org/role' in str(failure.value)
        transaction.set_rollback(True)  # restores fixture and trigger configuration
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



@pytest.mark.django_db(transaction=True)
def test_r3_legacy_issuer_migration_preflight_aborts(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    issuer_user=User.objects.create_user(email='legacyissuer@example.test',password='StrongPassword!2026')
    issuer=Membership.objects.create(user=issuer_user,organization=org,role='IT')
    assignee_user=User.objects.create_user(email='legacyit@example.test',password='StrongPassword!2026')
    it=Membership.objects.create(user=assignee_user,organization=org,role='IT')
    CaseAssignment.objects.create(case=case,role='IT',member=it,assigned_by=issuer,
                                  effective_from=timezone.now())
    foreign=Organization.objects.create(name='Legacy foreign')
    migration=importlib.import_module('backend.onboarding.migrations.0004_immutable_roots_and_issuer_guard')
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE public.accounts_membership DISABLE TRIGGER m1_member_links')
            cursor.execute('UPDATE public.accounts_membership SET organization_id=%s WHERE id=%s',
                           [foreign.pk,issuer.pk])
        with pytest.raises(DatabaseError) as failure:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(migration.PREFLIGHT_SQL)
        assert getattr(failure.value.__cause__,'sqlstate',None)=='23514'
        assert 'M1 migration blocked: invalid legacy assignment/issuer relationship' in str(failure.value)
        transaction.set_rollback(True)
    issuer.refresh_from_db()
    assert issuer.organization_id==org.pk
@pytest.mark.django_db(transaction=True)
def test_r2_employee_revocation_while_issuance_holds_case_lock(case_context):
    from backend.onboarding.services import issue_credential_for_case
    from backend.accounts.models import OneTimeToken
    org,employee_user,employee,case,hr_user,hr=case_context
    acquired=Event();release=Event()
    def issue():
        close_old_connections()
        try:
            return issue_credential_for_case(actor=hr_user,case_id=case.pk,purpose='RESET',
                _test_after_case_lock=lambda:(acquired.set(),release.wait(timeout=10)))
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(issue)
        assert acquired.wait(timeout=10)
        Membership.objects.filter(pk=employee.pk).update(active=False)
        release.set()
        with pytest.raises(CommandFailure) as rejected:
            future.result(timeout=12)
        assert rejected.value.status==404
    assert OneTimeToken.objects.count()==0
    assert AuditEvent.objects.count()==0

@pytest.mark.django_db(transaction=True)
def test_r2_candidate_revoked_after_case_lock_before_eligibility(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    old_user=User.objects.create_user(email='oldcandidate@example.test',password='StrongPassword!2026')
    old=Membership.objects.create(user=old_user,organization=org,role='IT')
    CaseAssignment.objects.create(case=case,role='IT',member=old,effective_from=timezone.now())
    new_user=User.objects.create_user(email='newcandidate@example.test',password='StrongPassword!2026')
    candidate=Membership.objects.create(user=new_user,organization=org,role='IT')
    acquired=Event();release=Event()
    def attempt():
        close_old_connections()
        try:
            return reassign_owner(actor=hr_user,case_id=case.pk,role='IT',
                new_member_id=candidate.pk,reason='Candidate revoked',expected_version=1,
                key=uuid.uuid4(),_test_after_case_lock=lambda:(acquired.set(),release.wait(timeout=10)))
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(attempt)
        assert acquired.wait(timeout=10)
        Membership.objects.filter(pk=candidate.pk).update(active=False)
        release.set()
        with pytest.raises(CommandFailure) as rejected:
            future.result(timeout=12)
        assert rejected.value.code=='INVALID_ASSIGNEE'
    assert OnboardingCase.objects.get(pk=case.pk).version==1
    assert CommandReceipt.objects.count()==0 and AuditEvent.objects.count()==0

@pytest.mark.django_db(transaction=True)
def test_r8_discarded_reply_can_recover_committed_receipt(case_context):
    from backend.common.http import transient_db_response
    org,employee_user,employee,case,hr_user,hr=case_context
    old_user=User.objects.create_user(email='oldreply@example.test',password='StrongPassword!2026')
    old=Membership.objects.create(user=old_user,organization=org,role='IT')
    CaseAssignment.objects.create(case=case,role='IT',member=old,effective_from=timezone.now())
    new_user=User.objects.create_user(email='newreply@example.test',password='StrongPassword!2026')
    new=Membership.objects.create(user=new_user,organization=org,role='IT')
    key=uuid.uuid4()
    options=dict(actor=hr_user,case_id=case.pk,role='IT',new_member_id=new.pk,
                 reason='Receipt recovery',expected_version=1,key=key)
    first=reassign_owner(**options)
    # Simulate a lost HTTP response *after* a confirmed commit; do not claim
    # that this test severed TCP during PostgreSQL COMMIT acknowledgement.
    unknown=transient_db_response(OperationalError('lost connection'),idempotent=True)
    assert unknown.status_code==503
    assert json.loads(unknown.content)['error']['outcome']=='UNKNOWN'
    recovered=reassign_owner(**options)
    assert recovered==first
    assert AuditEvent.objects.count()==1 and CommandReceipt.objects.count()==1
    assert OnboardingCase.objects.get(pk=case.pk).version==2

def _wait_for_observed_postgres_lock(pid,timeout=4):
    import time
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        with connection.cursor() as cursor:
            cursor.execute("SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s",[pid])
            row=cursor.fetchone()
        if row and row[0]=='Lock':
            return
        time.sleep(.02)
    raise AssertionError('Contender did not reach a real PostgreSQL lock wait')

@pytest.mark.django_db(transaction=True)
def test_r3_parent_and_child_lock_order_parent_first(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    foreign=Organization.objects.create(name='Parent change target')
    other_user=User.objects.create_user(email='foreignparent@example.test',password='StrongPassword!2026')
    other_employee=Membership.objects.create(user=other_user,organization=foreign,role='EMPLOYEE')
    it_user=User.objects.create_user(email='childit@example.test',password='StrongPassword!2026')
    it=Membership.objects.create(user=it_user,organization=org,role='IT')
    ready=Event();release=Event()
    holder_result={}
    child_pid=Event();state={}
    def hold_parent():
        close_old_connections()
        try:
            with transaction.atomic():
                OnboardingCase.objects.select_for_update().get(pk=case.pk)
                ready.set()
                assert release.wait(timeout=12)
                with pytest.raises(DatabaseError):
                    with transaction.atomic():
                        OnboardingCase.objects.filter(pk=case.pk).update(
                            organization=foreign,employee=other_employee)
                holder_result['rejected']=True
        finally:close_old_connections()
    def insert_child():
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_backend_pid()')
                state['pid']=cursor.fetchone()[0]
            child_pid.set()
            CaseAssignment.objects.create(case=case,role='IT',member=it,effective_from=timezone.now())
        finally:close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(hold_parent)
        assert ready.wait(timeout=10)
        b=pool.submit(insert_child)
        assert child_pid.wait(timeout=10)
        try:
            _wait_for_observed_postgres_lock(state['pid'])
        finally:
            release.set()
        a.result(timeout=12);b.result(timeout=12)
    assert holder_result.get('rejected') is True
    assert CaseAssignment.objects.get(case=case,role='IT').member_id==it.pk
    assert OnboardingCase.objects.get(pk=case.pk).organization_id==org.pk

@pytest.mark.django_db(transaction=True)
def test_r3_parent_and_child_lock_order_child_first(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    foreign=Organization.objects.create(name='Parent change target B')
    other_user=User.objects.create_user(email='foreignparentb@example.test',password='StrongPassword!2026')
    other_employee=Membership.objects.create(user=other_user,organization=foreign,role='EMPLOYEE')
    it_user=User.objects.create_user(email='childitb@example.test',password='StrongPassword!2026')
    it=Membership.objects.create(user=it_user,organization=org,role='IT')
    ready=Event();release=Event();pidready=Event();state={}
    def insert_and_hold_child():
        close_old_connections()
        try:
            with transaction.atomic():
                CaseAssignment.objects.create(case=case,role='IT',member=it,
                                              effective_from=timezone.now())
                ready.set()
                assert release.wait(timeout=12)
        finally:close_old_connections()
    def reparent():
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_backend_pid()')
                state['pid']=cursor.fetchone()[0]
            pidready.set()
            try:
                with transaction.atomic():
                    OnboardingCase.objects.filter(pk=case.pk).update(
                        organization=foreign,employee=other_employee)
            except DatabaseError:
                return 'REJECTED'
            return 'UNEXPECTED_SUCCESS'
        finally:close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(insert_and_hold_child)
        assert ready.wait(timeout=10)
        b=pool.submit(reparent)
        assert pidready.wait(timeout=10)
        try:
            _wait_for_observed_postgres_lock(state['pid'])
        finally:
            release.set()
        a.result(timeout=12)
        assert b.result(timeout=12)=='REJECTED'
    assert CaseAssignment.objects.get(case=case,role='IT').member_id==it.pk
    assert OnboardingCase.objects.get(pk=case.pk).organization_id==org.pk


@pytest.mark.django_db(transaction=True)
def test_r3_legacy_assignment_member_mismatch_rejected_by_preflight(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    migration=importlib.import_module('backend.onboarding.migrations.0004_immutable_roots_and_issuer_guard')
    foreign=Organization.objects.create(name='Old unrelated org')
    different=User.objects.create_user(email='malformedforeign@example.test',password='StrongPassword!2026')
    foreign_hr=Membership.objects.create(user=different,organization=foreign,role='HR')
    assignment=CaseAssignment.objects.get(case=case,role='HR')
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE public.onboarding_caseassignment DISABLE TRIGGER m1_assignment_links')
            cursor.execute('UPDATE public.onboarding_caseassignment SET member_id=%s WHERE id=%s',
                           [foreign_hr.pk,assignment.pk])
        with pytest.raises(DatabaseError) as failure:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(migration.PREFLIGHT_SQL)
        assert getattr(failure.value.__cause__,'sqlstate',None)=='23514'
        assert 'M1 migration blocked: invalid legacy assignment/issuer relationship' in str(failure.value)
        transaction.set_rollback(True)
    assignment.refresh_from_db()
    assert assignment.member_id==hr.pk

@pytest.mark.django_db(transaction=True)
def test_r3_legacy_assignment_role_mismatch_rejected_by_preflight(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    migration=importlib.import_module('backend.onboarding.migrations.0004_immutable_roots_and_issuer_guard')
    it_user=User.objects.create_user(email='malformedit@example.test',password='StrongPassword!2026')
    it=Membership.objects.create(user=it_user,organization=org,role='IT')
    assignment=CaseAssignment.objects.get(case=case,role='HR')
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE public.onboarding_caseassignment DISABLE TRIGGER m1_assignment_links')
            cursor.execute('UPDATE public.onboarding_caseassignment SET member_id=%s WHERE id=%s',
                           [it.pk,assignment.pk])
        with pytest.raises(DatabaseError) as failure:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(migration.PREFLIGHT_SQL)
        assert getattr(failure.value.__cause__,'sqlstate',None)=='23514'
        assert 'M1 migration blocked: invalid legacy assignment/issuer relationship' in str(failure.value)
        transaction.set_rollback(True)
    assignment.refresh_from_db()
    assert assignment.member_id==hr.pk

@pytest.mark.django_db(transaction=True)
def test_r3_migration_preflight_accepts_valid_nonempty_fixture(case_context):
    import importlib
    migration=importlib.import_module('backend.onboarding.migrations.0004_immutable_roots_and_issuer_guard')
    org,employee_user,employee,case,hr_user,hr=case_context
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(migration.PREFLIGHT_SQL)
        transaction.set_rollback(True)
    assert OnboardingCase.objects.filter(pk=case.pk,organization=org).exists()

@pytest.mark.django_db(transaction=True)
def test_c4_receipt_replays_after_candidate_deactivation_and_later_reassignment(case_context):
    org,employee_user,employee,case,hr_user,hr=case_context
    old_user=User.objects.create_user(email='c4old@example.test',password='StrongPassword!2026')
    old=Membership.objects.create(user=old_user,organization=org,role='IT')
    CaseAssignment.objects.create(case=case,member=old,role='IT',effective_from=timezone.now())
    target_user=User.objects.create_user(email='c4target@example.test',password='StrongPassword!2026')
    target=Membership.objects.create(user=target_user,organization=org,role='IT')
    second_user=User.objects.create_user(email='c4second@example.test',password='StrongPassword!2026')
    second=Membership.objects.create(user=second_user,organization=org,role='IT')
    args=dict(actor=hr_user,case_id=case.pk,role='IT',new_member_id=target.pk,
              reason='Primary change',key=uuid.uuid4(),expected_version=1)
    first=reassign_owner(**args)
    target_user.is_active=False
    target_user.save(update_fields=['is_active'])
    target.available=False
    target.active=False
    target.save(update_fields=['available','active'])
    assert reassign_owner(**args)==first
    followup=reassign_owner(actor=hr_user,case_id=case.pk,role='IT',
        new_member_id=second.pk,reason='Replacement',key=uuid.uuid4(),expected_version=2)
    assert followup[1]==200
    assert reassign_owner(**args)==first
    assert OnboardingCase.objects.get(pk=case.pk).version==3
    assert AuditEvent.objects.filter(event_type='OWNER_REASSIGNED').count()==2
    assert CommandReceipt.objects.count()==2
    with pytest.raises(CommandFailure) as denied_new:
        reassign_owner(actor=hr_user,case_id=case.pk,role='IT',new_member_id=target.pk,
            reason='Invalid new assignment',key=uuid.uuid4(),expected_version=3)
    assert denied_new.value.code=='INVALID_ASSIGNEE'
    hr.active=False
    hr.save(update_fields=['active'])
    with pytest.raises(CommandFailure) as denied_old_actor:
        reassign_owner(**args)
    assert denied_old_actor.value.status==404
    assert AuditEvent.objects.filter(event_type='OWNER_REASSIGNED').count()==2

@pytest.mark.django_db(transaction=True)
def test_c6_post_commit_password_session_failure_reports_committed(case_context):
    from backend.accounts.security import issue_token
    from backend.accounts.models import OneTimeToken
    org,employee_user,employee,case,hr_user,hr=case_context
    token=issue_token(hr_user,'RESET')
    client=Client(enforce_csrf_checks=True)
    csrf=client.get('/api/v1/auth/csrf').json()['csrf_token']
    login=client.post('/api/v1/auth/login',json.dumps({
        'email':hr_user.email,'password':'StrongSecretPassword!2026'}),
        content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert login.status_code==200,login.content
    csrf=client.get('/api/v1/auth/csrf').json()['csrf_token']
    class PostCommitAbort(OperationalError):
        sqlstate='57014'
    with patch('backend.accounts.views.update_session_auth_hash',
               side_effect=PostCommitAbort('synthetic session rotation failure')):
        response=client.post('/api/v1/auth/password/change',json.dumps({
            'old_password':'StrongSecretPassword!2026',
            'new_password':'AfterCommittedChange!2026'}),
            content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code==503,response.content
    assert response.json()['error']['outcome']=='COMMAND_COMMITTED'
    hr_user.refresh_from_db()
    assert hr_user.check_password('AfterCommittedChange!2026')
    assert not hr_user.check_password('StrongSecretPassword!2026')
    assert OneTimeToken.objects.filter(user=hr_user,used_at__isnull=True).count()==0
    assert AuditEvent.objects.filter(event_type='PASSWORD_CHANGED').count()==1
    assert AuditEvent.objects.count()==1
    assert OneTimeToken.objects.filter(user=hr_user).count()==1

@pytest.mark.django_db(transaction=True)
def test_c6_credential_rollback_and_logout_mutation_outcome(case_context):
    from backend.accounts.security import issue_token
    from backend.accounts.models import OneTimeToken
    org,employee_user,employee,case,hr_user,hr=case_context
    token=issue_token(hr_user,'RESET')
    client=Client(enforce_csrf_checks=True)
    csrf=client.get('/api/v1/auth/csrf').json()['csrf_token']
    login=client.post('/api/v1/auth/login',json.dumps({
        'email':hr_user.email,'password':'StrongSecretPassword!2026'}),
        content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert login.status_code==200,login.content
    csrf=client.get('/api/v1/auth/csrf').json()['csrf_token']
    class KnownAbort(OperationalError):
        sqlstate='57014'
    with patch('backend.accounts.views.append_event',side_effect=KnownAbort('forced audit abort')):
        denied=client.post('/api/v1/auth/password/change',json.dumps({
            'old_password':'StrongSecretPassword!2026',
            'new_password':'MustNotCommit!2026'}),
            content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert denied.status_code==409,denied.content
    assert denied.json()['error']['outcome']=='ROLLED_BACK'
    hr_user.refresh_from_db()
    assert hr_user.check_password('StrongSecretPassword!2026')
    assert OneTimeToken.objects.filter(user=hr_user,used_at__isnull=True).count()==1
    assert AuditEvent.objects.count()==0
    with patch('backend.accounts.views.logout',side_effect=KnownAbort('logout deletion uncertain')):
        uncertain=client.post('/api/v1/auth/logout','{}',content_type='application/json',
                              HTTP_X_CSRFTOKEN=csrf)
    assert uncertain.status_code==503,uncertain.content
    assert uncertain.json()['error']['outcome']=='UNKNOWN'
