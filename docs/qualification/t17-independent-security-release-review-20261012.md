# T17 Independent Security & Release Source Review — exact-state packet

**Review status: PENDING. This packet is NOT independent approval.**
**Date:** 12 October 2026. **Private repository:** `Electro-Anurag/employee-onboarding-companion`, **authorized account** `Electro-Anurag`, branch `feature/eoc-completion-development`. Do not access unrelated accounts/repositories or incorporate confidential employer or other project materials.

## 1. Reviewer assignment and immutable scope

Act as an **independent principal application security and adversarial release reviewer**. Read the actual repository code and immutable CI logs, not solely this summary. Evaluate the **exact final source SHA** before issuing any determination. The last application/workflow changes tested include **`b2765403e2c7f477c137351163364d8c389a1d37`** (D6 coordinated recovery). Subsequent documentation-only commits do not replace code-level test evidence; independently confirm branch HEAD and compare diffs.

Authoritative requirements: PRD v1.1 F01–F28, Business Journey v1.0 E01–E10, and hosted acceptance J01–J05. Do not silently narrow these requirements. Read `docs/qualification/d4-requirements-exception-traceability-20261012.md`, `docs/tracking/release-test-gates-20261011.md`, and `docs/handoffs/eoc-continuation-2026-10-12.md`.

The requested outcome is an **adversarial SOURCE-level T17 verdict** with evidence for each check, not authorization to deploy or incur cloud/AI charges.

## 2. Independently verified candidate evidence to challenge

| Subsystem | Exact evidence and expected scope |
| --- | --- |
| Full integration at latest D6 document-verifier source | [38218007460](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38218007460) **SUCCESS** at `b6a4ac9307c63eac5fbe57cbe04c0ecdf5b3c6a2`: PostgreSQL backend, React, Docker, four-role genuine Chromium. General suite skips 6 dedicated live service cases. |
| Real private S3, real ClamAV, version receipts and missing-version fail closed | [38219586182](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38219586182) **8/8 PASS** at `829f9e69de8972d248a88db74b1d086d63b1f367`; six legacy and two new exact-version recovery probes. |
| Full coordinated offline synthetic MinIO + PostgreSQL restoration | [38221427909](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38221427909) **SUCCESS** at `b2765403e2c7f477c137351163364d8c389a1d37`, exact restored S3 VersionId, hash, audit, receipt and migration fingerprint. Same local MinIO engine and filesystem. |
| Multi-role, CSRF/IDOR, denied mutation, state concurrency | [38208898601](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898601) **25 PostgreSQL tests PASS** at `4e078c20`, selected cross-tenant endpoints and inbox error handling. |
| Historical database upgrades | [38207921011](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38207921011) **PASS** for four populated histories: two valid full forward, two contradictory fail-closed. |
| Real background crash/recovery and periodic notifications | [38208898591](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898591) and [38208898616](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898616) **PASS**: PostgreSQL, worker hard kill/resume, Chromium exceptions. |
| Actual elapsed scheduling + rescheduling | [38204925335](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38204925335) **10 backend and 2 real elapsed Chromium PASS**. |
| Keyboard, narrow viewport, four-role automated WCAG A/AA | [38212201996](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38212201996) **4 real Chromium PASS**, zero axe violations in scanned states at `93868cf6`. Not a full WCAG/manual screen-reader audit. |
| Database-only physical snapshot and restoration | [38209892920](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38209892920) **PASS** on synthetic evidence. |
| Latest hosted status | The last recorded public hosted deployment is at **old SHA `ded82f9ca85213eb7bbc50ceb3eb81f4864b92f2`**, documented in `docs/qualification/hosted-acceptance-ledger-20261011.md`; no current-code hosted promotion is evidenced. All J01–J05 remain **0/5 QUALIFIED**. |

**Crucial:** a green test is proof only for the tested configuration. Find omissions and adversarial counterexamples rather than presuming PASS for full requirements.

## 3. Adversarial review checklist and required failure evidence

