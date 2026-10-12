"""CI-only populated 0018 -> 0019/0020 and already-applied-old-0019 qualification.

Uses throwaway PostgreSQL databases prefixed ci_m4_upgrade_. Never runs on
production/normal app data and never repairs historical evidence silently.
"""
import os
import uuid
from datetime import timedelta

db=os.environ.get('POSTGRES_DB','')
scenario=os.environ.get('M4_MANAGER_UPGRADE_SCENARIO','')
if not db.startswith('ci_m4_upgrade_') or scenario not in (
        'matching','mismatched','legacy_matching','legacy_mismatched'):
    raise SystemExit('Refusing to run outside explicit isolated CI upgrade database')

os.environ.setdefault('DJANGO_SETTINGS_MODULE','backend.config.settings')
import django
django.setup()

from importlib import import_module
from django.core.management import call_command
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.executor import MigrationExecutor
from django.db import connection,transaction
from django.utils import timezone
from backend.accounts.models import Organization,Membership,User
from backend.templates.services import create_default,publish_template
from backend.templates.models import TemplateTask
from backend.onboarding.state_machine import scheduled_at
from backend.onboarding.models import OnboardingCase,Task,ManagerAttestation,TaskCompletion

# Intentionally stop before the additive provenance migration.
call_command('migrate','onboarding','0018',interactive=False,verbosity=0)
# An earlier onboarding migration does not depend on later (unchanged)
# template-schema additions. Bring that app to its leaf before using the
# current model-based synthetic fixture; leave onboarding explicitly at 0018.
call_command('migrate','templates',interactive=False,verbosity=0)
# The currently used template/case commands depend on the audit append
# function, which is in audit 0002 but not in the 0018 dependency closure.
call_command('migrate','audit',interactive=False,verbosity=0)
org=Organization.objects.create(name='Disposable M4 Manager Upgrade Evidence',timezone='UTC')
users={}
members={}
for role in ('HR','EMPLOYEE','IT','MANAGER'):
    actor=User.objects.create_user(email=role.lower()+'@m4-upgrade.invalid',
        password='CI-onlySyntheticCredential!2026',display_name='Synthetic '+role)
    member=Membership.objects.create(user=actor,organization=org,role=role,
        can_manage_templates=(role=='HR'),can_coordinate_ownership=(role=='HR'))
    users[role],members[role]=actor,member
draft=create_default(actor=users['HR'])
published=publish_template(actor=users['HR'],template_id=uuid.UUID(draft['id']),revision=1)
# A database frozen at 0018 MUST be populated with the historical model.
# Current create_case() and current OnboardingCase ORM include schedule_revision,
# introduced only in 0023; using them would fabricate an upgrade failure.
historic=MigrationExecutor(connection).loader.project_state([
    ('onboarding','0018_restore_activity_cancellation_authority')]).apps
OldCase=historic.get_model('onboarding','OnboardingCase')
OldAssignment=historic.get_model('onboarding','CaseAssignment')
OldTask=historic.get_model('onboarding','Task')
joining_date=timezone.localdate()+timedelta(days=21)
tv_id=uuid.UUID(published['version_id'])
template_task=TemplateTask.objects.get(version_id=tv_id,key='manager_preparation')
with transaction.atomic():
    case=OldCase.objects.create(organization_id=org.pk,
        employee_id=members['EMPLOYEE'].pk,joining_date=joining_date,
        template_version_id=tv_id,created_by_id=users['HR'].pk,status='CREATED')
    assignments={}
    for role in ('HR','IT','MANAGER'):
        assignments[role]=OldAssignment.objects.create(case_id=case.pk,
            role=role,member_id=members[role].pk,
            effective_from=timezone.now(),assigned_by_id=members['HR'].pk,
            reason='Historical synthetic owner assignment for migration test')
    start_at=scheduled_at(joining_date,template_task.available_offset_days,
        org.timezone,template_task.available_local_time)
    due_at=scheduled_at(joining_date,template_task.due_offset_days,
        org.timezone,template_task.due_local_time)
    task=OldTask.objects.create(case_id=case.pk,template_task_id=template_task.pk,
        key=template_task.key,kind=template_task.kind,title=template_task.title,
        description=template_task.description,required=template_task.required,
        applicable=True,owner_role='MANAGER',
        owner_assignment_id=assignments['MANAGER'].pk,
        evidence_spec=template_task.evidence_spec,available_at=start_at,due_at=due_at,
        execution_state='IN_PROGRESS',work_started_at=timezone.now())
    OldCase.objects.filter(pk=case.pk).update(status='PRE_JOINING',
        version=2,activated_at=timezone.now())
task=Task.objects.get(pk=task.pk)
completed_by=users['MANAGER'] if scenario in ('matching','legacy_matching') else users['HR']
with transaction.atomic():
    evidence=ManagerAttestation.objects.create(task=task,actor=users['MANAGER'],
        prepared_fields={'first_week_plan':'Work planned','buddy_name':'Synthetic Buddy',
                         'workstation_ready':True},note='Synthetic manager attestation')
    completion=TaskCompletion.objects.create(task=task,evidence_type='MANAGER_PREPARATION',
        manager_attestation=evidence,completed_by=completed_by,evidence_hash='0'*64)
    task.execution_state='COMPLETED'
    task.completed_at=timezone.now()
    task.save(update_fields=['execution_state','completed_at'])
