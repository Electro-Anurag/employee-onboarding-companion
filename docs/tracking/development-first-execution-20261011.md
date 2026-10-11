# EOC development-first execution ledger (11 October 2026)

Branch: `feature/eoc-completion-development`  
Baseline: `60e6dbb9e37d1ee572cc011ec99d5bb02a30d973`, from `feature/m5-m6-parallel-development`.

## Governing scope and gates

PRD v1.1 (28 requirements), Business Journey v1.0 (Employee/HR/IT/Manager, ten exception journeys, J01–J05) and approved architecture remain authoritative. No silent scope reductions. Synthetic/anonymized data only. Keep the private repo, Ubuntu ARM64 runner and free-only restrictions; do not silently incur paid deployment/model costs.

Workflow: finish M5, M6, M7 product functionality with focused tests; execute expensive integrated Chromium/S3 qualification at milestone boundaries, then independently review security, deploy the exact qualified SHA, and execute hosted J01–J05 before submission. Tests added to code are **not** PASS until executed at the corresponding SHA.

## Prior CI qualification record (baseline SHA)

- M5–M6 integrated run [38126300175](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38126300175): PASS.
- M5–M6 Chromium run [38126300109](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38126300109): PASS.
- M3–M4 Chromium diagnostic run [38126300241](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38126300241): FAIL. Policy GET returned 200 and the expected synthetic-conduct edition; the browser's focused Conduct Ack card became absent after the read. This is a real open UI/acceptance defect, not license to waive policy acknowledgement. Preserve failure evidence for milestone qualification.

## M5 first development slice

Source implementation `1ea658b15df95a917cebcb580c066bae5ea62da9`; focused test correction `8e5368753c85dc9c330778a49881b5697fe681a5`: recipient inbox rejects stale DUE_SOON / OVERDUE_DAILY identities during worker outages without changing durable history. **Focused PostgreSQL qualification PASS:** [run 38127290650](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38127290650), 9 passed (4 non-fatal warnings) on exact SHA `8e5368753c85dc9c330778a49881b5697fe681a5`. Full milestone/hosted gates remain open.

## M5 second development slice

Source commit `08142c2131292f692b746e1093452e6728b3c5f7`: the recipient inbox now filters retired notification rows, retired intents and obsolete case/task revisions before the 100-record result limit. The existing per-user, per-case and live time-window checks remain authoritative on each item and mark-read action. A new synthetic regression adds 105 later archived notices and verifies that the older valid actionable notice remains visible and readable. **Focused PostgreSQL qualification PASS:** [run 38128147331](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38128147331), 10 passed (5 non-fatal warnings) on the exact implementation SHA. This does not prove unrestricted pagination or production-scale performance; full milestone/hosted qualification remains open.

## M5 worker concurrency and late recovery verification

Exact SHA `af0abf5392b8b602d987e4d31c7738f16cc0ca36`. Real separate PostgreSQL transactions from two concurrent application workers and a 72-hour simulated worker outage exercised in focused [CI run 38128475743](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38128475743): **14 passed, 5 nonfatal warnings**. Proves bounded idempotent concurrent reconciliation and no missed-day notice replay; does not qualify actual killed-process restart, multiple persistent worker hosts or production SLA.

## M6 offline model answer validation

Exact SHA `6a32720b7fa75ab56a8626ee4df1bb0f8aabde4a`. Strengthened malformed/unhashable answer-type denial, nonblank answer enforcement and meaningful abstention limitation. Focused [CI run 38128660863](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38128660863): **17 passed, 1 nonfatal warning**. All provider calls mocked or deliberately unavailable; no API charges, live semantic evaluation or production model admission implied. Real inference/provider, adversarial semantic relevance and hosted J04 remain open.

## M7 HR closeout readiness (focused qualification)

Backend source `4cf8fa1c4b193d146d1f0717a014b1cd6c11ac9c`, frontend and API test source `eeb2884964c028bf4d40639c81833c0bbd0122ba`: HR can request read-only, case-version-scoped closeout blockers (missing mandatory typed evidence and still-open exception episodes). Authorization is checked server-side; preview does not mutate data or authorize closeout. The final command re-evaluates gates under case/task PostgreSQL locks. React only enables confirmation after an exact current-version readiness response. **Focused CI PASS** [run 38129044659](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38129044659) on `eeb2884964c028bf4d40639c81833c0bbd0122ba`: 1 PostgreSQL closeout test passed, 14 React tests passed and Vite build succeeded (1 nonfatal Python warning). No hosted J01 completion, Chromium UI journey, full closeout dashboard, accessibility qualification, or release approval is implied.

