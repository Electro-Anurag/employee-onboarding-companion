"""Adversarial source-review regression: R2/R3/R7/R8 and malformed inputs."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from django.db import connection, transaction, IntegrityError, DatabaseError, close_old_connections
from django.test import Client
from django.utils import timezone
from backend.accounts.models import Organization,Membership,User
from backend.onboarding.models import OnboardingCase,CaseAssignment
from backend.onboarding.services import reassign_owner,issue_credential_for_case,CommandFailure
from backend.audit.models import AuditEvent,CommandReceipt
from backend.accounts.security import digest_token

@pytest.fixture
def setup(db):
    o=Organization.objects.create(name='M1 review org')
    people={}
    for role in ['EMPLOYEE','HR','IT','MANAGER']:
        user=User.objects.create_user(email=f'{role.lower()}@cases.test',
                    password='AReallyStrongPassword!2026',display_name=role)
        member=Membership.objects.create(user=user,organization=o,role=role,can_coordinate_ownership=(role=='HR'))
        people[role]=(user,member)
    case=OnboardingCase.objects.create(organization=o,employee=people['EMPLOYEE'][1],joining_date=timezone.localdate())
    for role in ['HR','IT','MANAGER']:
        CaseAssignment.objects.create(case=case,role=role,member=people[role][1],effective_from=timezone.now())
    return case,people,o

@pytest.mark.django_db(transaction=True)
def test_r3_invalid_cross_org_links_rejected_at_database(setup):
    case,people,org=setup
    foreign_org=Organization.objects.create(name='Other')
    foreign_user=User.objects.create_user(email='foreign@cases.test',password='AReallyStrongPassword!2026')
    foreign_emp=Membership.objects.create(user=foreign_user,organization=foreign_org,role='EMPLOYEE')
    foreign_hr_user=User.objects.create_user(email='hr.other@cases.test',password='AReallyStrongPassword!2026')
    foreign_hr=Membership.objects.create(user=foreign_hr_user,organization=foreign_org,role='HR')
    with pytest.raises((IntegrityError,DatabaseError)):
        with transaction.atomic():
            OnboardingCase.objects.create(organization=org,employee=foreign_emp,joining_date=timezone.localdate())
    with pytest.raises((IntegrityError,DatabaseError)):
        with transaction.atomic():
            CaseAssignment.objects.create(case=case,role='HR',member=foreign_hr,effective_from=timezone.now())
    with pytest.raises((IntegrityError,DatabaseError)):
        with transaction.atomic():
            CaseAssignment.objects.create(case=case,role='MANAGER',member=people['IT'][1],effective_from=timezone.now())
    with pytest.raises((IntegrityError,DatabaseError)):
        with transaction.atomic():
            CaseAssignment.objects.create(case=case,role='IT',member=people['IT'][1],
                                          effective_from=timezone.now()+timezone.timedelta(days=1))
    with pytest.raises((IntegrityError,DatabaseError)):
        with transaction.atomic():
            Membership.objects.filter(pk=people['IT'][1].pk).update(organization=foreign_org)

@pytest.mark.django_db(transaction=True)
def test_r7_audit_ids_resolve_to_actual_assignment_rows(setup):
    case,people,org=setup
    other=User.objects.create_user(email='otherit@cases.test',password='AReallyStrongPassword!2026')
    new=Membership.objects.create(user=other,organization=org,role='IT')
    old_assignment=CaseAssignment.objects.get(case=case,role='IT',effective_to__isnull=True)
    result,status=reassign_owner(actor=people['HR'][0],case_id=case.pk,role='IT',
         new_member_id=new.pk,reason='Team rotation',key=uuid.uuid4(),expected_version=1)
    assert status==200
    audit=AuditEvent.objects.get(event_type='OWNER_REASSIGNED')
    before=CaseAssignment.objects.get(pk=audit.sanitized_change['previous_assignment_id'])
    after=CaseAssignment.objects.get(pk=audit.sanitized_change['new_assignment_id'])
    assert before.pk==old_assignment.pk and before.member_id==people['IT'][1].pk
    assert after.member_id==new.pk and after.case_id==case.pk
    assert audit.sanitized_change['new_member_id']==str(new.pk)
    assert result['case_version']==audit.sanitized_change['case_version']==2

@pytest.mark.django_db(transaction=True)
def test_r2_replaced_hr_cannot_issue_token(setup):
    case,people,org=setup
    replacement_user=User.objects.create_user(email='newhr@cases.test',password='AReallyStrongPassword!2026')
    replacement=Membership.objects.create(user=replacement_user,organization=org,role='HR')
    reassign_owner(actor=people['HR'][0],case_id=case.pk,role='HR',new_member_id=replacement.pk,
                   reason='HR coverage',key=uuid.uuid4(),expected_version=1)
    with pytest.raises(CommandFailure):
        issue_credential_for_case(actor=people['HR'][0],case_id=case.pk,purpose='RESET')
    raw=issue_credential_for_case(actor=replacement_user,case_id=case.pk,purpose='RESET')
    assert len(raw)>30
    assert AuditEvent.objects.filter(event_type='RESET_ISSUED').count()==1

@pytest.mark.django_db(transaction=True)
def test_r2_user_and_membership_revocation_prevent_issuance(setup):
    case,people,org=setup
    user,member=people['HR']
    member.active=False;member.save(update_fields=['active'])
    with pytest.raises(Exception):
        issue_credential_for_case(actor=user,case_id=case.pk,purpose='RESET')
    assert AuditEvent.objects.count()==0
    member.active=True;member.save(update_fields=['active'])
    user.is_active=False;user.save(update_fields=['is_active'])
    with pytest.raises(Exception):
        issue_credential_for_case(actor=user,case_id=case.pk,purpose='RESET')
    assert AuditEvent.objects.count()==0

@pytest.mark.django_db(transaction=True)
def test_r8_held_case_lock_returns_bounded_conflict_without_mutation(setup):
    case,people,org=setup
    other=User.objects.create_user(email='backupit@cases.test',password='AReallyStrongPassword!2026')
    new=Membership.objects.create(user=other,organization=org,role='IT')
    owner,member=people['HR']
    locked=Event();release=Event()
    def hold_lock():
        close_old_connections()
        try:
            with transaction.atomic():
                OnboardingCase.objects.select_for_update().get(pk=case.pk)
                locked.set()
                assert release.wait(timeout=14)
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(hold_lock)
        assert locked.wait(timeout=10)
        c=Client(enforce_csrf_checks=True)
        csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
        login=c.post('/api/v1/auth/login',
                  json.dumps({'email':owner.email,'password':'AReallyStrongPassword!2026'}),
                  content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
        assert login.status_code==200
        csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
        response=c.post(f'/api/v1/cases/{case.pk}/assignments',
                 json.dumps({'role':'IT','new_member_id':str(new.pk),'reason':'Blocked while locked'}),
                 content_type='application/json',HTTP_X_CSRFTOKEN=csrf,
                 HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH=f'"case:{case.pk}:v1"')
        release.set()
        future.result(timeout=12)
    assert response.status_code==409,response.content
    assert response.json()['error']['code']=='TRANSIENT_DATABASE_CONFLICT'
    assert OnboardingCase.objects.get(pk=case.pk).version==1
    assert CommandReceipt.objects.count()==0
    assert AuditEvent.objects.count()==0

@pytest.mark.django_db(transaction=True)
def test_n1_malformed_uuid_types_return_bounded_error(setup):
    case,people,org=setup
    client=Client(enforce_csrf_checks=True)
    csrf=client.get('/api/v1/auth/csrf').json()['csrf_token']
    login=client.post('/api/v1/auth/login',
              json.dumps({'email':people['HR'][0].email,'password':'AReallyStrongPassword!2026'}),
              content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
    assert login.status_code==200
    csrf=client.get('/api/v1/auth/csrf').json()['csrf_token']
    for value in (23,None,[],{'abc':1}):
        response=client.post('/api/v1/auth/password-reset-tokens',
             json.dumps({'case_id':value}),content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
        assert response.status_code==422,response.content
        response=client.post(f'/api/v1/cases/{case.pk}/assignments',
             json.dumps({'role':'IT','new_member_id':value,'reason':'Any'}),
             content_type='application/json',HTTP_X_CSRFTOKEN=csrf,
             HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH=f'"case:{case.pk}:v1"')
        assert response.status_code==422,response.content
    assert AuditEvent.objects.count()==0


@pytest.mark.django_db(transaction=True)
def test_r3_member_identity_cannot_be_transferred_under_a_case(setup):
    case,people,org=setup
    replacement=User.objects.create_user(email='identitytransfer@cases.test',
                        password='AReallyStrongPassword!2026')
    membership=people['IT'][1]
    with pytest.raises((IntegrityError,DatabaseError)):
        with transaction.atomic():
            Membership.objects.filter(pk=membership.pk).update(user=replacement)
    membership.refresh_from_db()
    assert membership.user_id==people['IT'][0].pk