assert TaskCompletion.objects.filter(pk=completion.pk).exists()
with connection.cursor() as cur:
    cur.execute('SELECT 1 FROM django_migrations WHERE app=%s AND name=%s',
        ['onboarding','0019_restore_manager_actor_provenance'])
    assert cur.fetchone() is None
legacy=scenario.startswith('legacy_')
if legacy:
    # Install the *exact trigger/function portion* of the old 0019 that had
    # no historical preflight, then record 0019 as already applied. This
    # represents the documented prior-installation upgrade path without
    # weakening or mutating a real database.
    old_0019=import_module(
        'backend.onboarding.migrations.0019_restore_manager_actor_provenance')
    previous_sql=old_0019.SQL[old_0019.SQL.index('CREATE OR REPLACE FUNCTION'):]
    assert 'DO $m3_provenance_upgrade$' not in previous_sql
    with connection.cursor() as cur:
        cur.execute(previous_sql)
    MigrationRecorder(connection).record_applied(
        'onboarding','0019_restore_manager_actor_provenance')
    with connection.cursor() as cur:
        cur.execute('SELECT 1 FROM django_migrations WHERE app=%s AND name=%s',
            ['onboarding','0019_restore_manager_actor_provenance'])
        assert cur.fetchone() is not None

if scenario in ('matching','legacy_matching'):
    call_command('migrate','onboarding','0020',interactive=False,verbosity=0)
    with connection.cursor() as cur:
        for name in ('0019_restore_manager_actor_provenance',
                     '0020_audit_existing_manager_completion_provenance'):
            cur.execute('SELECT 1 FROM django_migrations WHERE app=%s AND name=%s',
                ['onboarding',name])
            assert cur.fetchone() is not None
        cur.execute("SELECT pg_get_functiondef('public.m3_guard_manager_completion_actor()'::regprocedure)")
        assert 'att.actor_id=NEW.completed_by_id' in cur.fetchone()[0]
    assert TaskCompletion.objects.get(pk=completion.pk).completed_by_id==users['MANAGER'].pk
    # New T06 D5 proof: continue the same populated 0018 history through all
    # current migrations, including the M5 exception and deferred date guards.
    # The historical attestation, completion and ownership must survive intact.
    call_command('migrate',interactive=False,verbosity=0)
    applied=MigrationRecorder(connection).applied_migrations()
    for mandatory in (
        ('onboarding','0020_audit_existing_manager_completion_provenance'),
        ('onboarding','0023_m5_case_joining_date_revisions'),
        ('onboarding','0025_m5_case_date_commit_invariant'),
        ('notifications','0002_policy_version_escalation'),
    ):
        assert mandatory in applied, f'Current-source migration missing: {mandatory}'
    current_case=OnboardingCase.objects.get(pk=case.pk)
    task.refresh_from_db()
    preserved=TaskCompletion.objects.get(pk=completion.pk)
    assert preserved.task_id==task.pk
    assert preserved.manager_attestation_id==evidence.pk
    assert preserved.completed_by_id==users['MANAGER'].pk
    assert ManagerAttestation.objects.get(pk=evidence.pk).actor_id==users['MANAGER'].pk
    assert task.execution_state=='COMPLETED'
    assert current_case.schedule_revision==0 and current_case.status=='PRE_JOINING'
    with connection.cursor() as cur:
        cur.execute("SELECT tgname FROM pg_trigger WHERE tgname=%s",
            ['m5_case_date_revision_invariant'])
        assert cur.fetchone() is not None, 'Current M5 date guard not installed'
    label='LEGACY_0019_' if legacy else ''
    print(f'M4_MANAGER_UPGRADE_{label}MATCHING_PASS: immutable evidence preserved, 0020 installed')
    print(f'D5_POPULATED_{label}FULL_FORWARD_MIGRATION_PASS: current schema, attestation and case preserved')
else:
    try:
        call_command('migrate','onboarding','0020',interactive=False,verbosity=0)
    except Exception as exc:
        cause=exc
        found=False
        while cause is not None:
            if getattr(cause,'sqlstate',None)=='23514':
                found=True
                break
            cause=getattr(cause,'__cause__',None)
        assert found, 'Upgrade failed for a reason other than mismatched historical manager provenance'
    else:
        raise AssertionError('Mismatched historical manager actor unexpectedly survived upgrade')
    connection.close()
    with connection.cursor() as cur:
        cur.execute('SELECT 1 FROM django_migrations WHERE app=%s AND name=%s',
            ['onboarding','0020_audit_existing_manager_completion_provenance'])
        assert cur.fetchone() is None
        cur.execute('SELECT 1 FROM django_migrations WHERE app=%s AND name=%s',
            ['onboarding','0019_restore_manager_actor_provenance'])
        assert (cur.fetchone() is not None)==legacy
        # A blocked migration must not silently apply newer schema or repair
        # contrary historical identity in either old installation history.
        cur.execute('SELECT 1 FROM django_migrations WHERE app=%s AND name=%s',
            ['onboarding','0025_m5_case_date_commit_invariant'])
        assert cur.fetchone() is None
    assert OldCase.objects.get(pk=case.pk).status=='PRE_JOINING'
    assert ManagerAttestation.objects.get(pk=evidence.pk).actor_id==users['MANAGER'].pk
    assert TaskCompletion.objects.get(pk=completion.pk).completed_by_id==users['HR'].pk
    label='LEGACY_0019_' if legacy else ''
    print(f'M4_MANAGER_UPGRADE_{label}MISMATCH_FAIL_CLOSED_PASS: evidence untouched, 0020 not installed')
