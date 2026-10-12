"""Actual MinIO/S3 exact-version cross-store verifier (no mock bytes)."""
import hashlib
import uuid
import pytest

from backend.onboarding.tests.test_m2_workflow import world, published, create
from backend.onboarding.commands import activate_case
from backend.onboarding.models import OnboardingCase, Task
from backend.documents.tests.test_secure_s3_journey import generated_pdf
from backend.documents.real_commands import prepare, receive, scan_one
from backend.documents.real_models import StoredQuarantineObject, SecureCleanObject
from backend.documents import storage
from backend.documents.recovery_integrity import verify_referenced_versions

pytestmark = pytest.mark.skipif(
    __import__("os").environ.get("M3_LIVE_S3_CLAMAV") != "1",
    reason="Requires actual CI MinIO versioning and fresh ClamAV daemon")


@pytest.mark.django_db(transaction=True)
def test_d6_exact_s3_version_recovery_verifier_refuses_missing_versions(world):
    org, roles = world
    created, _ = create(world, published(world))
    case = OnboardingCase.objects.get(pk=created["case_id"])
    activate_case(actor=roles["HR"][0], case_id=case.pk,
                  key=uuid.uuid4(), expected_version=1)
    task = Task.objects.get(case=case, key="identity_document")
    raw = generated_pdf()
    intent, _ = prepare(actor=roles["EMPLOYEE"][0], case_id=case.pk,
        task_id=task.pk, sha256=hashlib.sha256(raw).hexdigest(),
        size=len(raw), filename="synthetic_recovery_probe.pdf",
        key=uuid.uuid4(), expected_version=2)
    upload_id = uuid.UUID(intent["result"]["upload_id"])
    initially = verify_referenced_versions()
    assert initially["state"] == "STOP" and initially["incomplete"] == 1
    assert initially["integrity_errors"] == 0

    receive(actor=roles["EMPLOYEE"][0], case_id=case.pk,
        task_id=task.pk, upload_id=upload_id, raw=raw,
        key=uuid.uuid4(), expected_version=3)
    quarantined = verify_referenced_versions()
    assert quarantined == {
        "state":"PASS","checked":1,"quarantine_verified":1,
        "clean_verified":0,"incomplete":0,"integrity_errors":0,
        "scope_exceeded":False,
    }

    scanned = scan_one(upload_id)
    assert scanned["state"] == "AWAITING_HR_REVIEW"
    ready = verify_referenced_versions()
    assert ready["state"] == "PASS" and ready["clean_verified"] == 1
    assert ready["quarantine_verified"] == 1 and ready["integrity_errors"] == 0

    client = storage.client()
    quarantine, clean_bucket = storage.buckets(client)
    receipt = StoredQuarantineObject.objects.get(upload_id=upload_id)
    clean = SecureCleanObject.objects.get(upload_id=upload_id)
    assert storage.read_exact(quarantine, intent["result"].get("object_key",
        __import__("backend.documents.real_models", fromlist=["SecureUpload"])
          .SecureUpload.objects.get(pk=upload_id).object_key),
        receipt.version_id,hashlib.sha256(raw).hexdigest()) == raw
    assert storage.read_exact(clean_bucket,clean.object_key,clean.version_id,
                              hashlib.sha256(raw).hexdigest()) == raw

    # This destructive action is confined to the fresh disposable test bucket.
    # The missing exact version must not be replaced with the latest version
    # or treated as a successful restore.
    client.delete_object(Bucket=quarantine,
        Key=__import__("backend.documents.real_models",fromlist=["SecureUpload"])
            .SecureUpload.objects.get(pk=upload_id).object_key,
        VersionId=receipt.version_id)
    missing = verify_referenced_versions()
    assert missing["state"] == "STOP"
    assert missing["integrity_errors"] == 1
    assert missing["clean_verified"] == 0
    assert missing["scope_exceeded"] is False


@pytest.mark.django_db
def test_d6_recovery_verifier_never_claims_oversized_scope(world):
    from unittest.mock import patch
    from django.test import override_settings
    from backend.documents.real_models import SecureUpload
    # Constrain full-scope assertion even if caller requests one record.
    with override_settings(M3_REAL_DOCUMENT_ENABLED=True,
        M3_S3_QUARANTINE_BUCKET="ci-q", M3_S3_CLEAN_BUCKET="ci-c"):
        with patch("backend.documents.storage.client",return_value=object()), \
             patch("backend.documents.storage.buckets",return_value=("ci-q","ci-c")), \
             patch.object(SecureUpload.objects,"order_by") as ordered:
            ordered.return_value.values_list.return_value.__getitem__.return_value = [
                uuid.uuid4(), uuid.uuid4()
            ]
            result=verify_referenced_versions(limit=1)
            assert result["state"] == "STOP"
            assert result["scope_exceeded"]
            assert result["checked"] == 0
