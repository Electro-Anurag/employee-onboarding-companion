# Employee Onboarding Companion — exact-SHA qualification and release gate ledger

Updated 11 October 2026. Active development branch: `feature/eoc-completion-development`.
Last source-qualified CI commit: `be72be322ce6e15258f5da574f5ce5686d2d0871`, [self-hosted M6 run 38133071154](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38133071154).
This tracker is continued from the canonical 11 October handoff. PASS@SHA applies solely to the stated historical scope, not to an integrated release. A documentation-only subsequent HEAD does not change qualification scope.

| ID | Gate | Evidence or present state | Status |
|---|---|---|---|
| T01 | M0–M2 auth/audit/templates/dependencies full HEAD | Earlier M2 subsets at `d471b9f9…`; separate M2 final GO not evidenced | PENDING |
| T02 | M3–M4 complete four-role Chromium including Conduct Ack | [38126300241](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38126300241) old SHA `60e6dbb9…`: policy GET returned edition; Conduct Ack card vanished | **FAIL** |
| T03 | S3 document interrupted upload, same-ID resume, replacement | Real S3/MinIO/scanner acceptance not yet demonstrated | PENDING |
| T04 | Real elapsed meeting Chromium cancellation/reschedule/attendance | Complete elapsed browser path not qualified | PENDING |
| T05 | S3 scanner/worker kill and recover | Historical partial qualification only | PENDING |
| T06 | Full forward-only migration history from populated older DB | CM1 partial historical tests; exact HEAD full upgrade absent | PENDING |
| T07 | M5 current recipient inbox and retired notice window | PASS@8e536875… [38127290650](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38127290650); PASS@08142c21… [38128147331](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38128147331) | Historical scoped PASS |
| T08 | M5 concurrent workers / 72h catch-up / real kill/restart | 14 PostgreSQL PASS@af0abf53… [38128475743](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38128475743); process kill pending | Partial |
| T09 | M5 date move / handoff / escalation / exception real roles | Older integrated and focused tests only | PENDING |
| T10 | M6 shape, source, auth, quota, sanitized audit | **PASS@be72be322ce6e15258f5da574f5ce5686d2d0871**, 24 existing PostgreSQL tests [38133071154](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38133071154) | Focused PASS |
| T11 | M6 action/blocker evidence provenance | Included in 24 AI focused PASS@be72be322ce6e15258f5da574f5ce5686d2d0871; not full natural-language entailment | Focused PASS |
| T12 | M6 false-fact admission and robust semantic answer-to-evidence | Earlier STOP (4/7 unsupported admitted) at `00a9219c…` [38131859968](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38131859968). Now **0/7 unsupported admitted** in developer synthetic sample at `be72be322ce6e15258f5da574f5ce5686d2d0871`, [38133071154](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38133071154) | **CANDIDATE_ONLY**; independent semantic evaluation PENDING |
| T13 | Actual approved provider inference, factual support, honest abstention | Unapproved external call/cost; no live model tested | BLOCKED |
| T14 | M7 evidence-gated HR closeout and immutable audit | PASS@eeb28849… [38129044659](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38129044659); full real journey untested | Historical scoped PASS |
| T15 | M7 HR per-case dashboard with auth/races | PASS@c48f5c1b… [38130225197](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38130225197); browser pending | Historical scoped PASS |
| T16 | M7 HR current-assignment portfolio/pagination/created case | PASS@fb59c454… [38130736087](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38130736087); browser/security pending | Historical scoped PASS |
| T17 | Independent M1–M4 source/security requalification at final HEAD | Older SOURCE GO not production GO, current HEAD independent requalification absent | PENDING |
| T18 | Full integrated exact-HEAD PostgreSQL + React + Chromium + storage + recovery suite | Development-focused runs only | PENDING |
| T19 | Approved current-code hosting, migrations, HTTPS, worker safety | Render LIVE on old `b4312679…`, autoDeploy OFF, no worker | BLOCKED |
| T20 | Hosted J01 HR→employee→IT→manager→training→closeout | No qualifying hosted path | 0 PASS |
| T21 | Hosted J02 denied/accepted secure document revision chain | Real document intake unavailable on free evaluation | 0 PASS / BLOCKED |
| T22 | Hosted J03 IT blocked → reminders/escalation → recovery | Always-on worker unapproved/unqualified | 0 PASS / BLOCKED |
| T23 | Hosted J04 real model supported policy and honest abstention | T12 independent eval and T13 real model not qualified | 0 PASS / BLOCKED |
| T24 | Hosted J05 denial, idempotency, retries, durable audit | Hosted exact SHA not qualified | 0 PASS |
| T25 | Real hosted demo video, design/setup/deployment docs, delivery | Hosted product not ready; submission not authorized | PENDING |

## Weighted milestone estimate (non-acceptance)

| Milestone | Weight | Earned | Pending |
|---|---:|---:|---:|
| M0 | 5 | 5 | 0 |
| M1 | 9 | 8 | 1 |
| M2 | 10 | 8 | 2 |
| M3 | 13 | 10 | 3 |
| M4 | 11 | 8 | 3 |
| M5 | 15 | 11 | 4 |
| M6 | 15 | 5 | 10 |
| M7 | 7 | 5 | 2 |
| M8 | 7 | 2 | 5 |
| M9 | 5 | 0 | 5 |
| M10 | 3 | 1 | 2 |
| **Total** | **100** | **63** | **37** |

Estimate intentionally unchanged pending independently evaluated answer capability and integrated real-browser/hosted gates. No scope reduction: PRD v1.1 28 requirements, four roles, ten exceptions, J01–J05. Next development targets full M6 useful policy answers from server-authorized facts (without paraphrasing unverified prose), M5/M7 remaining functional flows; then consolidated T02/T03/T04/T08/T17/T18. Do not deploy or spend without authorization.

### Current pending M6 policy-quote test slice

Exact implementation + test SHA: `6481876a2328f054eaedaf84db1bcc0b2471ebdc`; [focused run 38146123757](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146123757) **QUEUED** as last inspected. Intermediate run 38146056504 at `7e580a40…` QUEUED and not sufficient. New full-edition policy quotation is not qualified until CI concludes successfully, and passing it would not close T12 independent relevance or T13 real-provider gates. Previous validated candidate at `be72be32…` remains 24 existing PostgreSQL + 4 adversarial/semantic + 20 React PASS. T01–T25 and 63/37 estimate unchanged; no deploy.

### T02 focused real-browser diagnostic — queued

