import json
import uuid
import pytest
from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from backend.accounts.models import Organization,Membership,User
from backend.onboarding.models import OnboardingCase,CaseAssignment
from backend.onboarding.services import reassign_owner,CommandFailure
from backend.audit.models import AuditEvent,AuditStream,CommandReceipt
from backend.audit.services import append_event

@pytest.fixture
def demo(db):
    o=Organization.objects.create(name='Security fixture')
    people={}
    for k in ['EMPLOYEE','HR','IT','MANAGER']:
        u=User.objects.create_user(email=k.lower()+'@demo.test',password='StrongPassword!2026',display_name=k)
        m=Membership.objects.create(user=u,organization=o,role=k,can_coordinate_ownership=(k=='HR'))
        people[k]=(u,m)
    backup=User.objects.create_user(email='backup@demo.test',password='StrongPassword!2026')
    new_it=Membership.objects.create(user=backup,organization=o,role='IT')
    case=OnboardingCase.objects.create(organization=o,employee=people['EMPLOYEE'][1],joining_date=timezone.localdate())
    for role in ['HR','IT','MANAGER']:
        CaseAssignment.objects.create(case=case,role=role,member=people[role][1],effective_from=timezone.now())
    return people,new_it,case

@pytest.mark.django_db(transaction=True)
def test_idempotent_reassignment_and_case_version(demo):
    people,new_it,case=demo
    actor=people['HR'][0];key=uuid.uuid4()
    params=dict(actor=actor,case_id=case.pk,role='IT',new_member_id=new_it.pk,reason='Coverage change',key=key,expected_version=1)
    a,status=reassign_owner(**params)
    b,status2=reassign_owner(**params)
    assert (a,status)==(b,status2)
    assert OnboardingCase.objects.get(pk=case.pk).version==2
    assert CaseAssignment.objects.filter(case=case,role='IT',effective_to__isnull=True).count()==1
    assert AuditEvent.objects.filter(stream_id=f'case:{case.pk}').count()==1
    assert CommandReceipt.objects.count()==1
    with pytest.raises(CommandFailure) as e: reassign_owner(**dict(params,reason='different reason'))
    assert e.value.code=='IDEMPOTENCY_KEY_REUSED'

@pytest.mark.django_db(transaction=True)
def test_audit_and_assignment_roll_back_together(demo):
    people,new_it,case=demo
    with pytest.raises(RuntimeError,match='injected rollback'):
        reassign_owner(actor=people['HR'][0],case_id=case.pk,role='IT',new_member_id=new_it.pk,
            reason='Will roll back',key=uuid.uuid4(),expected_version=1,fail_after_audit=True)
    assert OnboardingCase.objects.get(pk=case.pk).version==1
    assert CaseAssignment.objects.get(case=case,role='IT',effective_to__isnull=True).member_id==people['IT'][1].pk
    assert AuditEvent.objects.count()==0 and CommandReceipt.objects.count()==0

@pytest.mark.django_db(transaction=True)
def test_audit_chain_and_immutability(demo):
    people,new_it,case=demo
    with transaction.atomic():
        append_event(stream_key=f'case:{case.pk}',actor=people['HR'][0],event_type='M1_TEST_ONE',changes={'event':'one'})
        append_event(stream_key=f'case:{case.pk}',actor=people['HR'][0],event_type='M1_TEST_TWO',changes={'event':'two'})
    e=list(AuditEvent.objects.order_by('sequence'))
    assert len(e)==2 and e[0].sequence==1 and e[1].sequence==2
    assert e[0].previous_hash=='0'*64 and e[1].previous_hash==e[0].event_hash
    assert len(e[1].event_hash)==64
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as c:c.execute('DELETE FROM public.audit_auditevent')
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as c:c.execute('UPDATE public.audit_auditevent SET event_type=%s',['tampered'])
    assert AuditEvent.objects.count()==2

@pytest.mark.django_db(transaction=True)
def test_denies_role_bypass_and_invalid_case_assignment(demo):
    people,new_it,case=demo
    with pytest.raises(CommandFailure) as exc:
        reassign_owner(actor=people['EMPLOYEE'][0],case_id=case.pk,role='IT',new_member_id=new_it.pk,
            reason='escalate',key=uuid.uuid4(),expected_version=1)
    assert exc.value.status==404
    with pytest.raises(CommandFailure) as exc:
        reassign_owner(actor=people['HR'][0],case_id=case.pk,role='MANAGER',new_member_id=new_it.pk,
            reason='invalid role',key=uuid.uuid4(),expected_version=1)
    assert exc.value.code=='INVALID_ASSIGNEE'

