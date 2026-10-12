> **Latest mandatory submission requirements — 12 October 2026:** This evaluation now explicitly requires a **YouTube watch link** and a reviewer-accessible personal GitHub repo containing the detailed design, setup/deployment, code explanations, assumptions, and unit tests. A hosted URL is requested **only if hosted**, so older project-specific hosted acceptance remains useful but is not itself an elimination rule in the latest rubric. **AI inference must be genuine, not only mocked-contract CI or deterministic policy lookup.** See the [deadline AI/evidence packet](SUBMISSION_DAY_AI_AND_EVIDENCE_20261012.md) and the [isolated real-model runner](../../scripts/run_evaluation_real_ai.sh). The model demo, YouTube link, and reviewer access were **not verified** when this note was added.

> **Latest exact-source CI:** `caf34f2b629f2ad2786b63d63fc0e93844239d7b` passed [PostgreSQL/React/Docker/four-role Chromium](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893788), [PostgreSQL 18/migrations](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893843), [focused AI contracts](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893785), and [AI relevance tests](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893822). **Live Ollama is skipped** by ordinary CI. Older specific SHA claims below are historical and remain exact-source facts, not the latest result.

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
