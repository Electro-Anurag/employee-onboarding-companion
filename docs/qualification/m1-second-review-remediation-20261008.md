# M1 focused re-review — second STOP remediation handoff

**Decision state:** RE-REVIEW CANDIDATE; M2 BLOCKED until Astra issues an evidence-grounded GO and the owner authorizes M2.

**Private repository:** Electro-Anurag/employee-onboarding-companion  
**Branch:** `feature/m1-security-review-remediation`  
**Astra's second rejected baseline:** `d4400358be0aaa81a0158a4147e06cae423890ac`  
**New exact tested implementation:** `3f743d64cac0e4a41f29b11f160627eec9e4eaa4`  
**CI run:** https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37788617691  
**CI result:** success, 56/56 PostgreSQL-backed pytest tests, M0 hard-kill worker replay, Django migrations/check, frontend production build, same-origin smoke, restricted audit-role SQL probes, Docker build, npm audit all/runtime zero snapshot.  
**Original `main`:** `fc63b3dba2690f9989570ed6f98b84f112312283` (unchanged).

## Scope of this corrective delta

This update addresses Astra's focused re-review dated 8 Oct 2026, which marked R1/R4/R6/R7/N1 closed, and R2/R3/R5/R8 partially closed. No M2 domain, task workflow or deployment was added. The underlying approved React + Django + PostgreSQL + Procrastinate architecture is unchanged.

| Finding | Corrected owner and guarantee | Executed regression evidence |
|---|---|---|
| R2 and C1: cross-case user lock cycle / stale authority | `backend/onboarding/services.py` uses case-only `FOR UPDATE`, then sorted User row locks, then sorted Membership row locks; ID hints revalidated after locks; no joined incidental locks in the initial case query. Both issuance and reassignment use the same helper. | Two opposing HR-owner cases start concurrently using an internal after-case-lock Barrier; both commit without circular user locking. Additional in-flight employee/candidate revocation at a deliberate case-lock boundary denies without token/event/receipt. Prior revocation/reassignment regressions retained. |
| R3: invalid relationship updates and legacy migration | `onboarding/migrations/0004_immutable_roots_and_issuer_guard.py` makes case employee/organization roots immutable, blocks identity/role/org changes to an issuer-only assigned_by membership, and fails preflight on invalid legacy rows while holding write-excluding schema-table locks. | Direct SQL/ORM invalid updates rejected, inconsistent legacy case and issuer rows rejected by preflight. Both parent-first and child-first concurrent case/assignment schedules observed a real PostgreSQL Lock wait and ended valid, or rejected the forbidden reparent. |
| R5 and C2: rejected login storage growth | `backend/accounts/security.py` acquires deterministic advisory locks, examines both budgets, then creates/resets/increments counters **only after** full admission; denial does not persist a newly requested identity bucket. | Exhausted IP followed by 120 previously unseen rejected identifiers leaves counter-row count unchanged. Concurrent login limit, 15-minute window recovery, per-account/IP and invalid-token HTTP redemption budgets passed. |
| R8: errors/timeouts/uncertain reply | `backend/accounts/views.py`, `middleware.py`, `common/http.py`, `onboarding/views.py` catch live preflight/session database failures and provide sanitized errors. Known PostgreSQL aborts are retryable 409/ROLLED_BACK; generic failure response denotes UNKNOWN, does not claim rollback, and never auto-replays. | Preflight outage injections return 503 and no actions; real 2s lock timeout returns bounded 409 with no effects; after release same-key replay commits once. Database SHOW asserts effective local timeout and reset after transaction. An artificially discarded response after a confirmed commit is recovered using the same receipt/key with one audit/version. **No true network disconnect during COMMIT was executed.** |
| C3: missing owner role | `backend/onboarding/views.py` uses typed optional input then service validation | Omitted role is bounded 4xx with no state/audit/receipt |
| CI read-only integrity | `.github/workflows/m1-ci.yml` uses contents:read; installs from committed package-lock via npm ci; checks no lockfile diff; rejects npm audit service errors and any currently reported advisories. No CI self-commit step. | Latest CI succeeded at exact tested source with zero npm advisories in both reports; no dependency lock regeneration. |

## Evidence limitations (retain as reviewer questions)

- These are executed CI checks of a synthetic local/CI system. **No production or hosted deployment** and no real employee data, external API or cloud resources.
- Database/runtime access is still qualified using a CI schema-owner identity and temporary restricted audit-role probes. Final runtime/worker role grants must be qualified at the established deployment gate.
- Session expiry/CSRF and M1 account features remain exercised by Django test clients; there is no deployed browser/Playwright acceptance claim.
- The opposing HR test uses a deterministic service barrier after both case rows lock. The parent/child tests inspect `pg_stat_activity.wait_event_type='Lock'`; these are stronger than 100 ms sleeps, but do not model every possible external administrator transaction.
- The lost-response test intentionally discards an already-committed result; it **does not** sever TCP during COMMIT acknowledgment. The latter remains an infrastructure fault-injection/indeterminate-outcome limitation. Database code never blindly replays a write following an ambiguous outcome; idempotent commands can query the receipt with the same actor/key/payload after authorization.
- No general PostgreSQL deadlock fault-injection case was executed; the new reciprocal-HR test verifies the identified lock cycle is avoided. Abort mapping is covered by actual held-lock timeout.
- The immutable case root contract is M1-specific. If later scope requires owner-authorized root transfers, they need explicit future architectural/data migration review, not silent mutation.
- Astra's independent GO is **not** inferred from 56 green tests. The next review should inspect this exact source and adjudicate R2, R3, R5 and R8 against its own specific second review.

## Final stage disposition

**M1 correction candidate is CI-qualified, not independently approved.** Re-review against `3f743d64cac0e4a41f29b11f160627eec9e4eaa4` and run `37788617691`. If STOP, request source-level minimum delta and exact verification. If GO, request owner approval before starting M2.