Source commit `71ce39459e53445696a950ed3cdafc5c04b68fba` adds a **real** two-role synthetic HR→Employee Conduct Ack Chromium reproduction (create template and case, activate, read exact frozen edition, assert same card visible, explicitly acknowledge, reload to check immutable evidence), plus error/DOM diagnostics. JavaScript source parse checked locally without executing browser; [self-hosted run 38146978776](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146978776) is **QUEUED**, so T02 **remains FAIL** from historical [38126300241](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38126300241). Even a focused PASS would not close full four-role acceptance. M6 policy-quotation [38146123757](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146123757) is also **QUEUED**. No source-level fix for missing card has been claimed, and no test gate is downgraded. Estimate unchanged 63/37, hosted 0/5.

### M6 deterministic case-assigned policy reader — exact-SHA CI pending

Source commits: `bf9e69a33fa1139270297514f0f34f74f8469f76` (offline source answer + React representation), `6bfc89ccd7fd25c5034d7b29572972f992954eb9` (model-config-independent strict policy routing), and **`4aeeac2214b43f7f2a6b8c564c44642854d1139b`** (Django HTTP authorization test + include full new test file in M6 workflow). Tests include explicit conduct/privacy/benefits reading, false financial/instruction requests, IT/Manager denial, role/source provenance, stale context, long-document refusal, mocked configured provider bypass and real Django HTTP response with no-store/citations. These are **COMMITTED / NOT YET QUALIFIED**, not PASS. Self-hosted M6 [run 38147857389](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38147857389) was QUEUED at inspection. Historical M6 passed [38133071154](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38133071154) on `be72be32…`, not this HEAD. T10–T13 remain scoped/pending as above; T12 independent semantics and T13 real model still BLOCKED/PENDING. T02 historical FAIL and [targeted 38146978776](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146978776) QUEUED. Do not mark any hosted journey qualified; overall planning **63/37**, hosted **0/5 PASS**.

### Current completion sprint — source advanced, no unearned test credit

- Submission docs: `a2feb9c7e2ea94a38322c76ee0984e53bf1375b0`; corrected older LIVE Render SHA and current branch split, added actual-video and measurable-value evidence plan.
- Integrated current-branch PostgreSQL/React/real four-role Chromium workflow: `2cc3ed73fbfd5fa4a043477d95d5720a012c5ef2`; [run 38150225570](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38150225570) **QUEUED**. Full source regression + browser suite still **NOT QUALIFIED**. Integration does not include real S3/ClamAV/worker kill, live AI, independent security or J01–J05.
- Working UX correction: **`221c44328a260fb5e1eed3d093dd99859fb03bc3`** adds one-click, role-gated exact policy source reading and corrects input placeholder to supported offline grammar, with pure React helper tests. [Current M6 run 38150383695](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38150383695) and [M7 run 38150383700](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38150383700) both **QUEUED** at inspection.
- Historical T02 browser FAIL remains; [T02 diagnostic 38146978776](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146978776) QUEUED. No current live model, worker/S3-hosted qualification or video.
- GitHub connector cannot list actual runner registration/status. Only owner-run diagnostic in [runner queue recovery](../operations/runner-queue-recovery.md) can confirm current VM registration and service health. Never infer offline as fact from "queued" alone.

**Planning estimate unchanged: 63/100 earned, 37/100 pending (non-audited ±10–15); hosted J01–J05 = 0/5 PASS.**

### 11 October CI recovery — observed execution, failures and corrections

- Runner assignment probe [38151500790](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38151500790) **PASS** on original self-hosted runner `eoc-mac-ci-01`; NTP and job assignment restored.
- T02 focused [38146978776](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146978776) **PASS at 71ce39459…**: one genuine HR/Employee Chromium assigned Conduct policy reading, policy acknowledgement, persistence and reload. Earlier full four-role T02 FAIL does not turn into full GO; the full four-role current-source Chromium remains PENDING.
- Earlier M6 source candidates [38146123757](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146123757) and [38147728690](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38147728690) **focused PASS at their own historical SHAs**. No independent semantic relevance or real model provider was qualified.
- First integrated [38150225570](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38150225570) **FAIL at 2cc3ed73…**: 219 backend PASS, 2 skipped (live S3/ClamAV), one 404 in `test_offline_policy_http_response_is_scoped_unchanged_and_not_a_model`. React and Chromium were not reached. Root cause in synthetic HTTP fixture: Django `force_login()` bypasses real login and does not create `m1_session_started`; `SessionGuard` correctly rejects incomplete sessions.
- Correction `edb6317f267da197acc1ff82099977fde410a204` replaces test-only login shortcuts with actual synthetic HTTP login for Employee and Manager; no authentication relaxation. [M6 38152246137](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38152246137) and [integrated 38152246169](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38152246169) queued at initial inspection. A queued job earns no credit.
- No full current-SHA qualification, independent release security, hosted J01–J05 or real-provider inference. Estimate remains 63/37; hosted 0/5; production STOP.

### Full four-role browser case-selection synchronization — correction candidate

- [Integrated 38152246169](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38152246169) **FAIL** at `edb6317f…` despite **220 backend PASS, 2 skipped and React tests/build PASS**. It reached Chromium, but `Conduct Ack` card disappeared after the policy GET (HTTP 200 and version `synthetic-conduct-v1` were verified). Full four-role acceptance remains STOP.
- [M6 38152246137](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38152246137) **PASS at `edb6317f…`**, confirming repaired real HTTP synthetic login and focused M6 contract. [M7 38150383700](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38150383700) **PASS at historical `221c4432…`**, not new HEAD.
- Root-cause evidence: full `openCase()` asserted an already-visible previous case region, then conditionally clicked `View all steps` before the asynchronous `selectCase()` fetch and `setShowFullPlan(false)` completed; focused T02 test opens case once and had passed. Browser helper now waits for the actual `GET /cases/{id}/tasks` HTTP 200, busy-to-enabled UI settlement, and 17 rendered tasks after opening the full plan. No frontend workflow authority, policy assertions, security checks or task count are weakened.
- Trigger the new integrated workflow on the browser spec path; PASS is pending exact-SHA Chromium execution. Hosted J01–J05 0/5, production release STOP, progress estimate unchanged.

### 11 Oct next integrated Chromium failure and fix candidate

