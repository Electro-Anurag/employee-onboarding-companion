> **Superseding competition instructions received 12 October 2026:** Final submission on **12 October 2026** explicitly demands a **YouTube demo watch URL**, a reviewer-accessible personal GitHub source link, detailed technical design and diagrams, setup/deployment, code explanations, assumptions, and comprehensive unit tests. Hosting is **optional under this latest rubric** ("If Hosted" include its URL). Do not use the earlier below wording "YouTube optional" as current submission guidance. Internal F01–F28, E01–E10 and J01–J05 remain product/verification targets, but **complete hosted J01–J05 acceptance is not an explicit latest-rubric elimination item**. Do not claim real AI merely because mocked tests pass. See [submission-day AI and evidence packet](SUBMISSION_DAY_AI_AND_EVIDENCE_20261012.md). No automatic public release/upload authorized.

# Employee Onboarding Companion — final senior evaluation delivery contract

**Owner direction, 12 October 2026 — supersedes earlier production-release assumptions for assignment submission.**

## What we are building

This is a **personal, confidential senior-evaluation assignment**, NOT an operational HR product commissioned for real employees. The goal is to show a **working, credible, production-oriented AI-assisted onboarding companion** with high engineering quality, while avoiding needless deployment cost and production-only administration.

The governing functionality remains PRD v1.1 (**F01–F28**), Business Journey v1.0 (**four roles, E01–E10, J01–J05**), and the revised October 8 evaluation brief. **No requested business feature is silently removed** by this reclassification. Keep the project's personal GitHub repository private until owner-approved evaluator access. Use exclusively fictional/synthetic/anonymized/public information; do not mix in employer, PIOS or actual HR data.

**Product-evaluation GO and real-production GO are separate decisions.** Do not make an independent enterprise security audit, paid Render worker, production HA, RPO/RTO, KMS, geographically redundant S3, long-lived paid database or provider billing an automatic requirement for evaluation submission. These remain **production hardening / optional stretch**, unless explicitly required by the senior's rubric. Preserve the existing security controls; do not bypass authorization or invent test evidence.

## Definition of evaluation-ready (mandatory)

1. **Demonstrable app:** accessible functional HTTPS evaluation URL, with working React frontend, Django/API, stable synthetic role logins, persistent enough demo state for the evaluation window, and deployed SHA visibly tied to tested source. Free-tier cold starts/expiry may be disclosed; do not promise uptime.
2. **Real core workflow:** HR creates/activates a case and sees owners; Employee submits required synthetic data; HR reviews/rejects/accepts; IT and Manager record simulated external activities; case dependencies, policy/version acknowledgement, meeting/training, exception and HR closeout states change via *persisted* server-authorized commands, not fake UI screenshots.
3. **Four roles and ten exceptions:** check against F01–F28 and E01–E10. Run the five J01–J05 evaluation scenarios using actual hosted interaction whenever the feature is available. Where external HR/IT, storage/scanner, clock acceleration or provider services are purposely simulated, show a **reproducible, genuine local/CI test** and visibly label the simulated boundary. Never report local CI as a *hosted* PASS.
4. **Actual AI contribution:** demonstrate model inference on authorized policy/case context, with citations, valid next-step guidance, unsupported-answer abstention and visible human-control boundaries **if genuine AI is promised**. A deterministic policy lookup or canned text is NOT model AI. A real model can be tested in an owner-approved controlled/local setup, with a clear disclosure if inference is not enabled on the hosted demo. Do not purchase provider access without owner consent.
5. **Engineering evidence:** React/backend tests, PostgreSQL, real Chromium four-role flows, adversarial IDOR/CSRF, idempotent receipts, audit trail, secure S3/ClamAV and worker/recovery tests in isolated CI as applicable. Fix critical product/security defects; do not require every production architecture contingency to be simulated in hosted Free.
6. **Complete presentation package:** personal GitHub repo access for reviewer, architecture and diagrams, assumptions, installation/run/test instructions, relevant test results and source SHAs, hosted URL, demo account instructions passed privately, known mock/service limitations, and **a real screen-recorded video/demo**. A YouTube URL is **optional unless the latest written senior brief specifically requires it**; no fabricated URL.
7. **Honest evidence:** label each feature **LIVE HOSTED / LOCAL OR CI VERIFIED / EXPLICITLY SIMULATED / NOT DEMONSTRATED**. Do not claim 100% of assignment scope until mandatory behaviors and submission artifacts are evidenced.