## M7 HR case dashboard (focused qualification)

Backend source `9b50d0abc5443fa6701e794eb0b8086dd1ebfb2f`; React integration and source tests `798bd0d57d7af7456943e3f2a297e1038bbed06f`; HTTP test session-guard alignment `c48f5c1b0737eb717284d64945505da7b2d91fa9`. HR-only read-only `GET /api/v1/cases/{case_id}/dashboard` returns a versioned, timestamped view derived from typed mandatory TaskCompletion, task eligibility, role workload, overdue work and active exception episodes. Case/organization authorization is rechecked; Employee/IT/Manager cannot access the HR projection. React shows the counts only in the authenticated HR case view for the matching case version, with explicit snapshot timestamp and refresh button. No task mutations, new migrations, external calls or paid services.

**Focused CI PASS** [run 38130225197](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38130225197) at exact SHA `c48f5c1b0737eb717284d64945505da7b2d91fa9`: 3 PostgreSQL tests passed, 15 React tests passed, Vite production build succeeded. The previous run failed because an HTTP test omitted the existing SessionGuard session-start value; its test-only correction passed. Not a hosted browser demonstration, cross-case analytics or release clearance.

## M7 current-HR portfolio (focused qualification)

Backend source `9b44ad0184298ef7d5420a7145d17af2540e433e`; React interface + tests `98ffa277934a7838aa80710ef6962fee9a7427fe`; corrected test setup `fb59c4543e673a6b00f801c472a59d2c3af17385`. Private `GET /api/v1/portfolio` is scoped through the current HR's assignments and returns max 25 cases per page with opaque UUID cursor, no organization-wide total claim. It reports case status, real typed mandatory completion, overdue mandatory tasks and active exception episodes. React includes HR-only navigation, refresh, pagination and open-case action. Created cases with no activated snapshot correctly show zero mandatory tasks, not fabricated 17-task progress; test distinguishes them from activated cases. Unassigned HR memberships see empty results; other roles denied. User-provided limit and cursor are validated. No mutations, migrations, paid provider calls or deployment.

**Focused CI PASS:** [run 38130736087](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38130736087) at exact SHA `fb59c4543e673a6b00f801c472a59d2c3af17385`: 5 PostgreSQL tests passed (4 nonfatal warnings), 17 React tests passed and Vite build succeeded. No full/browser/hosted security qualification or production release claim.

## M6 task-specific provenance and human-readable evidence (focused qualification)

Backend `9a87b516c587d4ec30ca587999432556a16295a8` and focused-CI test registration `7d0571f2ad177b62000049f3cbce12bb02e2b519`: the model output validator now rejects a proposed action or blocker whose specific underlying task is absent from the cited `TASK:<task_id>` sources. Partial answers require a nonblank limitation. Real PostgreSQL adversarial scenarios include forged-but-valid unrelated citations, blocked-task provenance, cross-role policy citation, stale case versions, and audited fallback with no completion mutation. **Focused backend PASS:** [38131207102](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38131207102), 24 Python/PostgreSQL tests passed.

React source `2a71b39bb560ee60dc961dfde23dbb72cc958e9f`: the model answer now presents recognizable task/policy labels alongside exact evidence IDs; stale answers for a previous case version are suppressed; limitations of evidence-ID checking versus semantic factuality are explicitly explained. **Exact-SHA focused M6 PASS:** [38131450646](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38131450646), 24 PostgreSQL tests passed, 20 React tests passed, Vite production build passed. **Exact-SHA focused M7 frontend regression PASS:** [38131450498](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38131450498), 5 PostgreSQL tests, 20 React tests and production build passed.

These results are deterministic contract and presentation verification only. A correctly referenced task can still be attached to unsupported arbitrary prose. No real external AI provider called; semantic entailment, adversarial natural-language grounding, prompt injection resilience, human acceptance, browser/hosted J04, cost/latency and accessibility remain open. No deployment or billing implied.

