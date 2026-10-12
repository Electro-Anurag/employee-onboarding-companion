"""Read-only cross-store recovery preflight for exact version-pinned documents.

This is an integrity check, not an S3 backup, a scanner substitute or
authorization to restore/repin immutable PostgreSQL receipt rows.
To interpret a full PASS the operator must first stop document intake/writes.
Only bounded existing DB references are examined; no object content is emitted.
"""
import hashlib

from backend.documents import storage
from backend.documents.real_models import (
    SecureUpload, StoredQuarantineObject, SecureCleanObject,
)
from backend.onboarding.services import CommandFailure


def verify_referenced_versions(*, limit=100):
    """Check EVERY upload within a strictly bounded quiesced candidate scope.

    A missing receipt is reported as an incomplete upload, not silently
    declared recoverable. Read exact S3 VersionId and SHA-256 from the same
    immutable DB upload; no key/latest-version fallback is permitted.
    """
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("INVALID_RECOVERY_VERIFICATION_LIMIT")
    if not storage.configured():
        raise CommandFailure("REAL_DOCUMENT_STORAGE_DISABLED", 503)
    client = storage.client()
    quarantine_bucket, clean_bucket = storage.buckets(client)
    # LIMIT + 1 is essential: never claim the entire collection passed when
    # the oldest 100 rows only were sampled.
    ids = list(SecureUpload.objects.order_by("pk").values_list("pk", flat=True)[:limit + 1])
    if len(ids) > limit:
        return dict(state="STOP", checked=0, quarantine_verified=0,
                    clean_verified=0, incomplete=0, integrity_errors=0,
                    scope_exceeded=True)
    verified_q = verified_c = incomplete = errors = 0
    for upload in SecureUpload.objects.filter(pk__in=ids).select_related(
            "task").order_by("pk"):
        stored = StoredQuarantineObject.objects.filter(upload_id=upload.pk).first()
        clean = SecureCleanObject.objects.select_related("scan").filter(
            upload_id=upload.pk).first()
        if stored is None:
            if clean is None:
                incomplete += 1
            else:
                errors += 1  # Clean reference without a quarantine receipt.
            continue
        expected_q = (
            "quarantine/" + str(upload.task.case.organization_id)
            + "/" + str(upload.task.case_id) + "/" + str(upload.pk) + ".pdf"
        )
        if (upload.object_key != expected_q
            or len(upload.sha256) != 64
            or not all(ch in "0123456789abcdef" for ch in upload.sha256)
            or not stored.version_id or stored.version_id == "null"):
            errors += 1
            continue
        try:
            raw = storage.read_exact(quarantine_bucket, upload.object_key,
                                     stored.version_id, upload.sha256)
            if len(raw) != upload.byte_length:
                errors += 1
                continue
            verified_q += 1
            if clean is None:
                continue
            expected_clean = (
                "clean/" + str(upload.task.case_id) + "/"
                + str(upload.pk) + ".pdf"
            )
            if (clean.object_key != expected_clean
                or not clean.version_id or clean.version_id == "null"
                or clean.scan.upload_id != upload.pk
                or clean.scan.outcome != "CLEAN"):
                errors += 1
                continue
            restored = storage.read_exact(clean_bucket, clean.object_key,
                                          clean.version_id, upload.sha256)
            if len(restored) != upload.byte_length:
                errors += 1
                continue
            verified_c += 1
        except CommandFailure:
            # No document bytes, object keys, S3 error contents, or
            # employee identifiers in operator output.
            errors += 1
    checked = len(ids)
    return {
        "state": ("PASS" if checked and errors == 0 and incomplete == 0
                  else "STOP"),
        "checked": checked,
        "quarantine_verified": verified_q,
        "clean_verified": verified_c,
        "incomplete": incomplete,
        "integrity_errors": errors,
        "scope_exceeded": False,
    }