- [38153254420](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38153254420) FAIL on `7351764b5e2113c5033c68aebb10e12748fb5cbb`: **220 PostgreSQL tests PASS, 2 live S3/ClamAV SKIP**, frontend tests/build PASS. Full browser stopped at its *first* `openCase(hr)` call (line 122), immediately before case activation. The updated helper incorrectly required `View all steps (advanced)` while the CREATED case properly had zero tasks and no full-plan control. This is a test-sequence defect; do not instantiate tasks before activation to satisfy it.
- The browser helper now parses the exact case-tasks GET response, asserts empty tasks plus genuine `Activate case` and absent full-plan button for unactivated cases, and requires **17 tasks** and full-plan visibility for activated cases. Both branches retain positive assertions. The previously fixed async selection barrier remains. Current branch exact-SHA integrated Chromium PASS is required; no production or hosted credit yet.

## 12 Oct — exact-SHA focused qualification PASS

- [Self-hosted CI run 38178074575](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38178074575) **PASS at `d69cbcee00c7dc6b16ad72da474dd92a25989340`**. 16 focused PostgreSQL/unit M5 tests passed (5 nonfatal warnings). Shell entrypoint syntax, migration checks and locked dependency validation passed.
- **EOC_M5_REAL_WORKER_CRASH_RECOVERY_PASS:** genuine child Procrastinate control process died after committed reminder effect and before job acknowledgement; a heartbeat-based retry made the same job `todo`; a new worker completed it with exactly one active overdue reminder.
- **EOC_M5_REAL_PERIODIC_CONTROL_WAKE_PASS:** same running worker independently deferred and completed a real once-per-minute periodic M5 job, not invoked by the test via manual deferral.
- All crash test env flags are restricted to isolated local non-Render PostgreSQL. The dedicated Render Starter worker proposal has **not** been deployed or billed. Source-level worker/recovery/scheduler qualification: **PASS**; full repository integrated regression: **PENDING**; live J03: **BLOCKED — no hosted always-on worker**.

## M5 integrated completion — verified 12 October 2026

- [Full integrated run 38178300531](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38178300531) **PASS** at application SHA `9c567d6ac1491bd1403cbd03296cd1d55b33ece8`: **235 backend PASS / 2 live storage tests SKIPPED**, **26 frontend PASS**, Docker production image PASS, compiled asset check PASS, real four-role Chromium case journey PASS.
- [Focused M5 run 38178074575](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38178074575) **PASS** at prior source SHA `d69cbcee00c7dc6b16ad72da474dd92a25989340`: 16 tests PASS; real separate worker crashed after durable reminder commit and before ACK; stale heartbeat recovery succeeded with only one active reminder; automatic periodic one-minute worker job succeeded.
- **M5 source development for current in-app reminders, automatic periodic scheduling, HR escalation and dead-worker recovery: QUALIFIED.** No email/SMS delivery claim, no hosted uptime SLA.
- **Hosted J03 remains BLOCKED:** Free Render web has no continuously running worker. The paid Starter worker in `render.full.yaml` was updated but NOT deployed or authorized for billing. Source-level PASS is not hosted acceptance. J01–J05 0/5 full hosted PASS.

## 12 October — M6 source improvement, qualified focused tests

- **Exact question-to-source relevance gate:** model-presented canonical facts must answer the exact named task/policy intent; a true citation alone cannot be used to answer compensation, unrelated task, compound or injected questions. If a question does not fit the deliberately narrow grammar, no SUPPORTED/PARTIAL publication is admitted (uniform supported abstention permitted). The logic runs **after** server-side canonical source, authorization and case-version checks. This is not a general semantic entailment engine.
- **Provider-response hardening tests:** structured JSON extraction, refused/incomplete/multiple output, overlarge HTTP response, invalid usage, network/HTTP error, timeout, 16KB context limit, API request `store:false`, 12-second timeout and redacted failure behavior. All transport tests are fake network and incur no API charges.
- [M6 grounded suite 38179953152](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38179953152) **PASS** at code SHA `e65cd7936ddb8020ebc441925be0d06ee9da0807`: **60 PostgreSQL-backed/adversarial and provider-transport tests PASS**, 2 warnings.
- [M6 established contract suite 38179953115](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38179953115) **PASS** same SHA: **36 backend tests, 6 frontend source tests and 26 React tests PASS**.
- Corrected integrated current-head candidate `c2e0d8b323fcbb3b7f84ad78bad5a570c38dbd30`, [full integration run 38180256254](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38180256254) **IN PROGRESS AT RECORD TIME**. An earlier integration run had invalid workflow YAML and ran no tests; fixed by moving `EOC_AI_PROVIDER: DISABLED` and `OPENAI_API_KEY: ''` into *job* environment instead of PostgreSQL service. Do not mark integrated PASS until the new run finishes successfully.
- **External inference/hosted J04 still BLOCKED**: Free Render remains `EOC_AI_PROVIDER=DISABLED`, no provider key, no expenses, no real-model independent semantic evaluation or hosted AI reliability observation; all five hosted J01–J05 remain 0/5 full PASS. Read [M6 model admission operations](../operations/ai-admission.md).

## M6 final integrated source candidate — 12 October 2026

- [**Full application CI 38180256254**](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38180256254) **PASS** on immutable **`c2e0d8b323fcbb3b7f84ad78bad5a570c38dbd30`**: **253 backend tests PASS, 2 live-storage tests SKIP, 26 frontend tests PASS**, production Docker PASS, compiled frontend assets PASS, real four-role Chromium PASS.
- Earlier [M6 focused new relevance/transport suite 38179953152](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38179953152) **PASS** at `e65cd7936ddb8020ebc441925be0d06ee9da0807`: 60 tests PASS. [Prior M6 established contract suite 38179953115](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38179953115) **PASS**, 36 backend contract, 6 frontend source and 26 React tests. The complete integration run above also covers the newer source.
- **M6 offline source admission/transport hardening: QUALIFIED.** Narrow exact question-to-evidence relevance admission blocks true-but-unrelated canonical answers, and provider transport malformed envelopes fail closed. This remains a deliberately limited task/policy assistant; neither independent real-model semantics nor broad natural-language relevance has been demonstrated.
- **M6 hosted J04: BLOCKED.** No owner approval for paid inference or real external model provider, no live model semantic/adversarial dataset evaluation, no hosted provider cost/reliability evidence. The current Free Render web continues running its older qualified application and `EOC_AI_PROVIDER=DISABLED`; new source commits were NOT deployed. Hosted J01–J05 0/5 complete PASS.


## 12 October — D3 secure-storage correction and real-service qualification (current overlay)

This section **supersedes older T03/T05/T18 rows for current work only**; the complete
T01–T25 status overlay and 70/30 weights remain in
[`docs/handoffs/eoc-continuation-2026-10-12.md`](../handoffs/eoc-continuation-2026-10-12.md).
Historical evidence must not be re-labelled.

