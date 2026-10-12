"""CI-only disposable PostgreSQL dump/restore qualification (no real employee data).

Seeds current migrations with typed evidence, audited commands and a real
in-app reminder, then compares durable state on an independently restored DB.
Never accepts production/hosted connection strings.
"""
import hashlib
import json
import os
import secrets
import sys
import uuid
from datetime import timedelta

ALLOWED_DB = ("onboarding_m0", "ci_d5_restored")
db = os.environ.get("POSTGRES_DB", "")
if (len(sys.argv) != 2 or sys.argv[1] not in ("seed", "verify")
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("EOC_D5_BACKUP_PROBE") != "1"
        or os.environ.get("POSTGRES_HOST") not in ("localhost", "127.0.0.1")
        or os.environ.get("DATABASE_URL")
        or db not in ALLOWED_DB
        or (sys.argv[1] == "seed" and db != "onboarding_m0")
        or (sys.argv[1] == "verify" and db != "ci_d5_restored")):
    raise SystemExit("D5 backup/restore probe requires isolated approved CI database")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")

import django
django.setup()
from django.conf import settings
from django.db import transaction, DatabaseError, connection
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

from backend.accounts.models import Organization, Membership, User
from backend.templates.services import create_default, publish_template
from backend.onboarding.commands import create_case, activate_case, start_task, attest_manager
from backend.onboarding.models import (
    OnboardingCase, Task, TaskCompletion, ManagerAttestation, CaseAssignment,
)
from backend.audit.models import AuditEvent, CommandReceipt
from backend.notifications.models import ReminderIntent, Notification
from backend.notifications.services import reconcile_case

if not settings.DEBUG:
    raise SystemExit("D5 probe refuses non-DEBUG mode")
if len(connection.introspection.table_names()) < 20:
    raise SystemExit("D5 database has not been migrated")


def seed():
    if Organization.objects.exists() or OnboardingCase.objects.exists():
        raise SystemExit("D5 seed refuses non-empty test database")
    org = Organization.objects.create(name="D5 Disposable Backup/Restore",timezone="UTC")
    people = {}
    for role in ("HR","EMPLOYEE","IT","MANAGER"):
        user = User.objects.create_user(
            email=role.lower()+"@d5.restore.invalid",
            password=secrets.token_urlsafe(20)+"Ab1!",
            display_name="D5 Synthetic "+role)
        member = Membership.objects.create(user=user,organization=org,role=role,
            can_manage_templates=(role=="HR"),
            can_coordinate_ownership=(role=="HR"))
        people[role] = (user,member)
    draft = create_default(actor=people["HR"][0])
    published = publish_template(actor=people["HR"][0],
        template_id=uuid.UUID(draft["id"]),revision=1)
    result,status = create_case(actor=people["HR"][0],
        employee_id=people["EMPLOYEE"][1].pk,
        template_version_id=uuid.UUID(published["version_id"]),
        joining_date=timezone.localdate(),  # Due today: real in-app policy reminder
        owner_ids={"IT":people["IT"][1].pk,"MANAGER":people["MANAGER"][1].pk},
        key=uuid.uuid4())
    assert status == 201
    case_id = uuid.UUID(result["case_id"])
    activated,status = activate_case(actor=people["HR"][0],
        case_id=case_id,key=uuid.uuid4(),expected_version=1)
    assert status==200 and activated["result"]["status"]=="PRE_JOINING"
    manager_task = Task.objects.get(case_id=case_id,key="manager_preparation")
    started,code = start_task(actor=people["MANAGER"][0],
        case_id=case_id,task_id=manager_task.pk,
        key=uuid.uuid4(),expected_version=2)
    assert code==200
    attested,code = attest_manager(actor=people["MANAGER"][0],
        case_id=case_id,task_id=manager_task.pk,
        fields={"first_week_plan":"Synthetic first-week recovery schedule",
                "buddy_name":"D5 Synthetic Buddy","workstation_ready":True},
        note="Verified synthetic manager preparation during backup qualification",
        key=uuid.uuid4(),expected_version=3)
    assert code==200 and attested["result"]["state"]=="COMPLETED"
    # No worker dispatch, email, provider, or external action: only in-DB
    # current-state recipient intent and active in-app notification.
    result=reconcile_case(case_id)
    assert result["created"]>=1, result
    assert TaskCompletion.objects.filter(task=manager_task).exists()
    assert AuditEvent.objects.count()>=3
    assert CommandReceipt.objects.count()>=3
    print("D5_SYNTHETIC_PERSISTED_EVIDENCE_READY")


