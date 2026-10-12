# Evaluator quick start — Employee Onboarding Companion

**Purpose:** a confidential senior-evaluation assignment using exclusively synthetic people, policies and case data. This is not an operational employer HR system. The personal repository is private; reviewer access and demo credentials must be approved and provided privately.

## Verified source and CI as of 12 October 2026

**Last fully integrated application/test SHA:** `944d9768c77da63f5965a4644107efff68e81471`. [Full integration run 38260916703](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38260916703) **SUCCESS**: 271 Django/PostgreSQL 17 tests passed, eight environment-dependent MinIO/ClamAV tests skipped, 29 React tests passed, production Docker build passed and one real four-role Chromium acceptance scenario passed. These qualify the described **local CI** scope, not current Render hosting.

Separate [PostgreSQL 18 and populated-migration-history run 38256581292](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38256581292) **PASS at previous code SHA `495276e3`** (271 pass / eight live-service skips). [Grounded AI run 38256581318](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38256581318) **69 PASS at `495276e3`**, with **mocked model transport**. Neither is evidence of actual model inference.

Subsequent commit `881446c675c3ae6b4de70340dc0db68dc1258c18` adds an opt-in real Ollama test, **not a completed real-model evaluation**. See [local Ollama evaluation](local-ollama-evaluation-20261012.md).

## What to demonstrate

1. **HR:** publish a synthetic 17-task template, create and activate a case, view current owners and dependencies.
2. **Manager:** record first-week preparation with typed evidence and observe the persisted state.
3. **Employee:** see assigned tasks, permitted synthetic policy edition and acknowledgements; exercise applicable form/document paths.
4. **IT:** show an explicitly simulated external provisioning outcome recorded through an actual audited workflow command.
5. **HR:** inspect current case portfolio, review/exception state and the evidence-gated closeout conditions.

Each role has an in-app **Evaluation walkthrough**. Navigation is a real UI feature but the walkthrough itself does not complete or approve tasks.

## Evidence boundaries and outstanding submission work

| Item | Verified scope / missing evidence |
| --- | --- |
| Local integrated application | PASS at `944d9768`; test-suite exclusions are listed above |
| Real local Chromium video | [Recording run 38235666178](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38235666178): eight PNG screenshots and a genuine WebM video, **local CI only** |
| Private video artifact | [Download artifact 11742925882](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38235666178/artifacts/11742925882) before **15 Oct 2026 10:57 UTC** |
| Real local MinIO + ClamAV | [Eight tests PASS at historical SHA](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38219586182); **not enabled on hosted Free** |
| Background worker / recovery | Separately tested in earlier CI; no always-on hosted worker qualified |
| Model-generated AI | **NOT YET VERIFIED** on real Ollama; deterministic policy reader/fallback is not model AI |
| Current Render hosted application | [Existing HTTPS site](https://eoc-companion-web.onrender.com) last inspected at older deployment `ec781ab7`; current source **not deployed** |
| J01–J05 hosted journeys | **0/5 formally accepted**; do not convert local test PASS into hosted acceptance |
| Final senior submission | Hosted demonstration at approved current SHA, J01–J05 evidence, final screen-recording, architecture, reviewer access and private credentials remain pending |

No real personal documents or corporate policies belong in a demo. Do not enable cloud secrets, paid providers, data resets or live deployments without owner approval.

**Next:** verify the opt-in local real-model test where an already installed Ollama model and isolated synthetic PostgreSQL are available; secure deployment approval and safe current-SHA hosting; then execute and record J01–J05 honestly.

Further documents: [evaluation contract](evaluation-first-delivery-contract-20261012.md), [business walkthrough](evaluator-walkthrough-20261012.md), [actual recording/evidence protocol](evaluation-demo-evidence.md), [architecture](technical-design.md) and [requirement traceability](../qualification/d4-requirements-exception-traceability-20261012.md).