- **Current D3 application source candidate:** `3cfa126e79aa9c8784ea84f9633e40c559dec2f8`.
  GitHub branch `feature/eoc-completion-development`. This is **COMMITTED, NOT YET QUALIFIED**.
- **D3-01 storage endpoint trust boundary** introduced at `bb66033885eca6f6c48de8662e3bd0acbd60bf58`:
  custom S3 endpoints now require explicit local-test authorization *and* strict loopback,
  port 9000, no embedded credentials, query, fragment or path; rejects before boto3 I/O.
  The new negative test checks remote redirection and absent AWS KMS fail-closed.
  This is a source correction, not evidence of deployed production storage.
- **D3-02 genuine live-service runner setup**: first live run
  [38194157132](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194157132)
  at `bb66033885eca6f6c48de8662e3bd0acbd60bf58` **FAIL**, prior to tests.
  Job log: `clamav/clamav:1.4` lacks an ARM64 manifest; MinIO also logged a
  cross-device directory rename. Correction at
  `553b0b049fc6f66428a5772a2accf99666fa3e4e` uses the published ARM64
  `clamav/clamav-debian:1.4.6` image and a runner-owned temporary host bind
  mount for MinIO, cleaned up after the job. **Correction NOT YET QUALIFIED**.
- **D3-03 real interrupted PUT**: candidate
  `3cfa126e79aa9c8784ea84f9633e40c559dec2f8` adds a real MinIO
  process hard-exit *after* the S3 PUT but *before* Django stores the object
  receipt, then checks exact-upload-ID and idempotency-key recovery, one
  quarantine version, one audit receipt, one queued scan job, and no task
  completion. This is a real-service test candidate, **not a recorded PASS**.
- Current exact candidate workflows:
  [live MinIO + ClamAV 38194374320](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194374320)
  and [full PostgreSQL + React + Docker + Chromium 38194374258](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194374258)
  were **QUEUED/PENDING at this ledger write**, not PASS.
  Intermediate [live 38194301113](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194301113)
  is also queued at the preceding workflow-only SHA; an older integrated
  [38194157099](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194157099)
  was running at `bb66033885eca6f6c48de8662e3bd0acbd60bf58`,
  **not current D3 application source**.
- **T03:** OPEN pending real S3 interrupted PUT/resume, object version verification,
  malware rejection, revision replacement, negative authorization and audits.
  **T05:** OPEN pending actual ClamAV clean/malware and scan-worker kill/recovery,
  including scanner failure/restart. **T18:** prior integrated PASS@ `c2e0d8b3`
  remains historical only; current D3 integrated run PENDING.
- **Remaining D3:** resolve any live-service failures with actual logs; prove all
  new and existing live tests; inspect scanner-outage recovery, promotion-after-crash,
  private-bucket security and frontend integration; do not prematurely close T03/T05.
  **D4–D6, T17 and T19–T25 still OPEN/BLOCKED**. Hosted J01–J05 **0/5 PASS**.
  Keep the synthetic hosted case unchanged; no Render deployment or paid services.
- **Conservative weighted estimate remains 70/100 earned, 30/100 pending** with
  the handoff's ±10–15 point uncertainty. These unqualified D3 changes earn no
  additional progress credit.


### 12 October D3 subsequent exact-run evidence — service-level PASS and open final candidate

- [Full integrated 38194157099](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194157099)
  **PASS@bb66033885eca6f6c48de8662e3bd0acbd60bf58**: 254 backend passed,
  2 live-service skipped in the general suite, React tests/build, Docker build,
  compiled assets and real four-role Chromium pass. No real S3 in this workflow.
- [Live M3 38194301113](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194301113)
  **PASS@553b0b049fc6f66428a5772a2accf99666fa3e4e**: 2 real MinIO
  and ClamAV tests, with one non-fatal PostgreSQL teardown warning.
  Corrected ARM64 Docker service configuration actually ran.
- [Live M3 38194374320](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194374320)
  **PASS@3cfa126e79aa9c8784ea84f9633e40c559dec2f8**: 3 real-service
  tests, including actual process hard-exit after S3 PUT and exact same-intent
  re-delivery without duplicate version, audit or scan job; one teardown warning.
- [Full integrated 38194374258](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194374258)
  **PASS@3cfa126e79aa9c8784ea84f9633e40c559dec2f8**: 254 backend
  passed, 3 real-service skipped in general suite, React, production Docker,
  real four-role Chromium all pass. Real-service tests are separately qualified,
  never counted as general-suite passes.
- [Live M3 38194704739](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194704739)
  **PASS@2b7ea753117ddabaa47489f22732136b128320cc**: 4 real MinIO/ClamAV
  tests including actual scanner pause, refusal to issue clean evidence while
  unavailable, unpause and recovery on same object, with one teardown warning.
  The broader T05 release gate still needs further negative/restart review.
- **Clean-promotion retry fix** at `6d0201cffc839931ae0238fafac8aa1b5790b00b`:
  verifies an existing exact-version clean object before recopying after lost
  database receipt. Offline failure tests and actual post-S3-copy/finalization
  interruption regression committed. [Integrated 38194890046](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194890046)
  and [live 38194890025](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38194890025)
  were RUNNING/QUEUED respectively at this ledger update; **NOT YET PASS**.
- **Private object denial test** added at current code candidate
  `d2cad8f206e661d668d35893dd3eb784dc42fc31`:
  unsigned reads of both quarantine and clean S3 versions must fail.
  [Live 38195127881](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38195127881)
  and [integrated 38195127902](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38195127902)
  were **QUEUED/PENDING; no credit yet**.
- **Current scope**: D3 ongoing; T03/T05 **partially qualified in isolated real
  services, not production-complete**; T18 most recent PASS is older `3cfa126e`,
  latest exact source pending. No real hosted S3/ClamAV, persistent worker or
  AI provider. T19–T25 unchanged; hosted J01–J05 **0/5**.
  Weighted estimated delivery remains **70/100, uncertainty ±10–15 points**.
  Next action: inspect current exact-run outcomes, resolve failures, verify
  private access and clean-promotion retry, then complete remaining D3 before D4.


### 12 October — latest D3 code qualification verified (supersedes earlier pending rows)

- **Application code exact SHA:** `d2cad8f206e661d668d35893dd3eb784dc42fc31`.
  Newer branch commits before this overlay are CI diagnostics/workflow edits, not a new
  production behavior claim.