## M6 developer-labeled semantic baseline — measured STOP

Exact code/test SHA `00a9219c82529cb71ae627982877f50f3b4b762a`; focused [CI run 38131859968](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38131859968) PASS for execution (24 existing Python/PostgreSQL tests, 2 semantic-evaluation tests, 20 React tests, successful build). The report printed by the actual test states `admission=STOP`, with **12 cases: 4/4 supported admitted, 4/7 unsupported wrongly admitted (57.1% on this synthetic sample), 3/7 unsupported rejected, 1/1 safe abstention admitted**. Unsupported fabricated statements concerned task owner, task state, due date and an invented cash bonus, all attached to valid task citations. The test PASS demonstrates the measurement works, **not** semantic admission. This is a developer-labeled, non-independent, tiny synthetic sample; the 57.1% is not a model hallucination rate or an estimate on users' questions.

**Release-blocking finding:** valid citation IDs are insufficient evidence that arbitrary model prose is true. Do not mark M6 factual grounding, external-provider admission, J04 or full delivery PASS. Continue safe deterministic guidance; before real-provider admission implement and independently qualify a conservative claim-to-evidence mechanism with audited fail-closed behavior and separately evaluated real-provider outputs.

## Next implementation order

1. M5 reminder and escalation recovery, worker outage/multi-worker evidence and handoff edge cases.
2. M6 grounded AI answer evaluation and opt-in real provider qualification only with approved private credentials/budget.
3. M7 dashboard and evidence-gated closeout; end-to-end business journey functional completeness.
4. Consolidated exact-SHA integration/browser/security qualification, free-only deployment, hosted J01–J05, video and submission. Preserve and resolve all deferred failures.

Do not auto-run the three expensive CI workflows on each development commit. Never claim exact-HEAD release qualification from old passing workflows.

## M6 canonical claim-to-evidence candidate (focused verification, not real model GO)

Implementation source commit `84c4cd448e974d98450893dcb953103f8f51480e`; test-fixture correction and **exact tested source SHA** `be72be322ce6e15258f5da574f5ce5686d2d0871`. The validator now admits only exact server-derived authorized task/eligible-action/blocker/exception/policy-edition facts, with source binding, current snapshot and fixed abstention. It rejects arbitrary answer/limitation/clarification/escalation prose and prohibits unverified conflict claims. This is a deliberate conservative reduction of model prose; it does not satisfy full semantic question relevance or policy-content question answering.

**Self-hosted Ubuntu ARM64 focused CI PASS:** [38133071154](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38133071154): 24 existing PostgreSQL AI tests, 4 offline evaluation/adversarial tests, 20 React tests, TypeScript/Vite production build, Django checks/migrations all PASS. Developer-labeled 12-case fixture: 4/4 supported admitted, **0/7 unsupported admitted**, 7/7 unsupported rejected, 1/1 abstentions admitted, **CANDIDATE_ONLY**. Earlier run [38133019704](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38133019704) at `84c4cd4…` FAILED from a malformed new test harness; corrected without weakening any negative assertions at `be72be322ce6e15258f5da574f5ce5686d2d0871`. Do not aggregate these cases into external-model accuracy or claim semantic release GO. M6 live inference, independent evaluation, hosted J04 are still BLOCKED. M3–M4 Conduct Ack browser FAIL remains OPEN.

Tracking estimate remains **63/100 earned, 37/100 pending** (non-audited engineering estimate, ±10–15 points); no hosted J01–J05 passes. See [release-test-gates-20261011.md](release-test-gates-20261011.md) for continuously retained T01–T25 gates.

## M6 authorized full-policy quotation (source slice; CI still PENDING)

Source commits `7e580a4036e3f7dc09e46dbdff47fc57534c96c4` and newline-preservation correction **`6481876a2328f054eaedaf84db1bcc0b2471ebdc`**. Server accepts a model-selected *entire* case-assigned, SHA-256 verified policy edition only as a PARTIAL, precisely quoted source (max 800 characters). No model-selected fragment, paraphrase, fabricated benefit, leaked optional prose, forged citation, revoked-role policy or stale-version response is admitted. UI visibly identifies the text as a verbatim edition with unverified question relevance and escapes HTML. Offline positive/adversarial source tests were committed, including mocked transport only.

