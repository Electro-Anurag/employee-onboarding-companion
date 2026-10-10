# M5–M6 parallel development — source and acceptance ledger

**Date:** 10 October 2026. **Status:** implementation in progress; not a milestone qualification, independent GO or production authorization.

## Exact integration boundary

- Repository/authorized identity: `Electro-Anurag/employee-onboarding-companion` / `Electro-Anurag`.
- Target branch: `feature/m5-m6-parallel-development`.
- Fast-forward from `feature/m3-m4-integrated-workflows` commit `a77f70ee13a721b3e0566d26b09e8757cdd0a541`.
- Original M3–M4 branch and `main` were not modified by M5–M6 implementation.
- Real R2 web hard-exit recovery passed CI at the parent, pending independent source review.
- PRD v1.1 (28 requirements), Business Journey v1.0 (4 roles, 10 exception paths, J01–J05) and Technical Architecture & Engineering Handoff v1.0 are still governing. No reduced scope is approved.

## First M5 implemented slice

- `backend/notifications/` has PostgreSQL reminder identities and in-app inbox records, uniqueness constraint and recipient/status indexes.
- Reconciliation is based on persisted active-case/task/assignment state and task revision, with at-most-one current daily overdue reminder or due-soon reminder per action revision, and retirement of stale/previous delivery identities.
- Reconciliation supports 100-case cursor batches and explicit invocation via `python manage.py reconcile_m5_reminders` or the named `m5.reconcile_current_reminders` Procrastinate control task. The named control job now has a registered atomic continuation and a once-per-minute Procrastinate periodic entry point. A real worker generated a persisted overdue reminder in synthetic Chromium CI; separate 24-hour outage, multi-worker, startup immediacy, deployment and escalation gates remain open.
- `GET /api/v1/notifications` returns only authorized currently assigned in-app notifications; `POST /api/v1/notifications/{id}/read` persists a read timestamp and rechecks assignment authority. The React inbox tab supports refresh, mark read and authorized case drill-down.
- The initial review handoffs are implemented as a separate evidence-bound catalog described below; no fabricated email or calendar delivery. A first explicit exception lifecycle is implemented (details below). Recurring escalations, all edge-case handoff policies, complete versioned policy rules and external delivery remain to implement.

## Second M5 slice — source-verified exception recovery

- `backend/onboarding/migrations/0021_m5_exception_episodes.py` and additive `0022_m5_recurred_exception_supersession.py` hold one active exception for each task/cause, distinct numbered episodes, role-assigned ownership, and append-only transition events guarded by PostgreSQL triggers. A DB scope trigger rejects exceptions pointing at tasks from a different case.
- Case-locked idempotent `OPEN → ASSIGNED → RESOLVED → CLOSED` commands reuse M2 actor authorization, case-version preconditions, receipt and append-only case audit. Only a genuine unresolved predecessor, unavailable owner or overdue task can be raised. Resolution requires the actual underlying condition to clear; no generic exception action can complete a task.
- A problem returning while `RESOLVED` but before HR closure archives the previous episode as `SUPERSEDED` (not falsely verified `CLOSED`), writes distinct events, and opens a new episode. Repeated after closed also creates a new episode.
- `GET /api/v1/cases/{case}/exceptions`, `POST .../open`, and `POST .../{exception}/{assign|resolve|close}` plus case UI implement real episode creation, authorization, assignment, status guard, history and human confirmation.
- Developer PostgreSQL tests cover typed manager attestation as the ONLY path that removes a prerequisite, multi-episode recurrence, cross-tenant scope, CSRF/stale-version denial, historical immutability and retry receipts.
- **Real Chromium M5 journey and real periodic worker** passed [run 38019286959](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38019286959) at `f063ddadab597f0627dce9def3f1a982ede211f3`. The browser qualifies HR→Manager handoff and successful typed prerequisite recovery. The worker test qualifies one actual periodic current-state overdue inbox creation. Neither is hosted production qualification.

## Third M5 slice — joining-date change with DB-backed preview and HR decision

- `GET /api/v1/cases/{case}/joining-date/preview?joining_date=YYYY-MM-DD` is read-only, HR-scoped and requires the current If-Match case version. It returns a digest of the current case/template/task schedule and the exact old/new task timestamps. A preview performs no writes.
- `POST /api/v1/cases/{case}/joining-date/commit` is HR-only, CSRF-guarded, case-locked, idempotent and requires a verbatim preview digest, current case ETag and reason. Only PRE_JOINING cases can be moved within the bounded local-time window. Date changes for ACTIVE cases are NOT claimed.
- Snapshot scheduling uses the published immutable `TemplateTask.available_offset_days/due_offset_days` and local clock. A task with work-started or accepted/completed evidence is preserved unchanged; only untouched tasks shift. Recompute updates eligibility to READY/NOT_STARTED/BLOCKED without manufacturing completion.
- Additive migrations `0023` (durable schedule_revision, write-once CaseDateChange), `0024` (narrow M2 DB snapshot exception requiring an exact HR-authorized predeclared date-change record and published template schedule), and `0025` (deferred case-date revision evidence check at COMMIT) preserve old migrations. Arbitrary direct SQL deadline rewrites, past evidence rewrites and unapproved case-date edits are negative test cases. **Independent source/security review of the new M2-trigger exception remains mandatory**.
- Old M5 notifications are superseded inside the successful case transaction. Future reminder identities contain `case.schedule_revision` and cannot quietly replay an old due-time identity.
- React HR screen shows the previewed per-task changes, preserved task count and explicit reasoned approval. The existing Chromium test now includes real HTML interaction, HTTP commit receipt, reloaded joining date and earlier typed-evidence preservation.
- Qualification evidence from the additive migrations is **development-level only**, with exact final SHA and check results tracked in GitHub Actions; synthetic PostgreSQL and Chromium CI do not qualify hosted acceptance J01–J05.

