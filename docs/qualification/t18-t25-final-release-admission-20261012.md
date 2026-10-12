> **12 October OWNER REBASELINE — NOT THE CONTROLLING EVALUATION SUBMISSION GATE:** This file tracks rigorous *production-style* T17–T25 requirements and useful hosted evidence. The senior-assigned deliverable is a production-oriented **evaluation** product, not live operational HR software. For final submission use [Evaluation First Delivery Contract](../submission/evaluation-first-delivery-contract-20261012.md). Independent enterprise signoff, paid worker, production RPO/RTO, full cloud S3 migration and recurring infrastructure cost do **not** automatically block evaluation GO. Functional synthetic hosted experience, business journeys, actual AI evidence when claimed, relevant security tests, docs and video remain mandatory. Past "RELEASE STOP" statements mean **production GO STOP**, not that an evaluation demonstration is forbidden.

# Employee Onboarding Companion — T18–T25 Release Admission

**Date:** 12 October 2026. **State:** RELEASE STOP. **Repository:** private `Electro-Anurag/employee-onboarding-companion`; active branch `feature/eoc-completion-development`. This ledger must not be treated as permission to deploy, buy cloud services or enable external inference.

**Authority:** PRD v1.1 F01–F28; Business Journey v1.0, four roles HR/Employee/IT/Manager, E01–E10 and mandatory hosted J01–J05. The 28 functional requirements have code candidates and test mapping (`docs/qualification/d4-requirements-exception-traceability-20261012.md`) but **are not individually accepted by hosted evaluation**.

## Earned engineering evidence

- [Exact-source integrated application `38218007460`](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38218007460), full PostgreSQL/React/production Docker/real four-role Chromium **PASS** at `b6a4ac93`. Document-specific real-service tests live in separate workflow.
- [Eight real live ClamAV and S3/version tests `38219586182`](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38219586182) **PASS** at `829f9e69`, including missing historical S3 version fails closed.
- [Coordinated quiesced local synthetic DB+MinIO full-state DR `38221427909`](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38221427909) **PASS** at `b2765403`, preserving original VersionIds, receipt/audit fingerprint. **Not production-scale provider-independent recovery.**
- [Scoped D5 HTTP security/CSRF `38208898601`](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898601) 25 PASS; [M5 worker recovery `38208898591`](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898591) 16 PASS and crash/periodic wake; [populated historical migrations `38207921011`](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38207921011) four scenarios PASS; [real multi-state axe-core keyboard and responsive scan `38212201996`](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38212201996) four Chromium PASS, zero scanned DOM violations.
- **T17 independent security source review:** not yet performed; [review packet](t17-independent-security-release-review-20261012.md) prepared. No reviewer GO exists.

## Gates before final delivery

