# D6 secure document cross-store recovery: exact S3 versions

**Status 12 Oct 2026:** candidate read-only verifier, awaiting exact SHA CI qualification. **Not a backup/restore implementation** and not permission to enable live identity-document intake. The deployed Render Free environment still has real document storage disabled; hosted J02 and production GO remain blocked.

## Why a PostgreSQL-only restore is unsafe

`SecureUpload` stores the authoritative file SHA-256 and byte length, while `StoredQuarantineObject` and `SecureCleanObject` hold S3 object keys and immutable **VersionId** values. An object with the same key and hash but a *different* S3 version ID does **not** satisfy the persisted DB receipt. Restoring a dump while losing referenced historical versions must stop the system instead of reassigning an old receipt to the newest object or silently rewriting audit.

## Current bounded read-only preflight

`backend/documents/recovery_integrity.py` and the management command `verify_secure_document_storage`:
- Require real-storage feature configuration, two distinct versioned S3 buckets and a successfully authenticated provider.
- Require explicit `--confirm-quiesced`: the operator must first stop intake, uploads and scan/HR changes through an approved maintenance procedure. **The flag records operator acknowledgement; it does not stop processes automatically.**
- Examine **every existing SecureUpload row only if there are at most `--limit` rows**, with a hard maximum of 100. If more exist, return `scope_exceeded` and STOP; no misleading first-100 PASS.
- Reconstruct the allowed quarantine and clean key patterns; fetch by **exact recorded VersionId**, independently SHA-256 and byte-length check the payload; reject malformed receipts, clean receipts with no matching CLEAN scan, incomplete uploads and missing/tampered versions.
- Return only bounded aggregate counts and PASS/STOP, never object keys, raw bytes, employees, provider errors or any credentials.
- Never upload, delete, overwrite, remap object versions, adjust audit records, or retry scanner jobs.
- A database with zero secure uploads is **STOP/not qualified**, not proof of a successful document recovery.
- Not a consistent database snapshot by itself: if writes are still occurring, the result must not be used as a full inventory assertion.

Example **only after operator-approved isolation and quiescence**:

```bash
python manage.py verify_secure_document_storage --confirm-quiesced --limit 100
```

A nonzero exit, `INTEGRITY_ERRORS>0`, `INCOMPLETE>0` or `SCOPE_EXCEEDED=True` is STOP. **A green result verifies references in the current DB against a currently reachable S3 store, not that both stores can be backed up and restored.**

## Prerequisites before actual hosted recovery/release

1. Owner-approved documented maintenance scope, no production/personal employee data in synthetic qualification, and a verified private network/storage endpoint.
2. A durable PostgreSQL restore point with independently verified database migration history and immutable audit. Existing local test [38209892920](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38209892920) proves **only a disposable PostgreSQL** dump/restore.
3. Coordinated durable copy of **every referenced S3 historical object version**, including the original VersionId semantics. A generic copy into a new versioned bucket normally generates **new IDs** and cannot be assumed compatible. Do not invent a version rebind/migration or disable immutability checks.
4. Prove an independent disaster-recovery restoration of both systems **without changing the stored identifiers**, or design an owner-approved audited replacement reference mapping and rerun the independent security review.
5. Prove private bucket policies, KMS/encryption, scanner freshness, worker stability, backlog reconciliation, backup/restore permissions, retention/deletion controls and measured RPO/RTO.
6. Only after these pass may hosted J02/J03 workflows and T17–T25 release gates be reconsidered. Existing Free Render configuration lacks the secure storage/scanner and always-on worker; no paid infrastructure or feature flag is authorized by this document.

## CI evidence

[New live workflow 38218007489](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38218007489) targets real versioned MinIO plus current ClamAV, one actual clean promoted synthetic PDF, a missing exact-version adverse case, and an over-limit refusal. It is **NOT YET QUALIFIED** at document creation. The integrated run [38218007460](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38218007460) separately verifies the new source with general regressions; real-storage cases deliberately skip when MinIO/ClamAV is disabled. Check final results before declaring any PASS.