- **T03/T05 isolated live integration:** [38195127881](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38195127881)
  **SUCCESS / 6 passed** on real, local isolated versioned S3-compatible
  storage and live ClamAV with fresh signatures. Includes actual hard process
  exit after PUT then exact upload-ID recovery, scanner rejection, clean
  quarantine promotion, pause/unpause service outage, post-copy DB failure
  recovery, post-scan worker hard exit/retry, anonymous bucket-version denial.
  These are **isolated real-service PASS**, **not a hosted deploy** or blanket
  third-party security certification.
- **T18 current D3 application code integration:** [38195127902](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38195127902)
  **SUCCESS / 255 backend passed, 6 expected live-storage skipped in the
  general suite**, React tests/build PASS, production Docker PASS and real
  four-role Chromium PASS. Those six skipped tests passed separately in
  38195127881; do not double-count them in the general suite.
- **One remaining observed hygiene issue:** pytest-django reports
  `database "test_onboarding_m0" is being accessed by other users`
  during teardown (one PostgreSQL session), despite test-step PASS. This is
  a **non-fatal cleanup warning, not resolved**; it must not be hidden or
  counted as a production defect without identifying the session owner.
  Diagnostic commit `9ba789f516c674328b3c5d7fbb0b69e75a14aa39`
  added test-only session metadata. Live diagnostic
  [38196021734](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38196021734)
  **SUCCESS, 6 PASS / same warning**; output capture was not visible under
  default pytest settings. Workflow-only `1ee831768d4f2f6038c6fd260175ea03c3176910`
  enables pytest passed-test stdout display; [38196143451](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38196143451)
  was QUEUED at this entry. Do not assert the warning is closed until verified.
- **D3 scoped status:** all six current live-service tests and current D3
  application-code integration passed. Remaining before complete D3 release
  acceptance: resolve teardown hygiene, reconcile any uncovered negative cases,
  and ensure the full PRD/user-journey and independent security gates are
  separately reviewed. Preserve hosted service SHA, synthetic case and credentials.
  No hosted J01–J05 tests authorized now. **Production/evaluation GO remains STOP;
  hosted acceptance 0/5; conservative weighted estimate 70/30 unchanged**.


### D3 PostgreSQL teardown root-cause correction and final invariant — 12 Oct

- Previously observed non-fatal test cleanup warning was reproducible with
  six otherwise-passing real S3/ClamAV cases. Isolated PostgreSQL
  `pg_stat_activity` diagnosed exactly one extra idle client backend
  (test-only backend PID varies between runs); the worker tests did not
  demonstrate a production data-integrity failure.
- Source test correction
  [`a92f2f0f52b2dc4eaea1c88c5c04d2a5afd0270b`](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/a92f2f0f52b2dc4eaea1c88c5c04d2a5afd0270b)
  moves the genuine Procrastinate stalled-job retry controller out of the
  pytest process into a short-lived subprocess with actual isolated PostgreSQL.
  No scan verdict, task completion or production behavior was relaxed.
- [Live run 38196770355](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38196770355):
  **SUCCESS, 6 PASS, no PostgreSQL teardown warning**. Diagnostic output
  recorded `M3_POST_WORKER_PG_SESSIONS=[]` and
  `M3_POST_WORKER_SOCKET_OWNERS=[]`; this supports closure of the
  observed test-hygiene defect at that SHA. Root-cause assignment to the
  in-process async controller remains an engineering inference based on the
  changed execution boundary and reproduced clean behavior.
- Final cleanup candidate at
  [`4cda23d3d7da07d98104e3d51f05f273c232baaf`](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/4cda23d3d7da07d98104e3d51f05f273c232baaf)
  replaces diagnostic printing with a positive **zero-other-PostgreSQL-sessions
  assertion** in the actual crash/retry test, restoring concise pytest CI
  output. [Final real-service run 38197120380](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120380)
  and [integrated 38197120335](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120335)
  were **QUEUED/PENDING** when recorded; do **not** mark `4cda23d3` PASS
  until both exact-SHA checks complete.
- T03/T05 isolated real-service paths at `d2cad8f2` were previously
  qualified 6/6 PASS; no changes to hosted permissions, external storage,
  credentials, actual employee data or Render were made. This does **not**
  close T17 independent security, T19 release approval or T20–T24 hosted
  acceptance. Hosted J01–J05 remains 0/5; delivery remains 70/30 estimated,
  subject to remaining D4–D6 and release gates.


### Final D3 isolated-source closure evidence — 12 October, exact SHA

- Current final D3 test/CI hygiene commit
  [`4cda23d3d7da07d98104e3d51f05f273c232baaf`](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/4cda23d3d7da07d98104e3d51f05f273c232baaf)
  replaced temporary diagnostics with a durable assertion requiring no
  additional PostgreSQL sessions after real killed-worker recovery. This
  is **test-only** compared with previously qualified application code
  `d2cad8f206e661d668d35893dd3eb784dc42fc31`.
- [Live self-hosted ARM64 38197120380](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120380):
  **SUCCESS at 4cda23d — 6/6 genuine versioned MinIO + ClamAV PASS,
  0 pytest teardown warnings**. No real employee data or paid infrastructure.
  The earlier idle-session warning is **CLOSED within this isolated test**:
  recovery control runs in a separate short-lived process, and the
  assertion detects a future extra Postgres session.
- [Full self-hosted integration 38196770341](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38196770341):
  **SUCCESS at a92f2f0** (immediately preceding test-only cleanup guard).
  The [final 4cda23d integrated run 38197120335](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120335)
  remained **IN_PROGRESS in the PostgreSQL regression step** at this
  tracker snapshot; exact-SHA final integrated PASS cannot be claimed
  before its conclusion.
- **Scope of closure:** currently tested D3 source-level real-service behaviors
  are qualified and the demonstrated test teardown defect is corrected.
  This is not evidence of hosted secure-document operation, independent
  security certification or completed PRD J02. T03/T05 retain **hosted/
  release gates**, T17/T19–T25 remain unqualified, and hosted J01–J05
  remain 0/5. Overall delivery estimate remains conservatively 70/30.


### 12 October — D3 last integrated cancellation, immutable-SHA retry

