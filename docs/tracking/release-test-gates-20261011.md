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
