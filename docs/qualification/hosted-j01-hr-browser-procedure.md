# Hosted J01 — HR browser entry and controlled synthetic progression

## Exact application and evidence

- Public HTTPS: https://eoc-companion-web.onrender.com
- Last independently observed Render LIVE application SHA: `ec781ab7362da10648eea496b1402b8c317dcd4c` (verify again immediately before business mutation)
- The latest Git HEAD contains test/docs commits and need not equal the live application SHA.
- Owner reported successful HR browser login after direct copy of existing private Render password. Do not retry terminal HR login, reveal passwords or rotate credentials.
- This file is a procedure, **not** a PASS result. Record actual UTC timestamps, responses, UI transitions and SHA before updating the J01 verdict.

## Phase A — browser inventory (no mutations)

1. While signed in as **HR**, confirm the left navigation says `Role: HR`.
2. Open `Templates (N)`. Record whether a published `Employee First Month (Synthetic)` template already exists. A draft is not a published template.
3. Open `Cases (N)`. Record the number and status of any existing synthetic employee case (especially `CREATED`, `PRE_JOINING`, `ACTIVE` or `CLOSED`), without sharing employee information or internal IDs.
4. Send only `TEMPLATES: [count, published/default yes/no]` and `CASES: [count, statuses]`. If an appropriate case exists, inspect its tasks rather than creating a duplicate.
5. Do not create or publish anything until inspecting existing state. One live synthetic case under test is preferred; do not reset state or fabricate successful evidence.

## Phase B — controlled HR setup (only after Phase A)

1. If no published default template exists, HR selects `Create default synthetic 17-task template`, then opens the created draft and selects `Validate and publish`. Record genuine published state and version.
2. Use `Create an onboarding case` with the published default and existing synthetic Employee, IT and Manager accounts. Confirm the joining-date choice against the actual test plan before submission. **Do not choose a future joining date if same-day Day-1 transition is required:** Django enforces `JOIN_DATE_NOT_REACHED`. Conversely, do not falsify a real employee start date; this is synthetic-only.
3. Record case creation and transition `CREATED` → `PRE_JOINING` only after HR selects `Activate case`, confirming 17 instantiated tasks and prerequisite blocks. Record case version, role visibility, task inventory, and guarded rejection of invalid transitions.
4. Next, independently exercise each role’s real workflow. Never call missing worker, secure S3/ClamAV or disabled external AI paths "PASS" based on simulations.

## J01 full acceptance criterion

HR creates/activates and later explicitly closes the synthetic onboarding case; employee forms/documents and requirements have authentic independent HR verification; IT work and its approvals, manager meeting/training outcomes and dependencies persist; every applicable mandatory task has typed evidence; no open exceptions; case closeout and immutable audit are verified. A case created or a form accepted is only a **partial J01 step**, not end-to-end qualification. Without real storage, worker and provider, separately record J02–J04 blockers rather than substituting a mock.