- [Integrated run 38197120335](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120335) **attempt 1 FAIL at `4cda23d3d7da07d98104e3d51f05f273c232baaf`**. Its log explicitly verifies **255 backend PASS, 6 real-storage SKIP** in the general suite, React tests/build PASS and production Docker build PASS. The Chromium step was **cancelled during the standalone npm install of @playwright/test**, before starting the Django browser server or executing a Chromium assertion. The runner printed `The operation was canceled` after approximately 65 seconds in that step; reason for cancellation **not established**. Do not call it a failed browser assertion or an integrated PASS.
- [Live S3/ClamAV run 38197120380](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120380) **SUCCESS at the same application/test SHA**, **6 passed** with **no PostgreSQL teardown warning** and a positive no-extra-connections assertion.
- The cancelled integration **job 114642892177 was explicitly rerun using GitHub Actions**, reusing the **same immutable SHA** with run ID 38197120335, **attempt 2 QUEUED at last check**. This does not alter application source, require paid CI, or qualify Chromium before the rerun finishes.
- **T03/T05 isolated qualification remains PASS** within tested MinIO/ClamAV scope. **T18 final exact-SHA integration is OPEN** pending attempt 2. Do not deploy, restart hosted J01–J05, or modify synthetic hosted data. Conservative overall weighted estimate remains 70/30; hosted acceptance 0/5, release GO STOP.


### 12 October — D3 exact-SHA integrated and isolated CI gates PASS

- The complete [integrated workflow 38197120335, attempt 2](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120335) is independently verified **COMPLETED / SUCCESS**, at immutable SHA `4cda23d3d7da07d98104e3d51f05f273c232baaf` (GitHub run updated 2026-10-12 04:30:10 UTC). All steps passed: pinned checkout, uv/Node installation, locked dependencies, Django checks/migrations, **PostgreSQL backend regressions**, **React tests/build**, lockfile consistency, **production Docker image build**, **real Chromium four-role onboarding/case/dependency/policy/document journey**, and final `End of scope` marker. The previously cancelled attempt 1 is superseded as integration evidence by successful attempt 2; it is not a second code failure.
- The independently verified [live MinIO + real ClamAV workflow 38197120380](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120380) **COMPLETED / SUCCESS** at the **same SHA**, **6/6 passed, no pytest teardown warnings** with the zero-extra-Postgres-session guard. This closes the demonstrated isolated crash/retry test-hygiene defect and source-level D3 real-storage/scan CI checks.
- Runner recovery evidence: runner `eoc-mac-ci-01` had token/time-skew and missing/obsolete registration; its systemd service was reinstalled after local registration recovery, and the owner verified GitHub `status=online`, `busy=true`, with labels `self-hosted, Linux, ARM64, eoc-mac-ci`. Do **not** claim the GitHub-side runner registry is permanently healthy beyond this successful attempt; monitor future CI.
- **D3 source + isolated live-service + integrated local/browser CI: QUALIFIED / CLOSED within tested scope.** Release and acceptance still **NOT qualified**: separately gated hosted document operation/semantic and security review, no authorized hosted changes, T17 independent security, T19 release approval, and J01–J05 hosted acceptance (0/5). Remaining D4–D6 implementation/qualification and release gates persist; conservative overall weighted project completion estimate remains **70%**, not automatically increased by an infrastructure retry. **Production GO: STOP.**


### D4 work initiated — 12 October, source and CI qualification pending

- D3 previous integrated/local real services are PASS at exact code SHA `4cda23d3` ([integration attempt 2 38197120335](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120335); [MinIO/ClamAV 38197120380](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38197120380)), as recorded above. No hosted/independent acceptance implied.
- [D4 functional implementation/test commit b91b01d7](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/b91b01d78cea7accd03c3463d0035c71cfe01c68) adds **independent manager-owned elapsed check-in and HR-dependent task** to isolated synthetic M4 fixture, an actual Chromium MISSED → blocked → reschedule → ATTENDED → unlocked path, and a dedicated self-hosted ARM64 workflow. It retains the prior HR overdue/cancel/reschedule path. **T04 source/test candidate only** pending [run 38204925335](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38204925335); Django activity regression and UI compilation steps succeeded, actual elapsed Chromium step was IN_PROGRESS at this write.
- [D4 requirements map 73b7ac41](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/73b7ac41660678552fdfe833f4f1cc407d07f75c) creates `docs/qualification/d4-requirements-exception-traceability-20261012.md`, mapping all F01–F28 and E01–E10 to existing candidate source locations and acceptance gates without silently awarding PASS.
- [CI routing commit 0e64242d](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/0e64242d70fcf86050748495a48191351859bd90) enables existing M5 role-handoff, joining-date/exception/recovery Chromium workflow on the **active completion branch**, with path-scoped CI. [Run 38205278706](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38205278706) **QUEUED** on single self-hosted ARM64 runner. Do not claim E05/E06 newly qualified until actual result.
- **D4 T04/E04 and E05/E06 test gates: OPEN until exact-run PASS.** D5/D6 and T17/T19–T25 persist, hosted J01–J05 0/5, production GO STOP, conservative estimated delivery 70/100 unchanged. No deployment, paid service, external inference or hosted case mutation.


### D4 terminal owner-handoff invariant — candidate at 12 October

- [Code/test SHA afaa448a28fd98fc54a5600eab942e75a2e8065f](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/afaa448a28fd98fc54a5600eab942e75a2e8065f) corrects `reassign_owner` to refuse **new** HR owner changes when the case is `COMPLETED` or `CANCELLED`, preserving replays of a valid committed prior idempotency receipt (receipt lookup precedes terminal-state guard). Negative PostgreSQL regressions for both states assert no added assignment, audit or command receipt.
- Exact-source [integrated 38205540765](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38205540765) and [M5-M6 browser owner/date/exception 38205540661](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38205540661) **QUEUED** at write, after a prior M5 browser [38205278706](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38205278706) also queued on the single runner. D4 real elapsed [38204925335](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38204925335) still **IN_PROGRESS**. No new D4 claims of PASS until exact logs are checked. Avoid unneeded additional CI pushes while self-hosted runner drains.
- **Qualified D3 baseline remains 4cda23d3. D4 terminal guard is implementation-only until complete PASS**; new commits do not supersede historical PASS. Hosted J01–J05 0/5, release STOP, overall estimate unchanged at 70%.

### D4 exact-SHA qualification verified — 12 October

