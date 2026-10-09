# Employee Onboarding Companion — Focused Astra M2 R2/R3/R5 Requalification

**Date:** 2026-10-09  
**Disposition:** Corrective implementation and executable evidence **PASS**; **independent Astra final GO/STOP still pending**. No M3, real data, paid provision, public deployment or main merge.

## Exact identities

- Private repository: `Electro-Anurag/employee-onboarding-companion`
- Branch: `feature/m2-template-case-dependency-foundation`
- Last independently rejected SHA: `dd97763c5210b9f2f9a39ec099fe3933b3b8ae11`
- **Exact qualified corrective source SHA:** `d471b9f9c6d0225afb637e1afdb319e1c0356c7b`
- [M0–M2 PostgreSQL/frontend CI, 99/99 backend + 2/2 React](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37919310761) — success at `d471b9f9c6d0225afb637e1afdb319e1c0356c7b`
- [Real Playwright Chromium, 2/2 scenarios](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37919310640) — success at `d471b9f9c6d0225afb637e1afdb319e1c0356c7b`
- Original main remains `fc63b3dba2690f9989570ed6f98b84f112312283`.

## Independent assessment being answered

The uploaded focused Astra review concluded **M2 REVIEW STOP — CORRECTIONS REQUIRED**. It verified R1, R4, R6–R9 and T1–T4, but reported:
- **R2** insufficient independent original-caller User/Membership revocation and active organization replacement tests.
- **R3** startup `/auth/me` could replace a newer signed-in identity; prior Chromium race canceled/stalled a request without proving delivery of a successful stale payload.
- **R5** an activated case could be reset to CREATED, strip its template binding, then return ACTIVE (and potentially change topology).

## Corrected source and dedicated evidence

| Finding | Corrective source | Executable acceptance |
|---|---|---|
| R2 | The already corrected `create_case` receipt path in `backend/onboarding/commands.py` is unchanged. | Two new real PostgreSQL tests revoke original HR User, revoke original HR Membership, then replace the original active membership with another organization's HR Membership. Historical receipt access denies (404) without altering cases/audit/receipts. Authorized replay returns the original committed result. |
| R3 | `frontend/src/App.tsx`: startup identity fetch captures an auth generation and checks it after CSRF and JSON reads. Sign-in and sign-out invalidate older work **before** network transitions begin. | New `browser/identity-race.spec.cjs`: Playwright captures an actual HR-A `/auth/me` JSON body; delivers a successful old 200 response after HR-B login in the same mounted page; asserts HR-B remains. It separately fulfills a successful organization-A `/templates` 200 **after** HR-B login, asserts no organization-A template displays. Failure/cancellation is not accepted as delivery. |
| R5 | Additive `backend/onboarding/migrations/0009_irreversible_activated_case.py` replaces the previous SQL trigger function. It disallows **any post-activation transition back to CREATED** using PostgreSQL SQLSTATE 23514. Existing template immutability remains. | New real PostgreSQL regression attempts `ACTIVE → CREATED → template_version=NULL → ACTIVE` plus a novel edge; SQLSTATE 23514 rejects the initial reset. After rollback, status/version/template binding/task-edge count/audit remain unchanged. Existing CREATED activation and PRE_JOINING Day 1 tests continue to pass. |

### Qualification adequacy

- Python: **99 passing real PostgreSQL tests**, including the three new R2/R5 tests; app migration/checks and existing M0/M1 regressions passed.
- React: **2/2 existing static smoke tests passed** (not claimed to test asynchronous state).
- Playwright: **2/2 real Chromium scenarios passed**: original four-role journey plus new delivered-successful-response R3 scenario with two independent synthetic HR organizations.
- M0 hard-kill worker recovery, compiled frontend same-origin preflight, Docker build and npm audits passed in the corresponding successful CI runs (zero advisories reported by npm at the time).
- Synthetic HR-B is created only using `--include-second-hr` with `--confirm-synthetic` and DEBUG enabled; generated credentials remain in a restricted temporary CI runner file, never committed to the repo.

### Scope and limits

This is **developer qualification**, not independent Astra approval. The previous report's verified R1, R4, R6–R9 and T1–T4 remain supported by their earlier source/regression evidence and the complete green M0–M2 suite. Nonblocking N1–N6 have not been reclassified. No hosted acceptance, production database grants, externally delivered invitations, real employee evidence workflows or cross-browser matrix is claimed.

**Next action:** Astra reviews precisely `d471b9f9c6d0225afb637e1afdb319e1c0356c7b` with the two latest CI runs and the uploaded prior focused STOP report, confirms whether R2/R3/R5 and their negative tests meet the closure standard, and returns `M2 REVIEW GO` or a source-specific `M2 REVIEW STOP`. M3 implementation remains unauthorized.
