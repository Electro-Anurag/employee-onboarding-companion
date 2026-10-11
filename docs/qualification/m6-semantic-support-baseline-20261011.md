# M6 semantic support baseline — developer-labeled synthetic evaluation

## Question and scope

Does the current server-side output validator reject *false prose* when a returned citation identifier is nevertheless authorized? The source-authorization and action/blocker-link checks are already passing. This new test provides independently explicit developer-supplied gold labels for a small case-state sample; **it does not contain or call a language model**.

## Method

- Create one synthetic onboarding case and activate its real PostgreSQL task snapshots.
- Build examples using the actual `manager_preparation` task's current role, state, due date, available action, another real blocked task and authorized citation IDs.
- Label 4 source-supported claims, 7 unsupported claims (including wrong owner/state/due date, invented cash bonus, wrong action/blocker source, invented source ID) and 1 safe abstention.
- Invoke the real production `validate_answer` as a black-box admission decision.
- Score unsupported claims accepted, unsupported claims rejected, supported claims accepted/rejected and safe-abstention acceptance. Write only synthetic case IDs/counts to the CI job log.
- A green evaluation test means the test correctly measured the current capability; **the semantic admission result must be separately reported, even when it is STOP**.

## Acceptance criteria and next work

- Evaluation harness runs reproducibly under focused PostgreSQL CI with zero provider calls.
- Known unsupported claim samples that reuse valid IDs must be visible as false admissions. Do not suppress them or count structurally valid citations as semantic truth.
- If any false admission remains, semantic AI admission is **STOP**. A future evaluator must demonstrate factual support under independent adjudication before full AI claims are authorized.
- Even a zero-false-admission result on these fixtures only yields `CANDIDATE_ONLY`, never real-provider admission or deployment GO.

## Limitations

All gold labels are developer-authored, not independently adjudicated. This is a tiny deterministic synthetic probe of the current output checker, **not** a model benchmark, prompt-injection guarantee, accuracy claim, natural-language entailment engine or a pass for hosted J04. Real-model evaluation, unbiased labeled datasets, private-data review, cost/latency controls and owner authorization remain open.

## Measured CI result — 11 October 2026

The [focused run 38131859968](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38131859968) ran the actual source SHA `00a9219c82529cb71ae627982877f50f3b4b762a`. CI succeeded because the evaluation accurately reported the present limitations, not because those limitations were remediated.

| Gold label (developer, synthetic) | Admitted by current validator | Rejected |
|---|---:|---:|
| Supported | 4 | 0 |
| Unsupported | 4 | 3 |
| Safe abstention | 1 | 0 |

The four unsupported admissions were `false_owner`, `false_state`, `false_due`, `invented_bonus`. Exact measured unsupported false-accept proportion in this sample: **4/7 (57.1%)**. Result: **SEMANTIC ADMISSION STOP**. Do not conflate this figure with external-model factuality or infer generalization. Full source/fixture is `backend/ai/tests/test_semantic_evaluation.py`.
