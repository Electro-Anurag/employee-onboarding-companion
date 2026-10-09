# Employee Onboarding Companion — Independent M3–M4 Source Review Handoff

**Prepared:** 2026-10-09  
**Status:** Developer-corrected source and CI qualified; **independent Astra GO/STOP has not occurred**. This document is not an independent review verdict.

## Exact source identity and isolation

- Authorized private repo: `Electro-Anurag/employee-onboarding-companion`; authorized account: `Electro-Anurag`.
- Review branch: `feature/m3-m4-integrated-workflows`.
- **Exact code baseline to audit:** `0f1e6a26f1f22bc79c33de9d99e6b3cfdbfc5c9e` (handoff documentation may be committed later; do not silently substitute HEAD).
- `main` remains `fc63b3dba2690f9989570ed6f98b84f112312283`.
- No merge, production deployment, customer-system integration, real employee data, or independent Astra review is represented as complete.
- Governing baseline: Employee Onboarding Companion PRD v1.1, business journeys, M0–M2 qualified security and dependency controls, and original submission requirements. This handoff does not reduce that scope.

## Qualification evidence at the exact code SHA

1. [Python/PostgreSQL, React, migrations, Docker and worker-recovery CI](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37964794785) — SUCCESS; **132 passed, 1 skipped** Python cases; **2 React tests passed**, zero npm vulnerabilities reported. The skipped test requires live services.
2. [Real Chromium acceptance CI](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37964794824) — SUCCESS; **3 browser scenarios passed**, including four-role task flows, identity-race guard mutation control, M4 synthetic quizzes and activity controls.
3. [Actual MinIO/S3 versioning and actual ClamAV integration](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37964794792) — SUCCESS; generated PDF with embedded standard EICAR signature rejected, clean replacement scanned and promoted, exact-version S3 checks, HR accepted, and typed task completion verified.
4. None of these represents an external security penetration test, production IAM/KMS validation, real-worker crash/restart qualification of the **M3** task, or a deployed hosted user acceptance run.

## Review targets: complete M3 path

Employee authenticated upload intent `backend/documents/real_commands.py:prepare` → `receive` → private version-pinned S3 quarantine `storage.py` → transactional Procrastinate enqueue `backend/jobs/atomic.py` → worker `backend/jobs/tasks.py` → fail-closed ClamAV `scanner.py` → immutable scan outcome and verified clean S3 object `real_models.py` / `real_commands.py:scan_one` → authorized HR review `real_commands.py:review` → `SECURE_DOCUMENT` typed completion and task-dependency recomputation.

- `backend/documents/real_views.py`: role/case-scoped routes, CSRF, idempotency, exact-version authorized downloads and scan-status metadata.
- `backend/documents/migrations/0003_s3_secure_documents.py` and `backend/onboarding/migrations/0017_secure_s3_document_completion.py`: append-only evidence, relational approval provenance, typed completion.
- The original synthetic text-document path is separate. Older disabled-by-default `quarantine_*` code is an **experimental** PostgreSQL-byte quarantine, not an alternative production document path.

## Review targets: complete M4 path

- `backend/provisioning/`: synthetic IT requests, simulated failure and explicit retry, independent human confirmation, equipment receipt and dependency effects. Do **not** claim actual external IT provisioning.
- `backend/activities/`: versioned schedule, cancellation, reschedule, elapsed attendance, organizer role, and dependent-task unlock. No external calendar invite is claimed.
- `backend/training/`: frozen module hash and version, answers hidden from public module response, server-side grading, retry, immutable typed completion.
- `backend/onboarding/migrations/0015_training_completion.py`, `0016_activity_completion.py`, `0018_restore_activity_cancellation_authority.py`: database-level evidence and cancellation authority.
- `browser/m4-evidence.spec.cjs`: employee failed quiz/retake; HR schedule/cancel/reschedule; elapsed synthetic occurrence HR attendance; blocked successor unlock; cross-role UI boundaries.

