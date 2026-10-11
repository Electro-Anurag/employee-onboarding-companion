# EOC T02 — narrow Conduct Ack browser diagnostic

Current source baseline: 0d1de5212f342330568ebc26ba67d0070320a2ae.
Source: browser/m3-policy-card-focused.spec.cjs.
Manual-only workflow: .github/workflows/eoc-t02-policy-focused.yml.

Why this exists: a real four-role Chromium run (38126300241 at 60e6dbb9…)
failed after authorized GET /assigned-policy returned HTTP 200 with the expected
synthetic-conduct-v1 policy, but the focused Conduct Ack task card vanished.
The cause is not independently established. Source inspection finds the
loadPolicy handler only sets EvidenceWorkflows-local state; it does not call
case selection or the parent task refresh. Do not infer that a specific
React race is fixed from this inspection alone.

The new narrow browser path exercises real HR template publishing/case creation,
case activation, Employee session/CSRF, policy GET and edition display, explicit
acknowledgement, immutable progress and reload. No mocked browser state.
On failure the test reports the observed page, case/task card counts, full-plan
toggle, sanitized headings, UI alerts and browser console errors. The original
visibility assertion remains strict. The test uses the same disposable synthetic
database, pinned browser dependency and self-hosted Linux ARM64 runner.

Workflow is manual-only, deliberately NOT automatically queued while the
existing self-hosted CI queue is unresolved. This does not replace the full
M3–M4 four-role Chromium suite or hosted J01–J05. No new Run ID, PASS or
root-cause claim exists until actual successful execution and investigation
of any observed failure.
