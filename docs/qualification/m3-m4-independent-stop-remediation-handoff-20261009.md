# M3–M4 Independent STOP Remediation — Focused Closure Handoff

**Prepared:** 2026-10-09
**Independent original verdict:** **M3–M4 REVIEW STOP — CORRECTIONS REQUIRED** at code `0f1e6a26f1f22bc79c33de9d99e6b3cfdbfc5c9e`.
**Corrected source SHA for focused independent review:** `9313a4e9b3125545e08a07b1425beecbc62d01bc`.
**Repository/account:** private `Electro-Anurag/employee-onboarding-companion` / `Electro-Anurag`.
**Branch:** `feature/m3-m4-integrated-workflows`. Original `main` remains `fc63b3dba2690f9989570ed6f98b84f112312283`.

This is a **developer remediation handoff**, not independent approval, production readiness or owner authorization to merge/deploy. Preserve PRD v1.1 and Business Journey v1.0, including all five hosted acceptance journeys.

## Original reviewer findings and submitted corrections

| Finding | Source correction | New qualification |
|---|---|---|
| R1 HIGH generic Start strands typed tasks | `backend/provisioning/commands.py` now permits already-started IT request and employee equipment receipt; `backend/activities/commands.py` permits initial scheduling after generic Start while preserving typed evidence | New PostgreSQL tests `test_generic_start_keeps_typed_it_and_equipment_receipt_reachable`, `test_generic_start_keeps_initial_activity_schedule_reachable` |
| R2 HIGH interrupted/invalid PDF intent cannot resume/replace | `real_commands.prepare` permits **authorized, audited supersession** of unreceived intent only on changed file bytes; identical digest requires existing intent resume. `App.tsx` reads current history, resumes matching intent by UUID, uses the upload UUID as stable receive idempotency key; `EvidenceWorkflows.tsx` exposes the control | `test_m3_invalid_unreceived_document_can_be_audited_superseded` plus historical-replay and S3 412 tests; actual S3 browser upload/resume is not yet separately qualified |
| R3 HIGH exhausted scan attempts irrecoverable | Prior correction at `c7b8e3d7030191a223c0c27b8badad08db9c39ed`: `SCAN_EXHAUSTED` permits new employee revision with immutable old errors | `test_m3_exhausted_scan_error_permits_only_safe_new_revision` |
| R4 MEDIUM public SHA-256 brute-forces quiz answers | `training.definitions.public_spec` now exposes **HMAC-SHA256 opaque edition token** over private checksum using server secret and domain separation; internal private SHA still governs DB evidence. Even answer-only changes produce new public token | `test_public_training_fingerprint_cannot_oracle_private_answers` and normal server-grade HTTP tests |
| R5 MEDIUM lost manager completion actor equality | Additive migration `onboarding/0019_restore_manager_actor_provenance.py` installs manager-specific immediate INSERT guard with SQLSTATE 23514 without replacing newer shared evidence functions | `test_m3_manager_completion_requires_same_attesting_actor_after_all_migrations` checks mismatch rollback and valid matching actor |
| R6 MEDIUM overdue meeting cannot be rescheduled | Future slot still requires role/assignment, reason, validity and four-hour duration, but not end before immutable original deadline. Schedule audit records `original_due_at` and `scheduled_after_due` | `test_m4_overdue_activity_can_schedule_reasoned_recovery_without_changing_due`; full elapsed missed/reschedule/attended browser sequence not separately qualified |

## Additional security and recovery fixes

- Document downloads recheck case/task authority **after** S3 I/O and before byte response. Test: `test_m3_secure_download_rechecks_revocation_after_s3_read`.
- `backend/documents/pdf_worker.py` parses untrusted PDFs in a separate subprocess bounded by process CPU, virtual-memory and wall-clock limits; `pdf_validation.py` fails closed on timeout/invalid content. This is **not** a complete OS sandbox. Active catalog and timeout regression included.
- `backend/jobs/tasks.py` includes a CI-only environment-driven hard exit after a CLEAN scan transaction commits but before Procrastinate ACK. Live test `test_live_m3_real_content_worker_hard_exit_redelivery` uses actual content worker, PostgreSQL, MinIO and ClamAV, recovers the stalled job and asserts one scan row, one clean object, no premature completion, then separate HR acceptance.

## Qualification provenance

- Earlier full corrected SHA `31da8b6fbe95e27b0912bc54c77183fcad867caf`:
  - [Backend and React](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37973272884): SUCCESS — 141 Python passed, 2 skipped (separate live services); 2 React passed.
  - [Chromium](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37973272784): SUCCESS — 3 browser scenarios.
  - [Actual S3/ClamAV and real worker recovery](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37973272731): SUCCESS — 2 live integration tests.
- Latest corrected SHA `9313a4e9b3125545e08a07b1425beecbc62d01bc` changes only the **training opaque edition-token refinement** relative to that source; new [backend CI](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37973653735) and [browser CI](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37973653728) were triggered. Verify their final conclusions before acceptance; no claim is made here about results not yet observed.

## Still OPEN or qualified only in narrow scope

1. **Independent review STOP** remains in force until focused source and regression review of this corrected SHA.
2. M3 scanner S3/ClamAV I/O still occurs under a database transaction and upload lock. Concurrency/timeout risk is not disproved by happy-path or post-commit hard-exit tests.
3. Genuine kill before scan/promotion commits, S3 orphan-copy lifecycle, retention/deletion, bounded exhausted-error operator escalation and production alarms are not fully demonstrated.
4. AWS deployment IAM/KMS, tenant policy, object version immutability/retention, operational roles and isolation have not been verified. MinIO is not proof of AWS production security.
5. Full browser S3 upload refresh/resume/correction against live storage, elapsed meeting recovery after deadline, and all five hosted J01–J05 acceptance journeys remain future qualification tasks, **not claimed complete**.
6. Final M2 focused independent review remains separate/open. No genuine employee data, live HRIS/calendar/IT actions, merges, public deployment, billing or scope change has been authorized or executed.

## Independent closure request

Review **exactly `9313a4e9b3125545e08a07b1425beecbc62d01bc`** and its ancestry from reviewed `0f1e6a26…`, including all migrations and updated tests. Reproduce R1–R6 and examine old assumptions against the changed implementation; verify role revocation, immutable evidence, S3/ClamAV provenance, PDF resource isolation, post-commit worker replay and remaining transaction/concurrency failure points. Return independently determined GO or STOP with reproducible findings, paths/line numbers, severity and smallest safe changes. No developer assertion above substitutes for this decision.
