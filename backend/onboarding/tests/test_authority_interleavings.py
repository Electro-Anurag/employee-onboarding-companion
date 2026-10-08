"""Deterministic two-connection interleavings for M1 authority/replay boundaries."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event,Barrier
import time
import uuid
import pytest
from django.db import transaction,close_old_connections
from django.utils import timezone
from backend.accounts.models import User,Membership,Organization,OneTimeToken
from backend.onboarding.models import OnboardingCase,CaseAssignment
from backend.onboarding.services import issue_credential_for_case,reassign_owner,CommandFailure
from backend.audit.models import AuditEvent,CommandReceipt

@pytest.fixture
def rows(db):
    org=Organization.objects.create(name='Review concurrency')
    owner=User.objects.create_user(email='hr@interleave.test',password='SecurePassword!2026')
    hr=Membership.objects.create(user=owner,organization=org,role='HR',can_coordinate_ownership=True)
    employee_user=User.objects.create_user(email='employee@interleave.test',password='SecurePassword!2026')
    employee=Membership.objects.create(user=employee_user,organization=org,role='EMPLOYEE')
    case=OnboardingCase.objects.create(organization=org,employee=employee,joining_date=timezone.localdate())
    CaseAssignment.objects.create(case=case,role='HR',member=hr,effective_from=timezone.now())
    return org,owner,hr,employee_user,employee,case

@pytest.mark.django_db(transaction=True)
def test_r2_reassigned_hr_cannot_issue_after_prior_commit(rows):
    org,actor,hr,employee_user,employee,case=rows
    replacement_user=User.objects.create_user(email='replacement@interleave.test',password='SecurePassword!2026')
    replacement=Membership.objects.create(user=replacement_user,organization=org,role='HR')
    owner_ready=Event();owner_release=Event()
    def replace():
        close_old_connections()
        try:
            with transaction.atomic():
                reassign_owner(actor=actor,case_id=case.pk,role='HR',
                    new_member_id=replacement.pk,reason='Revocation',key=uuid.uuid4(),expected_version=1)
                owner_ready.set()
                assert owner_release.wait(timeout=12)
        finally: close_old_connections()
    def attempt():
        close_old_connections()
        try:
            try: return issue_credential_for_case(actor=actor,case_id=case.pk,purpose='RESET')
            except CommandFailure as e: return e.code
        finally: close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(replace)
        assert owner_ready.wait(timeout=12)
        b=pool.submit(attempt)
        # Keep case locked long enough to reach the contender's transaction.
        time.sleep(.10)
        owner_release.set()
        a.result(timeout=12)
        result=b.result(timeout=12)
    assert result=='NOT_FOUND',result
    assert OneTimeToken.objects.count()==0
    assert AuditEvent.objects.filter(event_type='RESET_ISSUED').count()==0

@pytest.mark.django_db(transaction=True)
def test_r2_employee_revocation_precedes_credential_issue(rows):
    org,actor,hr,employee_user,employee,case=rows
    target_ready=Event();target_release=Event()
    def revoke():
        close_old_connections()
        try:
            with transaction.atomic():
                locked=Membership.objects.select_for_update().get(pk=employee.pk)
                locked.active=False;locked.save(update_fields=['active'])
                target_ready.set()
                assert target_release.wait(timeout=12)
        finally: close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(revoke)
        assert target_ready.wait(timeout=12)
        b=pool.submit(issue_credential_for_case,actor=actor,case_id=case.pk,purpose='RESET')
        time.sleep(.10)
        target_release.set()
        a.result(timeout=12)
        with pytest.raises(CommandFailure) as failure: b.result(timeout=12)
        assert failure.value.status==404
    assert OneTimeToken.objects.count()==0

@pytest.mark.django_db(transaction=True)
def test_r8_same_idempotency_key_across_cases_never_unhandled_db_error(rows):
    org,actor,hr,employee_user,employee,case=rows
    other_user=User.objects.create_user(email='another@interleave.test',password='SecurePassword!2026')
    other_employee=Membership.objects.create(user=other_user,organization=org,role='EMPLOYEE')
    other_case=OnboardingCase.objects.create(organization=org,employee=other_employee,joining_date=timezone.localdate())
    CaseAssignment.objects.create(case=other_case,role='HR',member=hr,effective_from=timezone.now())
    current_it_user=User.objects.create_user(email='it@interleave.test',password='SecurePassword!2026')
    current_it=Membership.objects.create(user=current_it_user,organization=org,role='IT')
    new_it_user=User.objects.create_user(email='newit@interleave.test',password='SecurePassword!2026')
    new_it=Membership.objects.create(user=new_it_user,organization=org,role='IT')
    for c in (case,other_case):
        CaseAssignment.objects.create(case=c,role='IT',member=current_it,effective_from=timezone.now())
    shared=uuid.uuid4();barrier=Barrier(2)
    def execute(target_case):
        close_old_connections()
        try:
            barrier.wait(timeout=12)
            try:
                return ('ok',reassign_owner(actor=actor,case_id=target_case.pk,role='IT',
                   new_member_id=new_it.pk,reason='Shared request key',key=shared,expected_version=1)[1])
            except CommandFailure as error:
                return ('rejected',error.code)
        finally: close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(execute,case);b=pool.submit(execute,other_case)
        outcome=[a.result(timeout=20),b.result(timeout=20)]
    assert sorted(outcome)==[('ok',200),('rejected','IDEMPOTENCY_KEY_REUSED')]
    assert CommandReceipt.objects.filter(actor=actor,idempotency_key=shared).count()==1
    assert AuditEvent.objects.filter(event_type='OWNER_REASSIGNED').count()==1