- [D4 actual elapsed manager and HR Chromium 38204925335](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38204925335) **SUCCESS @ b91b01d78cea7accd03c3463d0035c71cfe01c68**. Isolated PostgreSQL activity regression **10 passed (2 nonfatal warnings)**; true elapsed HR overdue/cancel/reschedule and manager MISSED → task still incomplete / HR successor blocked → actual elapsed reschedule ATTENDED → HR successor READY, **2 real Chromium tests PASS (8.9 minutes)**. Final marker `EOC_D4_ACTUAL_ELAPSED_HR_MANAGER_MISSED_RECOVERY_PASS` verified. T04 and E04 local real elapsed activity paths: **SOURCE/CI QUALIFIED**. This is not hosted J01 or all types of missed training.
- [M5 actual owner/date/exception Chromium 38205278706](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38205278706) **SUCCESS @ 0e64242d70fcf86050748495a48191351859bd90**: **4 genuine Chromium tests PASS**, real Procrastinate periodic scheduler independently emits current-state reminder (`M5_REAL_PERIODIC_WORKER_REMINDER_PASS`, `M5_REAL_PERIODIC_SCHEDULER_CATCH_UP_PASS`). [Repeat on final code SHA 38205540661](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38205540661) **SUCCESS @ afaa448a28fd98fc54a5600eab942e75a2e8065f** with **4 Chromium PASS and real scheduler PASS**. E05/E06 current-source cross-role browser recovery paths: **CI QUALIFIED**, hosted J03/J01 still OPEN.
- [Complete current-source integration 38205540765](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38205540765) **SUCCESS @ afaa448a28fd98fc54a5600eab942e75a2e8065f**: **257 PostgreSQL backend PASS; 6 isolated real S3/ClamAV tests intentionally SKIP in general suite; 26 React PASS; production Docker PASS; compiled static assets PASS; genuine four-role Chromium PASS; final scope marker PASS**. The two terminal-case owner reassignment negative tests are included in the 257. The six separate live service tests remain **PASS at earlier D3 SHA 4cda23d3**; D4 did not modify storage/scanner behavior, but this latest full integration does not retest real services.
- Final **D4 implementation and covered regression paths locally QUALIFIED** for T04, E04 meeting recovery, E05 joining-date, E06 owner handoff and terminal-case freeze, as tested. **Not all 28 FRs independently accepted**, and the ten exception journeys are not all hosted. D4 remaining functional gaps require review against PRD source (especially full owner workflows and exception states), then D5 security/a11y/migrations and D6 operations/release. Independent final security T17, exact-SHA authorized deploy T19, hosted J01–J05 T20–T24 and final submission T25 **OPEN**. Hosted J01–J05 remain **0/5** and **production GO STOP**.
- Conservative overall completion estimate **70/100, uncertainty ±10–15 points** (not automatically increased for test reruns). CI on owner self-hosted ARM64. No paid infra, model provider calls, hosted mutations, or deploys.


### D5 populated upgrade history — 12 October, candidate awaiting exact CI verdict

- [Source/test f45a79af582cca6c3eaa5269cf6c820e5f870da2](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/f45a79af582cca6c3eaa5269cf6c820e5f870da2) extends the existing throwaway `ci_m4_upgrade_*` historical upgrade qualification without modifying older migrations or production records. For two correctly attributed populated installations (0018 and already-applied-older-0019), it now proceeds to **every current migration leaf**, asserts 0025 joining-date guard installed, confirms original case/manager-attestation/typed completion preserved. For two mismatched histories, 0020 must reject with SQLSTATE 23514, preserve existing contradictory rows and avoid recording 0025. The CI script explicitly refuses non-test database names and requires one of four hard-coded scenarios.
- [Self-hosted D5 run 38207624586](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38207624586) was **IN PROGRESS** at this tracker snapshot. **T06 current leaf/populated history = PENDING** until it reports success and markers for all four cases. Historical 0018→0020 CI evidence predates this full-leaf extension.
- D4 latest application-code PASS at `afaa448a`; this D5 commit modifies only a CI-only test script and workflow. Hosted J01–J05 0/5; no production data, paid infrastructure or deployed software changed; overall 70% conservative estimate unchanged.

### D5 T06 populated-history forward migration — PASS

- [D5 isolated PostgreSQL workflow 38207921011](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38207921011) **SUCCESS / exact SHA ea6de97e926eee4b1c1c6c9e7dd2e06d3031b7ca**. CI uses the owner self-hosted Linux ARM64 runner, PostgreSQL 17 service and four disposable `ci_m4_upgrade_*` DBs. The migration script never runs against a non-prefixed/non-allowlisted database and never changes old migration files or existing hosted/prod data.
- **Positive history 1:** populated onboarding 0018 with genuine matching MANAGER_PREPARATION actor → 0019/0020 → all current leaf migrations including 0023/0025; existing case, original manager attestation, typed TaskCompletion and case joining status preserved. Marker `D5_POPULATED_FULL_FORWARD_MIGRATION_PASS`.
- **Negative history 1:** populated onboarding 0018 with contradictory completion actor → migration rejected fail-closed at 0019, original task/evidence preserved, later 0020 and 0025 not installed. Marker `M4_MANAGER_UPGRADE_MISMATCH_FAIL_CLOSED_PASS`.
- **Positive history 2:** populated 0018 with **earlier 0019 already marked applied** and matching evidence → additive 0020 and all current leaf migrations; evidence preserved. Marker `D5_POPULATED_LEGACY_0019_FULL_FORWARD_MIGRATION_PASS`.
- **Negative history 2:** earlier 0019 already applied but contradictory actor → additive 0020 rejected fail-closed, record preserved, 0025 not installed. Marker `M4_MANAGER_UPGRADE_LEGACY_0019_MISMATCH_FAIL_CLOSED_PASS`.
- The first [run 38207624586](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38207624586) failed **before scenarios** because runner had no `psql`; corrected CI at `f52af15` uses locked psycopg. Second [run 38207725446](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38207725446) exposed a **historical fixture incompatibility** (current ORM demands `schedule_revision` at 0018); fixed test setup using Django migration-state model at `ea6de97e`, without adding fake columns or altering migrations. Superseding third run 38207921011 **PASS all scenarios**.
- **T06 defined source-level populated-history migration check: QUALIFIED in these four scenarios**. Production-scale populated snapshots, live hosting migration, backups and restore verification, independent D5 security review and release T17/T19 remain OPEN. Latest app code still `afaa448a` (D4 full integration PASS), D5 changes script/workflow only. Hosted J01–J05 0/5, production GO STOP. Conservative engineering estimate remains 70% ±10–15 points.


### D5 tenant isolation and notification DB-failure boundary — 12 October

