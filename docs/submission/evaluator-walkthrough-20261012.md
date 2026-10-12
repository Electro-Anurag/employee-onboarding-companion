# Evaluator walkthrough and genuine recording guide

**Context:** senior's confidential evaluation project, synthetic demonstration only. **This is not a real employee-production deployment or an HR integration.** Track approved scope in [evaluation first delivery contract](evaluation-first-delivery-contract-20261012.md).

## In-app tour

Every signed-in HR, Employee, IT and Manager has an **Evaluation walkthrough** in the sidebar with role-specific steps. The steps navigate to existing business features only. They cannot approve, waive, complete, start or simulate a task without the original server-authorized controls.

| Role | What an evaluator should inspect |
|---|---|
| HR | Publish immutable template, create/activate fictional case, review submissions, owner progress, readiness |
| Manager | First-week attestation, introduction/meeting/training with typed evidence |
| Employee | Policy acknowledgement, submitted fictional form, version/review outcome and next eligible work |
| IT | Simulated external provisioning with actual internal audited command and owner-scoped evidence |

The free hosted demo **may not have** live private S3/ClamAV, continuous reminder worker or a configured model. Screen copy distinguishes limitations and requires actual model inference for any claim about generative AI.

## Reproducible unedited real-browser CI recording

Workflow `.github/workflows/eoc-evaluation-demo-capture.yml` uses the owner's self-hosted ARM64 runner, isolated PostgreSQL, real Django sessions/CSRF and compiled React. It seeds ephemeral synthetic actors privately and records real actions as **Playwright Chromium .webm video** plus screenshots and a JSON provenance manifest. **No credential file is included in the artifact; it contains only fictional app views.** GitHub artifact retention is 3 days.

The capture visits sign-in, HR published template/case activation, Manager actual typed evidence completion, Employee and IT case views and HR portfolio. It deliberately does **not** claim a completed J01, live PDF S3 scan, hosted background worker or model AI inference. The capture is **local/CI**, not the user's existing Render URL.

- CI must report `EOC_EVALUATION_LOCAL_FOUR_ROLE_VIDEO_AND_SCREENSHOTS_PASS@<sha>`.
- Download the named `eoc-evaluation-local-video-<run_id>` private GitHub artifact from that successful workflow's **Artifacts** section.
- View the video and eight numbered PNGs; only cite that exact source SHA and synthetic backend.
- The actual senior submission requires a **separate real recorded hosted walkthrough** at the deployed SHA; use the same steps and explicitly show disabled/simulated integrations.
- For a polished 5–6-minute narrated final recording, use [evaluation-demo-evidence.md](evaluation-demo-evidence.md) for the evidence and story arc. Do not insert fictional "AI result", performance statistics or video URL.

## Minimum candid reviewer disclosure

> Employee Onboarding Companion is an evaluation application using fictional people. Case state, typed evidence, authorization, human decisions and audit are implemented on a real database. External HR/IT integrations are simulated. Production operational guarantees are out of scope. Where a hosted free-tier dependency is disabled, we provide separate CI evidence rather than claim it works on the hosted deployment.

**State:** proposed CI recording, not qualified until the workflow passes. This document is not evidence that a video has already been uploaded.