1. **Authorization and tenancy:** case/employee/org/role membership, deactivated users, multiple memberships, revoked assignments while a large response is streaming, cross-case task ID swaps, credential invitation/reset issuance, HR-only action restrictions, multi-role active browser sessions, cache headers.
2. **Authentication/CSRF/session:** real Django CSRF on all mutation routes; incorrect/content-type HTTP; login throttle and token-race behavior; absolute session expiry and logout/password reset revocation; HTTP-only secure cookies, proxy/TLS and origin/trust boundaries.
3. **State integrity and idempotency:** PostgreSQL advisory lock order, optimistic versions, idempotent receipt replay, historical receipt after owner/case closure, transaction commit uncertainty, zero audit on unauthorized write; concurrent HR, IT, worker and employee changes.
4. **Secure-document saga:** PDF type/content validation, quotas, MIME, malware rejection, versioned private S3 quarantine/clean separation, scan freshness, retry, interrupted upload, immutable DB receipts and HR review, real KMS/private access. Test a missing *historical* VersionId with newer version of same key and confirm fail-closed; never silently rebind identities.
5. **Recovery:** distinguish integrity verifier, actual offline same-image full-store restore, cloud S3 replication to another provider (not tested), object/key retention, key availability, RPO/RTO, pending Procrastinate recovery, failover under active writes; refuse unsupported production recovery claims.
6. **AI agency/privacy:** `backend/ai/context.py`, `backend/ai/answers.py`, `backend/ai/provider.py`, `backend/ai/validator.py`, `backend/ai/offline_policy.py`. Confirm no cross-org/private PDF content or auth tokens in external calls; model cannot mutate state; citations bound to canonical sources; unsupported answers abstain; provider timeout/outage fallback not disguised as model response; daily budget/race.
7. **Frontend/accessibility/privacy:** XSS vectors in employee names/filename/notes/policy/AI content, React escaping and no unsafe HTML, secret exposure via browser/network/logging, attachment downloads, output caching and labels/keyboard/zoom; automated axe scan not a conformance certification.
8. **Deployment/runtime supply chain:** locked `uv.lock` and `frontend/package-lock.json`; GitHub Actions privileges/self-hosted runner isolation and stale cached secrets; Docker pinned base/build; Render Free/paid-worker plans and manual deploy settings; service-to-service auth; config/secret handling; no insecure production flags.
9. **Data lifecycle:** audit immutability, GDPR/India privacy and retention policy **needs separate legal/operational approval**, least privilege DB/object store, backups vs deletions, synthetic-only hosted demo, no personal identity file until authorized.
10. **Source provenance:** exact branch SHA/CI run identity, migrations, known older failed attempts superseded only by exact corrected run; enumerate every assumption from harness or hosted conditions.

For each finding provide **ID, severity (BLOCKER/HIGH/MEDIUM/LOW), exact file and line, exploit or failure preconditions, reproduction/test evidence, data affected, minimal corrective action, and retest gate**. Do not fabricate exploitability. Mark UNKNOWN if evidence is absent.

## 4. Required verdict and release separation

Return:
- **T17 SOURCE SECURITY: GO or STOP** with evidence-backed blocking issues.
- **D5 ACCESSIBILITY: focused automated CI PASS**, broader screen-reader/human/zoom verdict **OPEN** unless independently tested.
- **D6 OPERATIONS: isolated offline restoration PASS**, but production hosting, tested RTO/RPO, retention, KMS/key recovery, 24/7 workers and cloud S3 recovery **OPEN** unless objectively proved.
- **HOSTED J01–J05:** **0/5 accepted** until each executes on the approved exact hosted SHA. J04 requires actual authorized provider-inference and independent policy semantics, not deterministic fallback disguised as AI.
- **PRODUCTION AND DELIVERY RELEASE: STOP** unless all owner-agreed requirements, hosted demonstrations, no blocking issues, approved paid plan/credentials, reproducible fresh tests and final reviewer approval are present.

A self-review, this packet, or old green CI runs **must never** be represented as independent T17 GO. No source changes, account/plan alteration, hosted mutation or charged provider access are authorized by this review request.