**CI NOT YET QUALIFIED:** self-hosted Ubuntu ARM64 [run 38146123757](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146123757) was QUEUED at inspection; older intermediate [run 38146056504](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146056504) also QUEUED and is not the final source. No test numbers or pass verdicts are claimed for this slice. Previous M6 24+4+20 focused PASS remains at earlier `be72be32…` [38133071154](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38133071154). No real model inference, independent semantic evaluation or hosted J04 attempted.

Planning estimate remains **63/100 earned, 37/100 pending**; hosted J01–J05 remain **0/5 PASS**. Keep T02 (Conduct Ack browser disappearance) FAIL until reproduced and corrected in actual Chromium; no change made there in this slice.

## Conduct Ack failing-browser investigation: isolated probe prepared (not a fix)

A code inspection of `frontend/src/EvidenceWorkflows.tsx` found that `loadPolicy()` updates only local policy/consent state and does not itself reset parent case selection or focused-plan visibility. This rules out *that direct operation* as an intentional parent reset, **not** other races, a render failure, or a browser issue. The historical failed real-browser result [38126300241](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38126300241) remains open. New focused synthetic UI diagnostic and self-hosted-only workflow at `71ce39459e53445696a950ed3cdafc5c04b68fba`; [run 38146978776](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146978776) queued at inspection. Source JavaScript parsed without execution; **no browser PASS or root-cause claim**. Await empirical DOM/error trace before smallest warranted correction. The M6 source-quote focused run 38146123757 is separately queued. No new deployment, spending or release progress credit.

## New M6 zero-cost policy reading feature (source committed; CI pending)

Exact latest source/test SHA: `4aeeac2214b43f7f2a6b8c564c44642854d1139b`. The read-only companion `/cases/{case_id}/companion/answer` now maps only strict requests for the single assigned conduct/privacy/benefits policy to the exact case/role-scoped, previously hash-verified whole edition; unknown, ambiguous, modifier-laden, unauthorized and overlong requests fail closed to existing deterministic guidance. Server-side `validate_answer` rechecks the case context revision and citation before publication. This happens even if model configuration exists; there is no provider attempt, billing or AI-model claim for these requests. React displays the exact source as a non-AI verified quotation with stale-version suppression; no approvals or workflow commands are performed. It is *not* general semantic QA or proof of a model's relevance. Tested only through source inspection and isolated grammar checks; full PostgreSQL/Django/React test code is committed but **not yet executed** on this SHA. The M6 workflow now includes `test_offline_policy.py` and HTTP test. [Run 38147857389](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38147857389) QUEUED; preserve previous PASS only at `be72be32…`. Also [T02 focused 38146978776](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146978776) queued. No percentage credit until qualification. M7 older runs do not prove current integrated HEAD.

## Current completion-source updates (CI remains queued)

- Source `a2feb9c7…` updates real submission docs: old Render LIVE SHA is separate from current branch; architecture and AI source mode now accurately described; genuine YouTube capture script and measured-value protocol supplied.
- Source `2cc3ed73…` adds first **current-branch** integrated PostgreSQL/React/Chromium workflow; [run 38150225570](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38150225570) QUEUED.
- Source `221c4432…` fixes the guidance input's formerly unsupported example. Authorized HR/Employee roles with case-assigned policy tasks now have one-click conduct/privacy/benefits **exact-source** shortcuts, which run through `askCompanion(caseId, exactQuestion)` and preserve server authority. The input example is now the exact admitted grammar. This path is **not AI**, does not approve tasks, and the UI does not claim it to be.
- M6 [38150383695](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38150383695) QUEUED, M7 [38150383700](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38150383700) QUEUED. Existing older M6 PASS applies only at historical SHA. T02 old Chromium FAIL retained, focused [38146978776](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146978776) QUEUED.
- [Runner queue troubleshooting](../operations/runner-queue-recovery.md) records read-only diagnostic before any restart. No runner manipulation through this chat; credentials stay on the user's VM. No live current-SHA deployment, release acceptance or production security GO. Estimate **63/37**, hosted **0/5**.
