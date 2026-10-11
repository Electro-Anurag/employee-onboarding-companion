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