- [New D5 multi-tenant HTTP tests 21a48084](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/21a480842acc81b57cd447c8f853ff3651982bd3) introduce a disposable **two-org and two-employee-within-one-org** Django/PostgreSQL fixture, probing 17 selected case-dependent GET endpoints and 3 unauthorized/CSRF POST commands with real session/CSRF request processing. Scope includes cases, task details, forms, documents and secure-document history, activities, policy, training, owner dashboards, exception and deterministic AI guidance. These selected probes do not represent every API, every role matrix or hosted J05.
- Initial [run 38208613731](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208613731) **FAILED** before the read matrix due to incorrectly named test policy task `code_of_conduct` instead of canonical `conduct_ack`. Corrected source [711a7d81](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/711a7d81ec0cb410d46d7a94464a4ab9e98952f5). The later candidate [run 38208674891](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208674891) was superseded/cancelled while queued. Do NOT count these as an authorization bypass or a PASS.
- [Notification boundary code/test candidate 4e078c20](https://github.com/Electro-Anurag/employee-onboarding-companion/commit/4e078c20866fe7fa1f1f02de6ca9a50cfc11a154) catches `DatabaseError` in recipient inbox and mark-read, sanitizing HTTP 503 and distinguishing read-only `NO_COMMAND_EXECUTED` from uncertain mutation `UNKNOWN`. Also catches authorization `PermissionDenied` as bounded not-found without reflecting account details. Three HTTP regression tests added at `backend/notifications/tests/test_d5_outage_boundary.py`, and included in focused D5 CI. Existing in-app notification and worker logic otherwise unchanged.
- Exact latest [D5 focused security run 38208898601](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898601), [PostgreSQL focused CI 38208898591](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898591), and [M5-M6 browser regression 38208898616](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898616), all at `4e078c20...`, **QUEUED** at last verification (owner's single self-hosted Linux ARM64 runner was executing older work). These gates **OPEN**, with no PASS inferred from commit alone. No production deployment or hosted case mutations.
- D3/D4 exact-SHA CI PASS and D5 T06 four-history migration PASS remain established independently. Hosted J01–J05 0/5, independent T17 and production deployment T19 OPEN, release STOP. Conservative weighted engineering estimate remains 70/100 ±10–15 points.


### D5 HTTP tenant isolation and notification outage — exact-SHA PASS

- [D5 dedicated security run 38208898601](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898601) **COMPLETED / SUCCESS** at immutable code SHA `4e078c20866fe7fa1f1f02de6ca9a50cfc11a154`. Exact runner log: **25 PostgreSQL-backed tests PASS, 7 warnings**; final `EOC_D5_TENANT_HTTP_CSRF_REASSIGNMENT_PASS@4e078c20...` marker present. All workflow steps succeeded, including locked dependencies, Django checks, isolated migrations, tests and lockfile verification.
- Selected **17 case-scoped HTTP GETs** were probed against separate-org HR/IT/Manager/Employee and a *different employee in the same organization*. Real session + CSRF-protected attempts to reassign a foreign case, start foreign task and create foreign exception were denied, with no new audit or receipt mutations. Authorized case reads and scoped collection positive controls passed. This is targeted API-path testing, NOT all possible endpoint permutations or independent security review.
- Three HTTP notification failure regressions qualified: DB failure on inbox → sanitized 503 `NO_COMMAND_EXECUTED`; DB/commit outcome uncertain on mark-read → sanitized 503 `UNKNOWN` and no automatic replay; invalid actor/authorization → bounded 404. No untrusted exception/SQL text disclosed by these probes. Existing concurrency, idempotency and DB integrity regressions in the same suite passed.
- Superseded [D5 run 38208613731](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208613731) failed on test's wrong synthetic policy key, corrected before successful final run. Cancelled [38208674891](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208674891) earned no qualification.
- [Broader focused PostgreSQL worker run 38208898591](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898591) was **IN PROGRESS** and [M5–M6 real exception browser 38208898616](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898616) **QUEUED** at ledger write. Verify them separately before claiming broad new-source regression PASS. D5 independent security T17, production-like restore/drill, broader accessibility and hosted J05 still OPEN. Production GO STOP, hosted J01–J05 0/5, conservative 70%±10–15 estimate unchanged.


### D5 exact-SHA worker/browser and disposable DB restore — PASS

- [Latest D5 secure HTTP suite 38208898601](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898601) **SUCCESS** @ `4e078c20866fe7fa1f1f02de6ca9a50cfc11a154`: 25 PostgreSQL-backed role, cross-org/same-org other-employee, CSRF, concurrency and sanitized notification DB-outage regression tests PASS (as above).
- [Current source focused Postgres+real Procrastinate recovery 38208898591](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898591) **SUCCESS** @ same `4e078c20` with **16 targeted PostgreSQL tests PASS**, actual worker hard exit/restart and durable exactly-once reminder proof `EOC_M5_REAL_WORKER_CRASH_RECOVERY_PASS`, plus `EOC_M5_REAL_PERIODIC_CONTROL_WAKE_PASS`.
- [M5 real exception browser and worker 38208898616](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38208898616) **SUCCESS** @ `4e078c20`: **4 real Chromium PASS**, actual HR/employee worker handoff `M5_REAL_FORM_HANDOFF_WORKER_BROWSER_PASS` and genuine periodic in-app reminder `M5_REAL_PERIODIC_WORKER_REMINDER_PASS`; exact full log inspected.
- [D5 disposable PostgreSQL backup/restore CI 38209892920](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38209892920) **SUCCESS** @ `89612688e33aa55fa8567031caaced369887a12a`. A fresh PostgreSQL 17 service contained only synthetic one-case/two-role task + typed manager evidence, immutable audit, durable command receipts, actual in-app reminders and migration rows. Executed the actual container `pg_dump` custom-format backup then `pg_restore` to distinct disposable `ci_d5_restored`; **before/after canonical state fingerprint and counts matched**, restored database independently rejected forged audit/TaskCompletion updates. Final markers `D5_RESTORED_AUDIT_AND_COMPLETION_IMMUTABILITY_PASS` and `EOC_D5_DISPOSABLE_POSTGRES_BACKUP_RESTORE_PASS@89612688...`. No files uploaded; temp backup deleted by step trap; no hosted/database/provider mutation.
- Earlier D5 restore [38209670813](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38209670813) failed synthetic notice seed because there was no truly due reminder. [38209803707](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38209803707) failed test assumption `PRE_JOINING` when joining date was today, correctly `ACTIVE`. Corrected fixture only at `e4f55398` and `89612688`, final rerun PASS. No production domain logic or older migrations changed.
- **D5 scoped CI qualification:** T06 four historical migrations PASS; tenant/CSRF and notification outage proof PASS; real worker/browser recovery PASS; synthetic database dump/restore and immutable evidence PASS. **Remaining:** T17 independent adversarial security at final release SHA, production-like object-storage & database backup/restore/retention plus RTO/RPO, full accessibility/responsiveness, exact full release T18 and hosted J01–J05 T20–T24, D6 delivery T25. Hosted J01–J05 **0/5**, production release STOP, conservative estimate **70/100 ±10–15 percentage points** unchanged.
