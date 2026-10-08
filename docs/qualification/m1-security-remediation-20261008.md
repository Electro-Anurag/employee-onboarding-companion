# M1 Adversarial Security Remediation — Source and CI Handoff

**Status:** REMEDIATION CANDIDATE; INDEPENDENT ASTRA RE-REVIEW REQUIRED — not an M2 GO.  
**Date:** 2026-10-08  
**Repository:** Electro-Anurag/employee-onboarding-companion (private)  
**Repair branch:** `feature/m1-security-review-remediation`  
**Reviewed predecessor source:** `daf164c583ab472a332b087905e8f95cf7bd849e`  
**Pre-repair documentation HEAD:** `e211a017687af00af40e2fca2ab78074a442f6f7`  
**Exact corrected source tested:** `d4400358be0aaa81a0158a4147e06cae423890ac`  
**CI evidence:** https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37782660451  
**CI result:** success; **40/40 pytest tests passed**, PostgreSQL migrations/healthchecks, M0 worker hard-kill replay, restricted audit-role SQL probes, same-origin React/Django smoke, Docker build, frontend bundle compilation.  
**Frontend package audit:** Vitest upgraded to 5.0.3, committed lockfile; npm audit ALL 0 and npm audit --omit=dev 0 in exact CI run. These are snapshot results, not permanent vulnerability guarantees.

## Review findings and correction ownership

| Astra ID | Corrective implementation | Executed regression/evidence | Reviewer outcome |
|---|---|---|---|
| R1 — stale tokens after password change | `accounts/security.py`: stable user-row lock, all-purpose token invalidation and password recheck after lock; `accounts/views.py` atomic audit | Cross-purpose reset/invite revocation, stale-old-password race, old session invalidation | Candidate closed; Astra to verify |
| R2 — stale HR credential issuance | `onboarding/services.py`: case-lock first, actor user/membership lock and recheck; target user/membership lock and recheck; consistent guarded ownership change | Real two-connection reassignment-before-issuance, employee deactivation-before-issuance, inactive actor checks | Candidate closed; Astra to verify |
| R3 — inconsistent organization/role references | `onboarding/migrations/0002_relation_guards.py`, `0003_member_identity_guard.py`: cross-table PostgreSQL triggers, role/time constraints, prevent case-linked membership user transfer; `onboarding/services.py` unified org/role scoping | Invalid cross-org employee/case/assignment, role mismatch, future-start denial, membership identity-transfer rejection | Candidate closed; Astra to verify |
| R4 — concurrent pending credentials | `accounts/security.py`: stable user row lock before invalidation and issue, pending user/purpose unique backstop in `accounts/migrations/0002_security_constraints.py` | Parallel two-connection issuance, only one pending token, same-token redemption | Candidate closed; Astra to verify |
| R5 — admission races and unthrottled redeem | `accounts/security.py`: transaction advisory locks sorted by bucket, reserved attempt budgets for login and redemption; independent account/IP and token/IP limits | Parallel nine-request login admission, account/IP and redemption budgets, original sequential auth checks | Candidate closed; Astra to verify |
| R6 — ambiguous active membership | `accounts/models.py` + migration: global partial unique active-user membership; `actor_context` exact get/fail closed | Second active organization membership rejected at DB, zero-context denial | Candidate closed; Astra to verify |
| R7 — wrong audit assignment UUID | `onboarding/services.py`: retain the newly created assignment and record its PK separately from member ID | Audit previous/new assignment IDs resolve to actual persisted rows and same case/role | Candidate closed; Astra to verify |
| R8 — unbounded command failures | `onboarding/services.py` 5s statement/2s lock timeout; `accounts/security.py` bounded auth/credential transaction waits; `common/http.py` sanitized retryable DB errors; cross-case idempotency-key serialization | Held row lock returns bounded 409, no partial effects, same-key retry/replay exactly one outcome, cross-case duplicate key controlled | Candidate closed; Astra to verify |
| N1 — malformed UUID types | `common/http.py` typed UUID validation; account and case views adopt it | Null/number/list/object malformed input yields bounded 422 | Adjacent fix implemented |

## Scope and evidence limits

- The prior source passed 23 tests before Astra's review; the corrected branch now passes **40**, including explicit adversarial scenarios.
- M0 queue transactional recovery continues to pass. The M1 audit command is transactionally committed and receives separate rollback/one-effect tests, but the future complete job-orchestration path is not yet implemented.
- CI uses a PostgreSQL-owner identity for Django/runtime and separately probes limited audit roles. **Actual least-privilege runtime/worker provisioning remains a hosting milestone**.
- This is source/test evidence, **not** a live penetration test, multi-user hosted Playwright qualification, field security of real employee documents, operational backup/restore qualification or production readiness.
- The accepted PRD v1.1 and Business Journey v1.0 remain governing scope. No task, document, IT, training, AI or complete Day-30 workflow was added to M1.
- The private repository has not been made public; no paid cloud/API service or hosted deployment was provisioned.

## Required independent reviewer decision

Review the exact corrected source SHA `d4400358be0aaa81a0158a4147e06cae423890ac`, its migrations/call paths and the CI run `37782660451`. Compare against Astra's previous R1–R8 findings and challenge each candidate closure. If a confirmed M2-blocking defect remains, return `M1 REVIEW STOP — CORRECTIONS REQUIRED` with smallest source-level correction and test. Only after a justified independent GO and owner authorization may M2 start.
