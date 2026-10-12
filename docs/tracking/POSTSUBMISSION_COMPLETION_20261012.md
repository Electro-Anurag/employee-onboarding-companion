# Post-submission completion ledger — from 12 October 2026
**Repository:** `Electro-Anurag/employee-onboarding-companion` — no relation to any other project.

## Immutable delivery baseline

- Owner confirmed that the evaluator submission was **submitted on 12 October 2026**. The actual submission receipt / portal fields / accepted YouTube URL are not in this repository.
- Submitted-source snapshot preserved at branch **`submission/2026-10-12`**, SHA **`be81c50a986ded46bc363f7788cfd926692549ab`**. That identifies *repository content*, not what external evaluators necessarily saw.
- Continue changes only on **`feature/eoc-postsubmission-completion`**. Do not silently rewrite or retag the submission snapshot; the branch is a named reference and must be treated as frozen.
- Latest complete pre-split exact application-source qualification at **`c515355502d3934d37ab479159c6f28879420b74`**: PostgreSQL17 + Django/React + Docker + four-role Chromium [38273035716](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38273035716); PostgreSQL18 + populated migration histories [38273035707](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38273035707); grounded AI offline [38273035680](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38273035680); focused AI contracts [38273035674](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38273035674). All four **PASS at that exact earlier SHA**; no real model was inferred.
- AI provider on hosted Free Render has historically been **DISABLED**, hosted J01–J05 formally **0/5 qualified**, latest deployed source version **not rechecked after submission**.

## No-drift, risk-ordered gates

| Gate | Actual current evidence boundary | Next action | Acceptance |
| --- | --- | --- | --- |
| A1 **Real Ollama transport** | Mac `gpt-oss:20b` and Ollama 0.35.1 verified installed/running. Mac PostgreSQL 17 Homebrew incomplete; Ubuntu `11434` reverse tunnel bind failed; `11534` tunnel unverified. | First run **`EOC_OLLAMA_MODEL='gpt-oss:20b' python3 scripts/preflight_real_mac_ollama.py`** on the owner's Mac from the post-submission checkout. No Django, Postgres or tunnel required. | Actual provider JSON + one exact cited owner/status fact + safe unsupported abstention. Prints preflight PASS. **Transport-only**, NOT AI admission. |
| A2 **Case-scoped live AI** | Real `backend/ai/tests/test_ollama_live_synthetic.py` remains unexecuted by verified CI. Mocked-provider regressions do not satisfy this gate. | Verify authorized Mac→Ubuntu SSH reverse loopback `11534`, opt in using `eval(real-ai):` trigger; run isolated Postgres17 GitHub job. | At least one real `MODEL_VALIDATED` supported answer with one source, three auditable model attempts, no case mutation, safe handling of bonus claim. |
| B1 **Integrated four-role case** | Chromium real synthetic progression and persistence qualified at historical SHA; no complete 17-task closeout J01 shown. | Fully exercise HR→Employee→Manager→IT→policy/forms/docs→reviews→meeting/training→closeout on **one** realistic case; record browser and API persistence. | Correct role scope, prerequisites, final HR evidence-gated closeout, zero unresolved exceptions. |
| B2 **Document revision & scanner** | Source and real MinIO/ClamAV historical tests exist; no accepted complete hosted J02. | Integrated staged upload, interrupt/restart, scan, HR reject/replace/accept, immutable evidence and deny unsafe files. | Actual lifecycle, recovery, role and audit evidence. No real identity docs. |
| C1 **Background notifications/recovery** | Transaction-backed Procrastinate source and earlier CI focused worker tests. No always-on worker verified on hosted Free. | Requalify periodic worker, overdue/catch-up, dedup and real process restart against current integrated branch. | Persisted work after restart, exactly-once effective reminder, recipient ownership and no silent approval. |
| C2 **Exception/handoff** | E01–E10 source tests/partial focused browser qualification. | Re-run all ten exception paths in integrated real-browser or live backend with role changes. | Open, assign, repair, close, audit; stale/no-op/conflict guards maintained. |
| D1 **Current-head CI/migrations/security** | Four major suites passed at c515 source SHA; later postsubmission commits require fresh evidence. | Post-submission branch CI enabled for integrated, PG18, AI relevance and contract suites. Add checks where real threat/race coverage is missing. | Exact latest application SHA PASS; record exclusions and independent/adversarial review separately. |
| D2 **Hosted application** | Older Render Free deployment, exact current release and reviewer roles unverified; Render workspace not yet owner-confirmed for connected tooling. | Owner confirms Render workspace/deploy authorization, inspect safe migration/data plan before any deploy. | Exact SHA on HTTPS, four role sign-in, real UI persistence, health/readiness/CSRF; never confuse local CI and hosted acceptance. |
| E1 **Evaluation measurement** | Proposed methodology, no observed before/after values. | Run repeatable synthetic-owner/blocker time study and one AI positive/negative sample; capture raw data and limits. | Actual raw timings/sample-size/accuracy; no invented ROI. |
| E2 **Review/demo after submission** | User confirmed submission, no receipt/video URL available to development loop. | Prepare a stronger actual browser walkthrough and actual AI transcript when qualified; do not overwrite claimed deadline artifacts silently. | Owner-reviewed honest shareable evidence; post-deadline update policy checked. |

### Live vs implementation labels

- `IMPLEMENTED`: corresponding source exists.
- `CI_PASS@SHA`: a specific run executed and succeeded at that exact revision.
- `REAL_MODEL_PASS@SHA`: actual model runtime passed authorization and citation admission.
- `HOSTED_PASS@SHA`: deployed version and actual hosted interaction verified.
- `SOURCE_REVIEW_GO` and `PRODUCTION_GO` are separately held gates.

### Planning progress (not acceptance)

Prior completion planning estimate was **approximately 70% with ±10–15 percentage point uncertainty** on the full evaluation/product-delivery envelope. This is **not upgraded by documentation, workflow registration, compilation or a PASS at an earlier SHA**. Separate binding gate counts remain **A2 0/1 real-model qualification; hosted J01–J05 0/5** until measured. All 28 PRD requirements (F01–F28), 10 exception journeys (E01–E10), four roles and J01–J05 remain in scope.

### Execution sequence (avoid new feature drift)

1. Admit real local model behavior with owner-run DB-free preflight; fix actual provider rejection only if measured.
2. Record a current exact-SHA integrated CI pass including the new tests.
3. Use existing Ubuntu Postgres+Mac SSH tunnel for full real case-context AI admission without modifying macOS Homebrew.
4. Complete/persist a full 17-task role journey and exception/document revision acceptance.
5. Qualify worker and security on current source and then prepare owner-approved safe hosted update and verifier login.
6. Report actual earned evidence and percentage; independently review before claiming release readiness.

**Non-goals:** PIOS associations, real employee data, uncontrolled paid infrastructure, exposing Ollama publicly, bypassing human approvals, claiming mocked inference as real AI, arbitrary source redesign, changing an old migration, or force-pushing the submitted snapshot.
