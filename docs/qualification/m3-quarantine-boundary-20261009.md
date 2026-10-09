# M3 quarantine adapter — development boundary (2026-10-09)

## Truth status

This is a **bounded, disabled-by-default, pre-production intake and scanner-adapter experiment**. It is **not** production document management, private object storage, verified antivirus operation, or HR-approved document evidence. Do **not** enable it for real employee data. Exact synthetic text fixtures continue through the existing separately qualified DocumentRevision / DocumentReview workflow.

## Source and permissions

- Modules: `backend/documents/quarantine_models.py`, `quarantine_commands.py`, `quarantine_views.py`, `scanner.py`.
- `M3_QUARANTINE_INTAKE_ENABLED` defaults to false. A non-empty `M3_CLAMAV_HOST` is also required.
- The opt-in multipart `POST /api/v1/cases/{case_id}/tasks/{task_id}/quarantine-intake` requires authenticated employee ownership, CSRF, case-version and idempotency headers; accepts no other form fields.
- Only a 16–262,144 byte PDF-prefixed payload is eligible for quarantine. The header check is not a PDF parser or a security verdict. Byte length and SHA-256 are persisted.
- The separate case-scoped `GET .../quarantine-status` returns only metadata and scan attempts to the authorized employee or HR. It exposes **no raw-byte download or release route**.
- Payloads are in **PostgreSQL BinaryField** for this bounded experiment; they are not in S3 or separated object-storage infrastructure. A deployment that uses this route for genuine private documents would violate the target architecture.

## Scanner and error behavior

- The `clamav_scan` adapter uses the ClamAV TCP INSTREAM protocol with bounded payloads, two-second socket timeouts, bounded responses and explicit `stream: OK` / `stream: ... FOUND` recognition.
- Missing scanner, connection loss, timeout, error response or malformed response maps to `ERROR`, never `CLEAN`. A direct network call may be made only to the explicitly configured daemon endpoint.
- The manual `python manage.py scan_quarantined_documents --limit 10` command records immutable outcomes. The first two errors may be retried, up to three attempts. Clean and malware outcomes are terminal for this experiment.
- Even a **CLEAN** result is *not* automatically trusted as an HR acceptance, document completion, dependency release, or public download authorization. No background scheduler is attached yet.
- Appendix: the quarantined payload, scan-attempt records and synthetic review/completion evidence use separate models. Scan history is append-only with PostgreSQL triggers.

## Qualification limits and next required build

Tests cover fail-closed ClamAV protocol parsing via controlled socket replies, role-scoped multipart intake, exact-byte hash protection, immutability, scanner unavailable/retry behavior, and absence of onboarding completion.

Before genuine employee documents can be accepted, implement: encrypted private S3-compatible object storage with per-case isolation and retention/lifecycle controls; a durable out-of-process scanner and engine/signature-version evidence; content-type/PDF parser defenses; quarantine recovery/cleanup; malware rejection and notifications; atomic promotion to the clean bucket; authorization-checked downloads; and HR accept/reject flows bound to the approved clean object version. Independently qualify all of those on an exact SHA with a **real** ClamAV daemon and object storage service, rather than only test doubles.

This slice does not claim to satisfy the full M3 storage/scanning acceptance criteria.
