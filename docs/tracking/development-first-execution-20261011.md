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

## Next implementation order

1. M5 reminder and escalation recovery, worker outage/multi-worker evidence and handoff edge cases.
2. M6 grounded AI answer evaluation and opt-in real provider qualification only with approved private credentials/budget.
3. M7 dashboard and evidence-gated closeout; end-to-end business journey functional completeness.
4. Consolidated exact-SHA integration/browser/security qualification, free-only deployment, hosted J01–J05, video and submission. Preserve and resolve all deferred failures.

Do not auto-run the three expensive CI workflows on each development commit. Never claim exact-HEAD release qualification from old passing workflows.