| Gate | Required immutable acceptance evidence | State |
|---|---|---|
| **T17 independent security and final quality review** | Separate adversarial reviewer gives exact-SHA source verdict; blocking issues corrected and independently requalified; manual accessibility/screen-reader review logged or explicitly disclosed | OPEN |
| **T18 full final candidate integration** | On the owner-approved final source SHA: locked migration/schema, full PostgreSQL backend, React tests/build, Docker image, Chromium four-role and focused storage/worker/AI/a11y/security suites all pass; final tested SHA exactly equals deployed SHA | OPEN at eventual final SHA |
| **T19 owner-authorized hosting and operations** | Explicit permission and selected Render workspace; approved costs/plan; persistent database beyond 30-day free expiry, backups and verified restore, secure S3/ClamAV and actual always-on worker, env and secret handling, safe rollback, smoke/readiness with SHA identity; no real employee data | OPEN |
| **T20 / J01 complete onboarding** | Real hosted HR creates/activates case, employee completes actual form/document obligations, HR verifies, IT fulfillment, manager check-in/intro, elapsed meeting/training, full dependency transitions and HR closeout; reload/restart persistence and audit | 0/1 hosted PASS |
| **T21 / J02 rejected document recovery** | Real hosted private/versioned S3, live ClamAV and negative malware path; employee submits PDF, HR rejects or requests clarification, employee uploads new revision, scanner passes, HR accepts and only correct successor unlocks; exact versions/audit verified | 0/1 hosted PASS |
| **T22 / J03 delay/exception/reminders** | Actual always-on hosted worker executes bounded deduplicated deadline/reminder/escalation (not a mocked status); IT delay, joining-date change and owner reassignment recover, repeated delivery does not duplicate notifications, restarted worker drains unfinished work | 0/1 hosted PASS |
| **T23 / J04 provider-grounded AI** | Explicitly authorized real external provider and capped budget; policy-question source citation support, current authorized case context, next action, unsupported abstention and provider-down fallback with no workflow-write tools; independent semantic evaluation passed | 0/1 hosted PASS |
| **T24 / J05 adversarial hosted authorization** | Real sessions for two different employees and four roles; foreign case/role access denied across documents, AI, notifications and task IDs, CSRF and stale write denied, concurrency/idempotent replay no duplication, immutable audit persists across restart | 0/1 hosted PASS |
| **T25 final submission** | Working final HTTPS URL, correct repo and tagged/immutable final commit, technical architecture and deployment/setup documentation, unit/integration/acceptance evidence, assumptions/privacy, clear limitations, recorded demo walkthrough/video, no blocking defects | OPEN |

**Absolute delivery stop:** J01–J05 hosted **0/5**, independent T17 **OPEN**, owner-approved hosting **NOT YET QUALIFIED**. Do not misreport the earlier public smoke at old deployed SHA `ded82f9` as actual hosted functional acceptance.

## Authorizations and constraints for the remaining work

Current Render configuration `render.yaml` is a no-cost public evaluation web service. Real secure S3/ClamAV intake and external AI are **DISABLED**, and no always-on worker is provisioned. `render.full.yaml` describes a **starter paid worker** but retains secure document and AI flags disabled and still lacks a qualified cross-provider S3 backup/protection implementation. **Neither file alone qualifies the product**. Free database expiration, backups, durability and costs require explicit owner decisions.

Do not silently enable a paid plan, expose database networking, set real data credentials, upload personal IDs, bypass feature gates, self-approve independent T17, or access any account unrelated to EOC.

Before hosted mutation, the owner should explicitly approve: **target Render workspace/account, final immutable source SHA, allowed compute/database/object-storage budget, deployment/secret delivery method and synthetic-only acceptance data**. Secrets must go through authorized private UI/connector flows, never chats/logs/GitHub source. Deploy only after environment, rollback and migration preflight.

## Final release statement format

- **SOURCE SECURITY T17:** GO/STOP, independent review ref and exact source SHA.
- **INTEGRATION T18:** GO/STOP with exact SHA and test-run IDs.
- **OPERATIONS T19:** GO/STOP; approved infrastructure, provider quotas, backups, S3 encryption, worker, recovery and cost.
- **HOSTED ACCEPTANCE T20–T24:** J01 ___ / J02 ___ / J03 ___ / J04 ___ / J05 ___ (evidence links, dates, deployed SHA).
- **SUBMISSION T25:** GO/STOP with repo, hosted URL, documentation/demo/video, known limitations.
- **OVERALL:** GO only after **all mandatory gates pass** and the owner explicitly authorizes final submission. Production use with real employee data is a separate privacy/operational approval, never implied by submission readiness.

## Live Render workspace inspection addendum — 12 October 2026

[Detailed observed current-state preflight](render-workspace-release-preflight-20261012.md). In confirmed `My Workspace`, the currently LIVE deployment SHA is **`ec781ab7362da10648eea496b1402b8c317dcd4c`**, not the old `ded82f9` from historical hosted smoke. Render has **one free web service only**, no control worker. PostgreSQL **18** free database expires **2026-11-09 15:02:21 UTC**; empty IP allowlist blocked safe external query so current hosted migrations cannot be claimed verified. Migration rehearsal and preservation are STOP gates prior to deployment. Selected workspace does not constitute budget, production data, model usage or secret-management approval.
