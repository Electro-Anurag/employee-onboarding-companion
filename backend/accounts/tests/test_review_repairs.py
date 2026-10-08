"""Regression tests for Astra M1 R1/R4/R5/R6 and credential authority boundaries."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json
import uuid
import pytest
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client
from backend.accounts.models import Membership,Organization,OneTimeToken,User
from backend.accounts.security import issue_token,redeem_token,change_password_locked,admit_attempt,actor_context,InvalidActor

@pytest.fixture
def identity(db):
    org=Organization.objects.create(name='R1 review demo')
    u=User.objects.create_user(email='case@review.test',password='PasswordBefore!2026',display_name='Case employee')
    m=Membership.objects.create(organization=org,user=u,role='EMPLOYEE')
    return u,m,org

@pytest.mark.django_db(transaction=True)
def test_r1_cross_purpose_tokens_revoked_on_reset_and_password_change(identity):
    user,member,org=identity
    user.set_unusable_password();user.save(update_fields=['password'])
    invite=issue_token(user,OneTimeToken.INVITE)
    reset=issue_token(user,OneTimeToken.RESET)
    redeem_token(reset,OneTimeToken.RESET,'PasswordAfterReset!2026')
    with pytest.raises(InvalidActor):
        redeem_token(invite,OneTimeToken.INVITE,'StolenToken!2026')
    assert OneTimeToken.objects.filter(user=user,used_at__isnull=True).count()==0
    after=issue_token(user,OneTimeToken.RESET)
    changed=change_password_locked(user,'PasswordAfterReset!2026','PasswordChangedAgain!2026')
    assert changed.check_password('PasswordChangedAgain!2026')
    with pytest.raises(InvalidActor):
        redeem_token(after,OneTimeToken.RESET,'StolenToken!2026')
    fresh=issue_token(changed,OneTimeToken.RESET)
    assert redeem_token(fresh,OneTimeToken.RESET,'FinalSecurePassword!2026').check_password('FinalSecurePassword!2026')

@pytest.mark.django_db(transaction=True)
def test_r4_issuance_same_user_across_real_connections(identity):
    user,_,_=identity
    start=Barrier(2)
    def run():
        close_old_connections()
        try:
            start.wait(timeout=10)
            return issue_token(user,OneTimeToken.RESET)
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(run);b=pool.submit(run)
        raw=[a.result(timeout=15),b.result(timeout=15)]
    pending=list(OneTimeToken.objects.filter(user=user,purpose='RESET',used_at__isnull=True))
    assert len(pending)==1
    from backend.accounts.security import digest_token
    assert pending[0].token_hash in [digest_token(t) for t in raw]
    assert OneTimeToken.objects.filter(user=user,purpose='RESET').count()==2

@pytest.mark.django_db(transaction=True)
def test_r5_simultaneous_admission_never_exceeds_account_limit(identity):
    start=Barrier(9)
    def run():
        close_old_connections()
        try:
            start.wait(timeout=15)
            return admit_attempt('login','case@review.test','203.0.113.11')
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=9) as pool:
        results=[x.result(timeout=25) for x in [pool.submit(run) for _ in range(9)]]
    assert sum(results)==5
    assert not admit_attempt('login','case@review.test','203.0.113.12')
    assert admit_attempt('login','different@review.test','203.0.113.12')

@pytest.mark.django_db(transaction=True)
def test_r5_redemption_attempts_ip_budget(identity):
    for k in range(10):
        assert admit_attempt('redeem',str(uuid.uuid4()),'198.51.100.21')
    assert not admit_attempt('redeem',str(uuid.uuid4()),'198.51.100.21')
    assert admit_attempt('redeem',str(uuid.uuid4()),'198.51.100.22')
    token=str(uuid.uuid4())
    for _ in range(5):
        assert admit_attempt('redeem',token,'198.51.100.23')
    assert not admit_attempt('redeem',token,'198.51.100.24')

@pytest.mark.django_db(transaction=True)
def test_r6_second_active_membership_fails_database(identity):
    user,member,org=identity
    other=Organization.objects.create(name='Second org')
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Membership.objects.create(user=user,organization=other,role='HR')
    member.active=False;member.save(update_fields=['active'])
    second=Membership.objects.create(user=user,organization=other,role='HR')
    assert actor_context(user).pk==second.pk
    second.active=False;second.save(update_fields=['active'])
    with pytest.raises(InvalidActor):
        actor_context(user)

@pytest.mark.django_db(transaction=True)
def test_r1_old_password_checked_after_credential_lock(identity):
    from threading import Event
    user,_,_=identity
    acquired=Event();release=Event()
    def reset_first():
        close_old_connections()
        try:
            with transaction.atomic():
                locked=User.objects.select_for_update().get(pk=user.pk)
                acquired.set()
                assert release.wait(timeout=12)
                locked.set_password('ResetWinsPassword!2026')
                locked.save(update_fields=['password'])
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(reset_first)
        assert acquired.wait(timeout=10)
        # A stale pre-lock password check would incorrectly accept the old password.
        import threading
        outcome={}
        def change():
            close_old_connections()
            try:
                try: change_password_locked(user,'PasswordBefore!2026','WrongOverwrite!2026')
                except InvalidActor: outcome['rejected']=True
            finally: close_old_connections()
        t=threading.Thread(target=change);t.start()
        release.set()
        t.join(timeout=15)
        future.result(timeout=15)
    assert outcome.get('rejected') is True
    user.refresh_from_db()
    assert user.check_password('ResetWinsPassword!2026')

@pytest.mark.django_db(transaction=True)
def test_r1_prior_session_invalid_after_reset(identity):
    user,member,org=identity
    client=Client(enforce_csrf_checks=True)
    csrf=client.get('/api/v1/auth/csrf').json()['csrf_token']
    response=client.post('/api/v1/auth/login',json.dumps({'email':user.email,'password':'PasswordBefore!2026'}),
                         content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code==200
    assert client.get('/api/v1/auth/me').status_code==200
    raw=issue_token(user,'RESET')
    redeem_token(raw,'RESET','AfterSessionReset!2026')
    assert client.get('/api/v1/auth/me').status_code==401
