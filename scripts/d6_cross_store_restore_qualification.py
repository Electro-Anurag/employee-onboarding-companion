"""Disposable, quiesced PostgreSQL + MinIO physical snapshot restore proof.

Cannot run against public, production, remote or populated systems. No document
bytes, IDs, source keys, credentials, or employee data are printed.
"""
import hashlib
import json
import os
import secrets
import sys
import uuid
from datetime import timedelta

if (
    len(sys.argv) != 2 or sys.argv[1] not in ("seed", "verify")
    or os.environ.get("GITHUB_ACTIONS") != "true"
    or os.environ.get("EOC_D6_DR_PROBE") != "isolated-synthetic-only"
    or os.environ.get("POSTGRES_HOST") not in ("localhost", "127.0.0.1")
    or os.environ.get("POSTGRES_PORT") != "5432"
    or os.environ.get("M3_S3_ENDPOINT_URL") != "http://127.0.0.1:9000"
    or os.environ.get("M3_S3_ALLOW_LOCAL_TEST_ENDPOINT") != "1"
    or os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_DB") != (
        "onboarding_m0" if sys.argv[1] == "seed" else "ci_d6_restored"
    )
):
    raise SystemExit("D6 isolated synthetic recovery qualification only")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")
import django
django.setup()

from django.db.migrations.recorder import MigrationRecorder
from django.db import connection

from backend.accounts.models import Organization, Membership, User
from backend.templates.services import create_default, publish_template
from backend.onboarding.commands import create_case, activate_case
from backend.onboarding.models import OnboardingCase, Task, TaskCompletion
from backend.documents.real_models import (
    SecureUpload, StoredQuarantineObject, SecureCleanObject,
    SecureScanAttempt, SecureHRReview,
)
from backend.documents.real_commands import prepare, receive, scan_one, review
from backend.documents.tests.test_secure_s3_journey import generated_pdf
from backend.documents.recovery_integrity import verify_referenced_versions
from backend.audit.models import AuditEvent, CommandReceipt
from backend.notifications.models import ReminderIntent, Notification
from backend.documents import storage
from django.utils import timezone

def seed():
    if Organization.objects.exists() or SecureUpload.objects.exists():
        raise SystemExit("Refusing to seed nonempty PostgreSQL")
    org = Organization.objects.create(name="D6 CI-only version-preserving restore", timezone="UTC")
    actors = {}
    for role in ("HR", "EMPLOYEE", "IT", "MANAGER"):
        user = User.objects.create_user(
            email=role.lower()+"@d6-restore.invalid",
            display_name="Disposable D6 "+role,
            password=secrets.token_urlsafe(24)+"Ab1!")
        member = Membership.objects.create(
            user=user, organization=org, role=role,
            can_manage_templates=role=="HR",
            can_coordinate_ownership=role=="HR")
        actors[role] = (user, member)
    draft = create_default(actor=actors["HR"][0])
    published = publish_template(actor=actors["HR"][0],
        template_id=uuid.UUID(draft["id"]), revision=1)
    case_result, status = create_case(
        actor=actors["HR"][0], employee_id=actors["EMPLOYEE"][1].pk,
        template_version_id=uuid.UUID(published["version_id"]),
        joining_date=timezone.localdate()+timedelta(days=28),
        owner_ids={"IT":actors["IT"][1].pk,"MANAGER":actors["MANAGER"][1].pk},
        key=uuid.uuid4())
    assert status==201
    case_id=uuid.UUID(case_result["case_id"])
    _, status = activate_case(actor=actors["HR"][0],case_id=case_id,
        key=uuid.uuid4(),expected_version=1)
    assert status==200
    task=Task.objects.get(case_id=case_id,key="identity_document")
    raw=generated_pdf()
    digest=hashlib.sha256(raw).hexdigest()
    intent,code=prepare(actor=actors["EMPLOYEE"][0],
        case_id=case_id,task_id=task.pk,sha256=digest,size=len(raw),
        filename="disposable_restore.pdf",key=uuid.uuid4(),expected_version=2)
    assert code==201
    upload_id=uuid.UUID(intent["result"]["upload_id"])
    received,code=receive(actor=actors["EMPLOYEE"][0],
        case_id=case_id,task_id=task.pk,upload_id=upload_id,raw=raw,
        key=uuid.uuid4(),expected_version=3)
    assert code==201 and received["result"]["state"]=="QUARANTINED"
    scanned=scan_one(upload_id)
    assert scanned["state"]=="AWAITING_HR_REVIEW"
    result,code=review(actor=actors["HR"][0],case_id=case_id,task_id=task.pk,
        upload_id=upload_id,decision="ACCEPTED",
        note="Disposable D6 document restore acceptance",
        key=uuid.uuid4(),expected_version=4)
    assert code==201 and result["result"]["task_completion"]=="COMPLETED"
    print("D6_SYNTHETIC_VERSION_PINNED_CASE_READY")


def fingerprint():
    def rows(model,fields):
        return list(model.objects.order_by("pk").values(*fields))
    integrity=verify_referenced_versions(limit=10)
    assert integrity["state"]=="PASS",integrity["state"]
    assert integrity["checked"]==1
    assert integrity["quarantine_verified"]==1
    assert integrity["clean_verified"]==1
    assert integrity["incomplete"]==0 and integrity["integrity_errors"]==0
    data={
        "cases":rows(OnboardingCase,("id","organization_id","employee_id",
            "status","version","joining_date","schedule_revision")),
        "tasks":rows(Task,("id","case_id","key","execution_state","version",
            "owner_assignment_id")),
        "completions":rows(TaskCompletion,("id","task_id","evidence_type",
            "secure_review_id","evidence_hash","completed_by_id")),
        "uploads":rows(SecureUpload,("id","task_id","sha256","byte_length",
            "object_key","revision")),
        "quarantine":rows(StoredQuarantineObject,("id","upload_id","version_id")),
        "scans":rows(SecureScanAttempt,("id","upload_id","number","outcome")),
        "clean":rows(SecureCleanObject,("id","upload_id","object_key",
            "version_id","scan_id")),
        "reviews":rows(SecureHRReview,("id","clean_id","reviewer_id","decision")),
        "audit":rows(AuditEvent,("id","stream_id","sequence","event_type",
            "previous_hash","event_hash","entity_id","actor_id")),
        "receipts":rows(CommandReceipt,("id","case_id","route",
            "request_hash","status_code","idempotency_key")),
        "reminders":rows(ReminderIntent,("id","case_id","task_id","status")),
        "inbox":rows(Notification,("id","case_id","task_id","status")),
        "migrations":sorted(a+"."+b for a,b in MigrationRecorder(connection).applied_migrations())
    }
    assert len(data["cases"])==len(data["uploads"])==len(data["clean"])==1
    assert len(data["quarantine"])==len(data["reviews"])==len(data["completions"])==1
    assert len(data["audit"])>=3 and len(data["receipts"])>=3
    assert data["completions"][0]["evidence_hash"]==data["uploads"][0]["sha256"]
    canonical=json.dumps(data,sort_keys=True,separators=(",",":"),default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()

if sys.argv[1]=="seed":
    seed()
else:
    if Organization.objects.count()!=1 or not Organization.objects.filter(
            name="D6 CI-only version-preserving restore").exists():
        raise SystemExit("Wrong restored synthetic database")
digest=fingerprint()
print("EOC_D6_CROSS_STORE_FINGERPRINT_SHA256="+digest)
if sys.argv[1]=="verify":
    print("EOC_D6_EXACT_S3_VERSION_IDENTITIES_SURVIVED_RESTORE")