def snapshot():
    case=OnboardingCase.objects.get()
    qs = lambda model,fields,order: list(model.objects.order_by(*order).values(*fields))
    data={
        "case":qs(OnboardingCase,("id","organization_id","employee_id",
            "joining_date","status","version","schedule_revision",
            "template_version_id","activated_at"),("id",)),
        "assignments":qs(CaseAssignment,("id","case_id","role","member_id",
            "effective_from","effective_to"),("id",)),
        "tasks":qs(Task,("id","case_id","key","kind","execution_state",
            "blocked_reason_codes","owner_assignment_id","version",
            "available_at","due_at","work_started_at","completed_at"),("id",)),
        "completions":qs(TaskCompletion,("id","task_id","evidence_type",
            "manager_attestation_id","completed_by_id","evidence_hash",
            "completed_at"),("id",)),
        "attestations":qs(ManagerAttestation,("id","task_id","actor_id",
            "prepared_fields","created_at"),("id",)),
        "audit":qs(AuditEvent,("id","stream_id","sequence","event_type",
            "previous_hash","event_hash","entity_id","actor_id"),("id",)),
        "receipts":qs(CommandReceipt,("id","route","case_id",
            "idempotency_key","request_hash","status_code"),("id",)),
        "reminders":qs(ReminderIntent,("id","case_id","task_id","recipient_id",
            "status","rule_code","schedule_revision","action_revision"),("id",)),
        "inbox":qs(Notification,("id","case_id","task_id","recipient_id",
            "intent_id","status","read_at"),("id",)),
        "migrations":sorted([a+"."+b for a,b in
            MigrationRecorder(connection).applied_migrations()]),
    }
    assert len(data["case"])==1
    assert len(data["tasks"])==17
    assert len(data["completions"])==len(data["attestations"])==1
    assert len(data["reminders"])>0 and len(data["inbox"])>0
    assert len(data["audit"])>0 and len(data["receipts"])>0
    assert any(x["key"]=="manager_preparation"
        and x["execution_state"]=="COMPLETED" for x in data["tasks"])
    # Case and dependency data come from server-derived immutable DB state.
    payload=json.dumps(data,sort_keys=True,separators=(",",":"),default=str)
    return {"sha256":hashlib.sha256(payload.encode()).hexdigest(),
        "counts":{k:len(v) for k,v in data.items()}}


if sys.argv[1]=="seed":
    seed()
elif not Organization.objects.filter(name="D5 Disposable Backup/Restore").exists():
    raise SystemExit("D5 synthetic restore evidence is absent")
print("D5_BACKUP_STATE_FINGERPRINT "+json.dumps(snapshot(),sort_keys=True))
if sys.argv[1]=="verify":
    # Re-check database-enforced append-only provenance on the RESTORED database.
    audit_id=AuditEvent.objects.first().pk
    completion_id=TaskCompletion.objects.first().pk
    with transaction.atomic():
        try:
            with transaction.atomic():
                AuditEvent.objects.filter(pk=audit_id).update(event_type="FORGED")
        except DatabaseError:
            pass
        else:
            raise AssertionError("Restored audit mutation was not rejected")
    with transaction.atomic():
        try:
            with transaction.atomic():
                TaskCompletion.objects.filter(pk=completion_id).update(evidence_hash="f"*64)
        except DatabaseError:
            pass
        else:
            raise AssertionError("Restored completion mutation was not rejected")
    assert AuditEvent.objects.get(pk=audit_id).event_type!="FORGED"
    assert TaskCompletion.objects.get(pk=completion_id).evidence_hash!="f"*64
    print("D5_RESTORED_AUDIT_AND_COMPLETION_IMMUTABILITY_PASS")
