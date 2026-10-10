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
from django.db import connection,transaction
from django.utils import timezone
from backend.accounts.models import Organization,Membership,User
from backend.templates.services import create_default,publish_template
from backend.onboarding.commands import create_case,activate_case
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
made,_=create_case(actor=users['HR'],employee_id=members['EMPLOYEE'].pk,
    template_version_id=uuid.UUID(published['version_id']),
    joining_date=timezone.localdate()+timedelta(days=21),
    owner_ids={'IT':members['IT'].pk,'MANAGER':members['MANAGER'].pk},key=uuid.uuid4())
case=OnboardingCase.objects.get(pk=made['case_id'])
activate_case(actor=users['HR'],case_id=case.pk,key=uuid.uuid4(),expected_version=1)
task=Task.objects.get(case=case,key='manager_preparation')
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
    label='LEGACY_0019_' if legacy else ''
    print(f'M4_MANAGER_UPGRADE_{label}MATCHING_PASS: immutable evidence preserved, 0020 installed')
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
    assert TaskCompletion.objects.get(pk=completion.pk).completed_by_id==users['HR'].pk
    label='LEGACY_0019_' if legacy else ''
    print(f'M4_MANAGER_UPGRADE_{label}MISMATCH_FAIL_CLOSED_PASS: evidence untouched, 0020 not installed')
