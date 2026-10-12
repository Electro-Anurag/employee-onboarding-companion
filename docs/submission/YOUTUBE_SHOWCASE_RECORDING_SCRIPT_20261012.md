# YouTube showcase capture script — submission day

**Purpose:** Create an honest, watchable product showcase **before the 12 October 2026 cutoff**. The evaluator requires a YouTube URL, not merely a private local CI artifact. Upload action/visibility remains with owner.

**Minimum viable capture:** A **4–6 minute narrated desktop screen recording** combining a real browser journey if available, source-controlled engineering evidence, the real architecture and a candid AI trust-boundary description. Do not fabricate an AI response, type fake terminal PASS output or overlay a mock as live functionality. Existing [Chromium CI recording run 38235666178](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38235666178) can supplement real footage **with a caption that it was recorded in local CI at that specific run**.

## 00:00–00:30 — Problem and product proposition
**Narration:** “Employee onboarding is not one checklist. HR, IT, employee and manager each own evidence, approvals, readiness and timed handoffs. When one prerequisite stalls, nobody has a clear current picture. I built Employee Onboarding Companion to make onboarding state, ownership and next steps transparent and auditable.”

On screen: application landing page (if functioning), or architecture overview labeled **Product overview**; never present design art as real UI.

## 00:30–02:40 — Actual browser journey
Show the longest reliable real browser flow, preferably across four separate synthetic role sessions in the **same case**:
- HR creates/activates synthetic onboarding case from a published template and locates current status
- Employee sees only assigned tasks/policy and sends one actually saved form/acknowledgement if functional
- Manager or IT records an actually persisted update (IT external provisioning must be visibly labeled *simulated*)
- HR revisits the case to see the new state, dependency or review status

If a step is failing in the current demo, skip that action rather than manufacturing a success; show existing verified CI browser recording and cite its commit/run.

## 02:40–03:30 — AI: what it can and cannot do
**Narration:** “The assistant is intentionally read-only. It assembles a role-authorized onboarding case snapshot, calls an explicitly configured model, and independently checks that any returned fact and citation match the current case and the question. Invalid, unrelated or stale results fall back to deterministic guidance. The model cannot approve HR requests or mutate the workflow.”

Show `backend/ai/provider.py`, `backend/ai/validator.py`, `backend/ai/relevance.py`, and the real local-model admission test. **Distinguish mocked-provider CI from actual model inference.** Only show `MODEL_VALIDATED` if the real-model gate has actually passed. Otherwise call it an implemented adapter under runtime qualification.

## 03:30–04:20 — Technical design
Open [technical-design.md](technical-design.md) and display the Mermaid architecture:
React frontend → Django auth/API → PostgreSQL versioned tasks/audit → transactional Procrastinate jobs. AI read-only channel sits alongside the workflow engine, not inside its command authority.

Briefly explain role separation, idempotency/retry, versioning, immutable audit and why external services are synthetic in an evaluation.

## 04:20–05:10 — Evidence
Show [real integration run 38262893788](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893788), [PostgreSQL 18 migration run 38262893843](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893843), and [AI contract run 38262893822](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38262893822). Explicitly indicate these passed at `caf34f2b629f2ad2786b63d63fc0e93844239d7b` and that the live-model test was skipped. Never pass off a pending workflow as green.

## 05:10–05:35 — Close
**Narration:** “This submission demonstrates a real governed onboarding workflow with role-scoped actions and repeatable tests. The architecture permits completing the full synthetic journey and integrating a local AI provider safely; separate provider and hosted qualification are tracked explicitly. Full source, diagrams, tests and setup documentation are linked in the submission.”

## YouTube publication and reviewer-access check
1. On Mac, record the actual application and evidence using QuickTime Player → File → New Screen Recording or macOS Screenshot toolbar (Shift–Command–5).
2. Make sure the video is a **real recording**, contains a readable browser, clear audio and no credentials/real employee records. Do not record private GitHub URLs containing embedded access tokens.
3. Upload using owner's YouTube account, set **Unlisted** or **Public** so anyone with the URL can view without permission, and verify from a logged-out/private browsing window.
4. Copy its actual watch URL into the submission form and [EVALUATOR_SUBMISSION_PACKAGE_20261012.md](EVALUATOR_SUBMISSION_PACKAGE_20261012.md) as applicable. **No watch URL is prefilled because none was verified.**
5. Ensure source access: a private GitHub repository requires preauthorized evaluator access. Sharing its URL alone does not grant access; do not change its visibility without owner approval.
6. Preserve evidence of the submission receipt, cutoff time and content. Post-submission improvements may not change what evaluators actually assess if the rubric freezes artifact versions.

**If the current hosted site is not at the qualified source revision:** do not claim that the hosted site has every feature illustrated by local-CI evidence. Share the hosted URL only with a visible “older demo deployment” limitation, since hosting is optional.