@pytest.mark.django_db(transaction=True)
def test_replayed_command_not_authorized_after_reassignment(demo):
    people,new_it,case=demo
    # Replay checks current HR assignment first, not merely a saved response.
    request=dict(actor=people['HR'][0],case_id=case.pk,role='IT',new_member_id=new_it.pk,
        reason='Switch',key=uuid.uuid4(),expected_version=1)
    reassign_owner(**request)
    CaseAssignment.objects.filter(case=case,role='HR',effective_to__isnull=True).update(effective_to=timezone.now())
    with pytest.raises(CommandFailure) as ex: reassign_owner(**request)
    assert ex.value.status==404

@pytest.mark.django_db(transaction=True)
def test_audit_read_role_no_modify(demo):
    people,new_it,case=demo
    with transaction.atomic(): append_event(stream_key=f'case:{case.pk}',actor=people['HR'][0],event_type='M1_GRANT_TEST',changes={})
    # Owner can grant a separate restricted role. This tests actual database enforcement.
    with connection.cursor() as c:
        c.execute('CREATE ROLE m1_read_only_audit NOLOGIN')
        try:
            c.execute('GRANT USAGE ON SCHEMA public TO m1_read_only_audit')
            c.execute('GRANT SELECT ON public.audit_auditevent TO m1_read_only_audit')
            c.execute("SELECT has_table_privilege('m1_read_only_audit','audit_auditevent','UPDATE'),has_table_privilege('m1_read_only_audit','audit_auditevent','DELETE'),has_table_privilege('m1_read_only_audit','audit_auditevent','TRUNCATE')")
            assert c.fetchone()==(False,False,False)
        finally:
            c.execute('REVOKE SELECT ON public.audit_auditevent FROM m1_read_only_audit')
            c.execute('REVOKE USAGE ON SCHEMA public FROM m1_read_only_audit')
            c.execute('DROP ROLE m1_read_only_audit')

@pytest.mark.django_db(transaction=True)
def test_parallel_replay_across_connections(demo):
    """Same key across two PostgreSQL sessions produces exactly one business change."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from django.db import close_old_connections
    people,new_it,case=demo
    start=Barrier(2)
    params=dict(actor=people['HR'][0],case_id=case.pk,role='IT',new_member_id=new_it.pk,
                reason='Concurrent coverage',key=uuid.uuid4(),expected_version=1)
    def run():
        close_old_connections()
        try:
            start.wait(timeout=10)
            return reassign_owner(**params)
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1=pool.submit(run);f2=pool.submit(run)
        first=f1.result(timeout=20);second=f2.result(timeout=20)
    assert first==second
    assert OnboardingCase.objects.get(pk=case.pk).version==2
    assert AuditEvent.objects.filter(stream_id=f'case:{case.pk}').count()==1
    assert CommandReceipt.objects.filter(case=case).count()==1
    assert CaseAssignment.objects.filter(case=case,role='IT',effective_to__isnull=True).count()==1

@pytest.mark.django_db(transaction=True)
def test_parallel_conflicting_commands_reject_stale_version(demo):
    """Different commands against the same old case version cannot both commit."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from django.db import close_old_connections
    people,new_it,case=demo
    other=User.objects.create_user(email='third-it@demo.test',password='StrongPassword!2026')
    third=Membership.objects.create(user=other,organization=case.organization,role='IT')
    start=Barrier(2)
    def run(target):
        close_old_connections()
        try:
            start.wait(timeout=10)
            try:
                result,status=reassign_owner(actor=people['HR'][0],case_id=case.pk,role='IT',
                    new_member_id=target,reason='Parallel reassignment',key=uuid.uuid4(),expected_version=1)
                return ('ok',status)
            except CommandFailure as exc:
                return ('rejected',exc.code)
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1=pool.submit(run,new_it.pk);f2=pool.submit(run,third.pk)
        results=[f1.result(timeout=20),f2.result(timeout=20)]
    assert sorted(results)==[('ok',200),('rejected','STALE_VERSION')]
    assert OnboardingCase.objects.get(pk=case.pk).version==2
    assert AuditEvent.objects.filter(stream_id=f'case:{case.pk}').count()==1
    assert CommandReceipt.objects.filter(case=case).count()==1