## Developer source-audit findings corrected before handoff

1. **M3 transactional job creation** — `85acf960c3666be402791fc56e971df467d2a5ad`: replaced ordinary `scan_secure_document.defer()` with `defer_atomic()`, registered only the matching enqueue-only task contract, and added PostgreSQL fault injection after job creation to demonstrate joint queue/receipt/object-evidence rollback and successful retry.
2. **M3 stalled scan starvation** — `2d0041625275289c45f695276f6a453bc266a87f`: eliminated reconciliation's oldest-100 scan of unreceived/terminal intents; PostgreSQL selects eligible actionable scans/promotions before the bounded work limit. Added a historical-intent stress regression.
3. **M3 background scanner retry** — `0f1e6a26f1f22bc79c33de9d99e6b3cfdbfc5c9e`: scanner/promotion failure states no longer silently ACK as successful jobs. Added bounded delayed Procrastinate retries (3 retries, 30s); malware is terminal, not auto-retried. M3 worker-level retry strategy has an executable test, **not yet a real-worker outage/restart end-to-end test**.
4. **M4 cancellation trigger integrity** — `ba07e4a9c79f8d0589d12016fa8926b1c248225d`: additive migration restored the cancelled-occurrence rejection lost when M3 altered the shared PostgreSQL attendance function; direct-SQL regression demonstrates rejection after the cancelled meeting time has elapsed.
5. **M3 interrupted upload version replay** — `f5112c14ab9cdcc7de1d37fa25914e49be8f414a`: only S3 412 precondition conflicts can recover an exact version after verifying bytes and SHA-256; historical committed receipt remains replayable across newer document revisions.

## Adversarial questions that remain OPEN for independent assessment

- Can account/membership/assignment revocation or cross-tenant IDs expose metadata, upload/download bytes, or historical review receipts? Test concurrent role changes during S3 I/O.
- Can an attacker cause forged clean scan/provenance, stale object promotion, unauthorized HR acceptance, unverified download, or premature dependent-task completion? Evaluate DB triggers, not just HTTP guards.
- Does `scan_one()` holding DB transaction/row lock during network scanner and S3 I/O cause bounded timeouts, deadlocks or loss of forward progress under outages? Qualify worker hard-kill/restart and re-delivery on **M3 itself**.
- Is the final `ERROR` after the bounded scan-attempt ceiling operator-recoverable without privileged evidence alteration, and how is a stuck user's document safely replaced or escalated?
- What occurs when a quarantine S3 write commits but DB finalize does not, or clean promotion succeeds in S3 but a later DB transaction rolls back? Check idempotency and orphan lifecycle.
- Do the actual planned hosting IAM policies ensure tenant isolation, version immutability, separate private buckets, object retention/deletion, least privilege and required KMS encryption? Current MinIO CI is not a production AWS authorization/retention test.
- Can malformed/active PDFs abuse the local pypdf parse boundary? No claim is made of PDF sandboxing or sanitization.
- Do M4 role changes, meeting cancellation, future timestamp manipulation, attendance fraud, IT simulated failure replay, and training module-version changes defeat typed completion barriers?
- Validate that the UI shows only actually functioning actions; no fake buttons or claimed external integrations.

## Requested independent disposition

Return **M3–M4 REVIEW GO** or **M3–M4 REVIEW STOP — CORRECTIONS REQUIRED** at the exact code SHA above. For each finding provide severity, source path/function, reproducible scenario, current-test coverage/gap, and smallest safe fix; distinguish product-demo acceptance from production readiness.

**STOP** on any untrusted clean-document approval, cross-tenant/private-byte leak, forged typed completion, broken idempotency under retry, lost committed scan job, unsupported synthetic-vs-real claim, or source-level authorization bypass. Never infer PASS from existing green CI alone. No merge/deployment without owner authorization and independently accepted gates.