## Boundaries we intentionally will not purchase/build merely for evaluation

- No paid 24/7 Render worker or database upgrade as a prerequisite when reliable local/self-hosted worker tests and honestly labeled evaluation demonstration suffice; any extra spend requires explicit approval.
- No live employee identity documents, external corporate HR/identity integrations, real IT account creation, production credentials or real-company policy datasets.
- No enterprise SLA, monitored multi-zone HA, cloud failover, 24/7 support, production compliance certification, multi-provider object-store replication or formal production RPO/RTO target.
- No paid external LLM invocation by default, and never call rule-based guidance "AI".
- No automatic promotion of the old Render Free deployment. Manual redeployment of current source still changes a live public environment and requires explicit release authorization and safe synthetic-data precautions.

## Remaining focused evaluation work (ordered)

| Priority | Evidence/decision required | Evaluation status at rebaseline |
| --- | --- | --- |
| P0 | Fix/qualify any actual defect on final source SHA; ensure evaluator-facing login and workflows can run | Source CI substantial PASS; fresh hosted source not yet deployed |
| P0 | Functional current-SHA hosted browser demo of HR/Employee/IT/Manager and the critical business journey | **OPEN**, old hosted SHA is `ec781ab7` |
| P0 | J01–J05 **evaluation scenario** evidence: hosted cases where available + clearly identified local/CI simulation of external boundaries | **NOT YET accepted**; do not silently mark 5/5 |
| P0 | Real AI demonstration or explicit, candid statement of capability and current availability | **OPEN** for real inference; deterministic guidance is not AI |
| P1 | README/technical design/architecture, exact test matrix and synthetic setup, limitations | Partially ready; final review needed |
| P1 | Actual recorded walkthrough, demonstration link/file and concise evaluator-facing narrative | **OPEN** |
| P2 | Independent source security review and full manual WCAG/screen-reader audit | Recommended if feasible, **not mandatory enterprise release certification**; critical proven findings remain blockers |
| Out of scope for submission | Production S3 portability, HA, paid worker, production RPO/RTO, 24/7 service, real HR integration | Explicitly **not required** |

## Practical hosting rule

Use the existing no-cost Render web and synthetic-only data wherever technically adequate; it currently has one Free web service, no always-on worker, and Free PostgreSQL 18 expiring **2026-11-09**. This is acceptable as a *time-bounded evaluation environment with disclosed limitations*, not as durable production hosting. A local or CI sidecar may show genuine worker, MinIO/ClamAV and AI mechanics where public Free hosting cannot. If a key judged feature genuinely requires paid hosting or external inference, first justify its evaluation value and seek a specific, capped decision rather than redesigning the project around infrastructure.

## Exit statements

**EVALUATION SUBMISSION GO:** all mandatory evaluation-visible functionality, test evidence, fresh hosted demo, project documentation and actual video are complete; known limitations accurately stated; no critical security defects. Owner approves submission.

**PRODUCTION OPERATIONS GO:** separately not requested, not claimed, and does not block the evaluation. Local DR/security hardening remains a valuable demonstrable engineering strength, not a mandate to operate HR data commercially.

See [existing production-oriented T17–T25 ledger](../qualification/t18-t25-final-release-admission-20261012.md) for optional future operational gates; it is **not** the controlling evaluation-exit checklist after this owner clarification.
