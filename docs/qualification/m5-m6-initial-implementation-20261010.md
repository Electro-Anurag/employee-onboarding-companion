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
- The initial reminder catalog intentionally excludes document/form review handoffs because recipient routing must not invent an action owner; no fabricated email or calendar delivery. A first explicit exception lifecycle is implemented (details below). Recurring escalations, all document/form review handoffs, joining-date changes, owner-unavailable remediation, complete versioned policy rules and external delivery remain to implement.

## Second M5 slice — source-verified exception recovery

- `backend/onboarding/migrations/0021_m5_exception_episodes.py` and additive `0022_m5_recurred_exception_supersession.py` hold one active exception for each task/cause, distinct numbered episodes, role-assigned ownership, and append-only transition events guarded by PostgreSQL triggers. A DB scope trigger rejects exceptions pointing at tasks from a different case.
- Case-locked idempotent `OPEN → ASSIGNED → RESOLVED → CLOSED` commands reuse M2 actor authorization, case-version preconditions, receipt and append-only case audit. Only a genuine unresolved predecessor, unavailable owner or overdue task can be raised. Resolution requires the actual underlying condition to clear; no generic exception action can complete a task.
- A problem returning while `RESOLVED` but before HR closure archives the previous episode as `SUPERSEDED` (not falsely verified `CLOSED`), writes distinct events, and opens a new episode. Repeated after closed also creates a new episode.
- `GET /api/v1/cases/{case}/exceptions`, `POST .../open`, and `POST .../{exception}/{assign|resolve|close}` plus case UI implement real episode creation, authorization, assignment, status guard, history and human confirmation.
- Developer PostgreSQL tests cover typed manager attestation as the ONLY path that removes a prerequisite, multi-episode recurrence, cross-tenant scope, CSRF/stale-version denial, historical immutability and retry receipts.
- **Real Chromium M5 journey and real periodic worker** passed [run 38019286959](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38019286959) at `f063ddadab597f0627dce9def3f1a982ede211f3`. The browser qualifies HR→Manager handoff and successful typed prerequisite recovery. The worker test qualifies one actual periodic current-state overdue inbox creation. Neither is hosted production qualification.

## First M6 implemented slice

- `backend/ai/context.py`: reads one currently authorized case, task/dependency states, actual blocker identifiers and the server's eligible action IDs; omits uploaded document bodies and private form data.
- `backend/ai/validator.py`: bounded exact output fields; deny unknown source IDs, blocker IDs, action IDs, any tool-call field, or responses referring to a stale case version/context digest.
- `backend/ai/guidance.py` and `GET /api/v1/cases/{case}/companion/guidance` provide a functional, role-authorized, read-only deterministic fallback: three actually eligible next actions, predecessor/owner blocker facts and active exception episodes. The React case view labels it non-AI guidance; source IDs are exact existing task/exception records and action IDs cannot mutate the workflow.
- **Not a model response**. No provider call, real inference, policy-corpus publication, semantic truth validation, budget, request/attempt ledger or model API authorization has yet been implemented or qualified. The provider must never get workflow write tools. Tests of this foundation do not close M6.

## Qualification and follow-up order

1. Verify `.github/workflows/m5-m6-ci.yml` and `.github/workflows/m5-m6-browser-ci.yml` against the final code SHA: migration parity, PostgreSQL tests, React build, independent-role Chromium, real periodic worker and queue cursor. Do not transfer a prior SHA's PASS to a later source change.
2. Close any observed test failures without bypassing session guards, version checks or SQL uniqueness.
3. Finish M5: date-change preview/commit and schedule revisions, exception notifications and 48-hour escalations, document/form-review handoffs, verified 24-hour outage/multi-worker reconciliation, and owner-unavailable recovery. The current predicate-gated exception and periodic worker slices are not full M5 closure.
4. Add real M6 AI request/attempt/answer persistence, approved synthetic policy evidence/citations, account-authorized provider adapter, strict structured-output validation, cost budget and end-to-end evaluator. Require owner-authorized inference account/budget for the real gate.
5. Re-review combined changes independently before milestone closure. Keep all J01–J05 hosted and production IAM/KMS/retention/security gates separately open.

No merge to `main`, real employee data, paid provider use, or public deployment is authorized by this ledger.
