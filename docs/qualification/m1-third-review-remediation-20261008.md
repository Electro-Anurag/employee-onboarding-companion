# M1 — Third independent STOP correction handoff

**Status:** CORRECTION CANDIDATE; ASTRA GO PENDING. M2 BLOCKED.

**Private repository:** Electro-Anurag/employee-onboarding-companion
**Branch:** feature/m1-security-review-remediation
**Prior rejected source:** 3f743d64cac0e4a41f29b11f160627eec9e4eaa4
**Exact corrected source to review:** 874f28a722c609475dc33274034bec63567855c4
**CI run:** https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37809199672
**Executed result:** success, 62/62 real PostgreSQL tests, M0 hard-kill/recovery, Django migration and consistency checks, React/Django smoke, Docker build, 0 npm advisory findings in all/runtime snapshots.
**Main:** fc63b3dba2690f9989570ed6f98b84f112312283, unchanged.

## Third-review delta — C4, C5, C6

### C4 — Historical reassignment receipt recovery

backend/onboarding/services.py preserves case-first and globally ordered User then Membership locks, followed by current actor/root authorization. Candidate identity/activity/availability checks no longer block a previously committed receipt; those eligibility predicates apply only when a new reassignment is being considered. Existing receipt lookup still validates actor, route, idempotency key, payload hash and case.

**CI regression:** Reassign IT, deactivate the target User and Membership, make target unavailable, recover the same result with the original key, reassign to another owner, recover the original result again. Confirm unchanged receipt and historical audit effects, deny a new command to the inactive candidate and deny replay after current HR actor revocation.

### C5 — Legacy migration preflight now actually executes

backend/onboarding/tests/test_second_review_closure.py creates malformed root/issuer/assignment relationships under rollback-only PostgreSQL transactions with the relevant relation guard disabled. The fixture setup is outside the expected exception. The actual migration 0004 PREFLIGHT_SQL is executed inside a savepoint, and tests assert the specific PostgreSQL SQLSTATE 23514 and the matching M1 migration-blocked message. Malformed root, issuer-only reference, assignment organization and assignment role are tested, as is a valid nonempty fixture.

**Scope:** This executes the real preflight against simulated legacy-shaped rows on the installed schema. It is not a full historical migration replay from 0001.

### C6 — Error outcome attribution respects transaction phase

backend/accounts/views.py splits credential/token/audit commit from subsequent session hash rotation. A forced database error in session refresh after an actual credential commit produces a sanitized 503 with outcome COMMAND_COMMITTED and session_state UNKNOWN. Changed password, revoked token and one audit persist. A separate in-transaction audit error rolls the credential operation back. Logout mutations now use the indeterminate error path rather than a false preflight/rollback label.

**Scope:** Known SQLSTATE errors were injected at handler boundaries; the test does not sever PostgreSQL TCP while COMMIT is acknowledged. Astra previously found physical transport disruption not independently M2-blocking.

## Immutable review boundary

This is an M1 CI-qualified candidate, not an independent security GO. No M2, paid provisioning, cloud deployment or public publishing. Approved React + Django + PostgreSQL + Procrastinate architecture unchanged.

Astra should re-review exactly 874f28a722c609475dc33274034bec63567855c4 and run 37809199672, check C4/C5/C6 source and test evidence, then give M1 REVIEW GO, M1 REVIEW STOP or REVIEW BLOCKED with exact remaining blockers. M2 additionally requires owner authorization.
