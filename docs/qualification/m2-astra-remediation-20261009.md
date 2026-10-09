# M2 — Astra STOP Findings R1–R9, Corrective Source and Executed Qualification

**Disposition:** CORRECTION CANDIDATE — CI QUALIFIED; independent Astra focused re-review **PENDING**. Do not initiate M3.

Private repository: `Electro-Anurag/employee-onboarding-companion`  
Branch: `feature/m2-template-case-dependency-foundation`  
Independent Astra rejected source: `2cb002c1ae40731fa1530a2c02c28978c64ee672`  
**Exact corrected/tested implementation: `e2e7bad089f26cf73375e6403ded760d9f9591f5`**  
CI: https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37909701209  
Chromium: https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37909701207  
Baseline main: `fc63b3dba2690f9989570ed6f98b84f112312283`, unchanged.

## Astra R1–R9 correction matrix

| ID | Applied source correction | Executed evidence and caveat |
|---|---|---|
| R1 — template version collision | `backend/templates/services.py`: revisions of new cloned versions start at prior version revision + 1, so stale v1/r2 cannot match a later v2/r2 under normal service writes. | Old approval, stale edit/publish denial, no new audit/content mutation, current edit passes. **Limit:** old persisted versions created before this change are not automatically renumbered; a version-specific ETag is possible additional defense and should be evaluated by Astra. |
| R2 — case creation receipt access | `backend/onboarding/commands.py`: receipt advisory lookup is followed by case-first locking, canonical User/Membership locks, fresh case/root and current HR assignment authorization before revealing historical response. | Historical replay after current HR transfer denied; ordinary replay retains exact response/receipt; no duplicate case/audit. |
| R3 — identity-switch UI | `frontend/src/App.tsx`: reset all account-specific template/editor, case/workspace, selectors, owner options and manager-attestation drafts; generation-token guards prevent an old read response repopulating new state. | Four-role Playwright scenario extended with same-page HR→IT login switch, held old /templates request, data-absence checks. Browser cancellation can settle an abandoned HTTP request; this test does not prove old server data was delivered. |
| R4 — completion without evidence | `backend/onboarding/migrations/0008_completion_provenance_and_snapshot_lock.py`: DEFERRABLE INITIALLY DEFERRED task-side evidence check at PostgreSQL COMMIT for completed Manager Preparation. Non-supported kinds and evidence-less terminal state reject. | Direct ORM updates on DOCUMENT and MANAGER_PREPARATION without accepted completion fail with SQLSTATE 23514; real Manager completion succeeds; completed timestamp clearing rejected. |
| R5 — mutable activated snapshot | Same migration freezes Task.available_at, Task.due_at and terminal metadata and freezes case.template_version_id upon/after activation; M1 legacy NULL shells not silently backfilled. | PostgreSQL immutable schedule/provenance update tests and exact rollback. |
| R6 — whitespace attestation | `commands.py`: trim first-week plan, buddy and note before length, persistence and hash; fail on meaningless normalized values. | Whitespace-only negatives produce no evidence/audit/receipt and no progress; normalized positive completes. |
| R7 — mixed-command lock cycle | `commands.py` create-case uses **unlocked hints → sorted User locks → sorted Membership locks**, then fresh authority recheck. Avoid actor-only User/Membership lock preceding lower-sorted IT owner. | Two concurrent connections with barrier and deliberately lower-sorted IT User successfully create a separate case and reassign a prior case; exact version/assignments/audit preserved. |
| R8 — stale availability | `backend/onboarding/state_machine.py` projects task state/actions read-only at request time based on clock, prerequisites and current owner; mutations still use locked authoritative recompute. | Clock-only eligibility and revocation test: READY and START action appear when availability time passes; owner-unavailable view blocks; supported action commits. Test uses Django service-level projection, not elapsed real-time browser. |
| R9 — cached employee readiness | `_command_case` no longer joins root/User before case lock; `_lock_case_authority` supplies freshly locked root/User and replaces case cached employee before readiness, credential/invite and availability checks. | Two-connection barrier tests commit unusable password or unavailable employee before authority lock, then deny activation with unchanged status/version and no tasks, receipt or activation audit. |

## Reviewer-requested test adequacy repairs

- The previously misleading late-dependency test now uses a **new same-case pair** (not a duplicate existing edge), asserting PostgreSQL 23514 and unchanged edge count.
- **Post-partial-write activation rollback** injects failure after writing tasks and at least one dependency, then verifies zero persisted tasks/edges/audit/receipts and unchanged case.
- **Post-evidence attestation rollback** injects failure after ManagerAttestation insertion, checking unchanged task/version and zero accepted evidence/audit/receipt.
- **Real PostgreSQL AND graph:** two supported Manager Preparation predecessors feed one child; first completion remains BLOCKED, second unlocks READY; unrelated independent task stays READY.
- M0/M1 regressions remain in the same CI suite.

## Evidence and limits

**CI run 37909701209:** success, **95/95 PostgreSQL-backed Python tests**, **2/2 React smoke tests**, M0 worker hard-kill recovery PASS, migrations/check, compiled frontend same-origin smoke, Docker image build, all/runtime npm audit zero reported findings at execution.

**Browser run 37909701207:** success, **1/1 sequential Chromium journey** with four synthetic roles, including expanded same-mounted-page identity switch. It is not a cross-browser/full hosted acceptance matrix.

The following are NOT claimed: live deployment, real employee data, production grants, hosted journeys, external integrations, independent M2 GO, or completion of M3–M10. Nonblocking Astra N1–N6 remain for later triage unless independent review promotes one to a demonstrated blocker.

**Next required action:** Astra should inspect exact source `e2e7bad089f26cf73375e6403ded760d9f9591f5` and both runs, evaluate R1–R9 including historical pre-fix template-version collision risk, and return a bounded M2 GO or source-specific STOP. Do not declare M2 independently closed merely from passing CI.
