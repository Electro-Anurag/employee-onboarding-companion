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
- Reconciliation supports 100-case cursor batches and explicit invocation via `python manage.py reconcile_m5_reminders` or the named `m5.reconcile_current_reminders` Procrastinate control task. **A production recurring scheduler and startup catch-up trigger are not installed yet.**
- `GET /api/v1/notifications` returns only authorized currently assigned in-app notifications; `POST /api/v1/notifications/{id}/read` persists a read timestamp and rechecks assignment authority. The React inbox tab supports refresh, mark read and authorized case drill-down.
- The initial reminder catalog intentionally excludes document/form review handoffs because recipient routing must not invent an action owner; no fabricated email or calendar delivery. Recurring escalations, schedule changes, explicit exception lifecycle, owner-unavailable recovery and policy-versioned rules remain to implement.

## First M6 implemented slice

- `backend/ai/context.py`: reads one currently authorized case, task/dependency states, actual blocker identifiers and the server's eligible action IDs; omits uploaded document bodies and private form data.
- `backend/ai/validator.py`: bounded exact output fields; deny unknown source IDs, blocker IDs, action IDs, any tool-call field, or responses referring to a stale case version/context digest.
- **Not a model response**. No provider call, real inference, policy-corpus publication, semantic truth validation, budget, request/attempt ledger or model API authorization has yet been implemented or qualified. The provider must never get workflow write tools. Tests of this foundation do not close M6.

## Qualification and follow-up order

1. Run `.github/workflows/m5-m6-ci.yml` against exact branch HEAD: migration parity, genuine PostgreSQL backend tests, existing regression suite, React tests and build.
2. Close any observed test failures without bypassing session guards, version checks or SQL uniqueness.
3. Complete M5 exceptions and predicates, date-change preview/commit and scheduling revisions, true periodic reconciliation/catch-up, and stale owner suppression including real Chromium/worker-restart tests.
4. Add real M6 AI request/attempt/answer persistence, approved synthetic policy evidence/citations, account-authorized provider adapter, strict structured-output validation, cost budget and end-to-end evaluator. Require owner-authorized inference account/budget for the real gate.
5. Re-review combined changes independently before milestone closure. Keep all J01–J05 hosted and production IAM/KMS/retention/security gates separately open.

No merge to `main`, real employee data, paid provider use, or public deployment is authorized by this ledger.