## Fourth M5 slice — version- and recipient-bound review handoffs

- `backend/notifications/services.py` now reconciles evidence-backed `FORM_HR_REVIEW`, `FORM_CORRECTION`, `DOCUMENT_HR_REVIEW` and `DOCUMENT_CORRECTION` intents. Identities bind to the latest immutable submission/upload UUID, current task version, schedule revision and currently authorized recipient; no notification includes submitted answers, PDF bytes, upload filenames or reviewer notes.
- FORM handoff is generated only after the latest submitted `FormSubmission` is awaiting HR review; a real `FormReview.CHANGES_REQUESTED` switches it to the current employee. Revised submissions replace the old handoff; accepted evidence retires it.
- DOCUMENT handoff honors the two existing document boundaries. Synthetic fixture revisions require `VALIDATED_SYNTHETIC`; actual S3 versions are reviewable only when the exact latest `SecureUpload` has a `SecureCleanObject` sourced from a CLEAN scan. Quarantined, unscanned or unpromoted PDFs never trigger `DOCUMENT_HR_REVIEW`. Review rejection/clarification switches to the current employee.
- `GET /api/v1/notifications` and mark-read revalidate current case access, schedule revision, task version, exact latest immutable source UUID, handoff rule and current recipient. Former HR access is revoked immediately upon reassignment, before worker cleanup. The existing private inbox and case drill-down are reused; no invented auto-approval, email or calendar sending.
- Dedicated test `backend/notifications/tests/test_review_handoffs.py` uses real PostgreSQL commands for revision 1 → correction → revision 2 → approval, real synthetic document review, and the S3 clean-scan boundary (S3/scanner doubles here; actual live S3 regression remains separate). The isolated Chromium fixture and `browser/m5-exceptions.spec.cjs` extend the real periodic worker journey through two signed-in roles.
- Evidence: [focused PostgreSQL handoff suite](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38024572153) PASS on the first source slice. Whole-branch Chromium/backend runs at the added browser scenario SHA must complete before full developer acceptance can be claimed. External delivery, escalation and multi-worker/outage qualification remain OPEN.

## First M6 implemented slice

- `backend/ai/context.py`: reads one currently authorized case, task/dependency states, actual blocker identifiers and the server's eligible action IDs; omits uploaded document bodies and private form data.
- `backend/ai/validator.py`: bounded exact output fields; deny unknown source IDs, blocker IDs, action IDs, any tool-call field, or responses referring to a stale case version/context digest.
- `backend/ai/guidance.py` and `GET /api/v1/cases/{case}/companion/guidance` provide a functional, role-authorized, read-only deterministic fallback: three actually eligible next actions, predecessor/owner blocker facts and active exception episodes. The React case view labels it non-AI guidance; source IDs are exact existing task/exception records and action IDs cannot mutate the workflow.
- **Not a model response**. No provider call, real inference, policy-corpus publication, semantic truth validation, budget, request/attempt ledger or model API authorization has yet been implemented or qualified. The provider must never get workflow write tools. Tests of this foundation do not close M6.

## Qualification and follow-up order

1. Verify `.github/workflows/m5-m6-ci.yml` and `.github/workflows/m5-m6-browser-ci.yml` against the final code SHA: migration parity, PostgreSQL tests, React build, independent-role Chromium, real periodic worker and queue cursor. Do not transfer a prior SHA's PASS to a later source change.
2. Close any observed test failures without bypassing session guards, version checks or SQL uniqueness.
3. Finish M5: independently review the joining-date DB exception; implement policy-versioned exception notifications and 48-hour escalations, broader document/form-review handoff edge cases, 24-hour outage and multi-worker reconciliation, owner-unavailable remediation, and full temporal edge cases. The date-change slice covers PRE_JOINING only; do not claim full M5 closure.
4. Add real M6 AI request/attempt/answer persistence, approved synthetic policy evidence/citations, account-authorized provider adapter, strict structured-output validation, cost budget and end-to-end evaluator. Require owner-authorized inference account/budget for the real gate.
5. Re-review combined changes independently before milestone closure. Keep all J01–J05 hosted and production IAM/KMS/retention/security gates separately open.

No merge to `main`, real employee data, paid provider use, or public deployment is authorized by this ledger.
