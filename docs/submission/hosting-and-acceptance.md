# Hosted submission and acceptance runbook — 11 Oct 2026

Status: **older Render web build live, completion-branch release not deployed or
hosted-qualified**. Current development branch: `feature/eoc-completion-development`.
Last observed Render LIVE SHA: `b4312679cddf7598d542f396a45318cde9a3e590c`
(`https://eoc-companion-web.onrender.com`). This is an **older** build, not
permission to claim any current feature or hosted journey works. This guide is
synthetic-demo-only and is not a production security certification.

## Deployment boundary

The checked-in `render.yaml` proposes a Django/React Docker web service, a
private Render PostgreSQL database and a PostgreSQL-backed Procrastinate
`control` worker. The document upload/scanning path deliberately stays
disabled without separate S3, ClamAV, retention, access controls and a
qualified secure-hosting review. **Do not upload real employee or ID documents.**

The worker's `starter` instance incurs charges and requires owner approval
before applying the blueprint. Render's `free` web instance sleeps on
inactivity and its free PostgreSQL instance expires after 30 days. This is
a deadline-focused evaluation setup, not a reliable long-term production SLA.

Render account/repository access and any paid infrastructure must be explicitly
authorized. Deploy from the existing branch only; do not switch to `main`
or modify GitHub Actions to GitHub-hosted runners.

## Provisioning and release gates

1. Connect the owner's **private** GitHub repository to Render and review
   `render.yaml` in Blueprint preview. Verify branch and environment names.
   Confirm any paid worker cost *before* applying.
2. Set/verify HTTPS, `RENDER_EXTERNAL_HOSTNAME`, `DATABASE_URL` referencing
   the private database, generated `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`,
   both M3 intake flags = 0. Keep DB and API keys out of Git and CI logs.
3. Deploy immutable Docker image from an exact reviewed branch commit. The
   web startup applies **forward-only** migrations; it must not rewrite any
   previously applied migration. The control worker must show healthy
   background processing, not merely a healthy web server.
4. Capture the resulting **real** HTTPS URL, deployed SHA and timestamp. Verify
   `GET /health/live` and `GET /health/ready` both return 200. Verify the
   React root returns HTML/JS, then log in and exercise one real HTTP journey.
5. On the **paid worker's authenticated shell**, manually provision synthetic
   demonstration identities. The free web tier has no shell access. Configure
   distinct strong `EOC_DEMO_{HR,EMPLOYEE,IT,MANAGER}_PASSWORD` values as
   *private worker environment secrets* and set
   `EOC_HOSTED_DEMO_BOOTSTRAP=1`. Execute:

   ```sh
   python manage.py seed_hosted_synthetic --confirm-synthetic
   ```

   This one-time command requires production mode, explicit confirmation and
   the bootstrap flag, creates only fictional identities and prints no
   passwords. Immediately disable the bootstrap flag and remove the four
   bootstrap password environment secrets from the service after credentials
   have been securely recorded by the owner. The command deliberately rejects
   an existing demo, rather than resetting passwords or cases.
6. Sign in as synthetic HR, create/publish the existing 17-task first-month
   template in the UI, create the fictional employee case, assign IT/Manager,
   activate it and verify independent role views.
7. Configure a dedicated, explicitly approved model provider and private API
   credential before claiming **M6 model inference**. The currently qualified
   deterministic guidance does not count as a model-generated answer.

Do not enable `DJANGO_DEBUG=1` on a public service to run local seed commands.
Never paste account passwords or API keys into a publicly shared video.

## Hosted acceptance evidence (all initially NOT VERIFIED)

| ID | Required live journey and expected evidence |
| --- | --- |
| J01 | HR create/activate → employee requirements → HR document verification → IT fulfillment → manager scheduled/completed activity → training → **HR closeout**; complete state and audit |
| J02 | Rejected synthetic document → blocked dependent task → replacement → accepted HR review → unblocked dependent task, preserved revisions |
| J03 | Persisted IT request blocked → HR/employee see owner/blocker → periodic reminder/escalation → fulfill → dependent task eligible, no duplicates |
| J04 | Employee asks supported **policy** question → approved source citation and current next action; then unsupported question → explicit abstention, **real authorized model inference** |
| J05 | Cross-employee access 404/denied; repeat command idempotent; failed action rolls back safely, audit remains intact |

For each, record real HTTPS URL, deployed SHA, synthetic actor/role,
timestamp, browser steps, server response and immutable state evidence.
A previous CI/browser pass is not a hosted pass. If J01 cannot close because
M7 closeout is not built, report that as a **blocking missing feature**,
not an accepted or mock demonstration.

## Submission manifest — fill from actual evidence only

- Older hosted web URL: `https://eoc-companion-web.onrender.com` (**not a current release**) 
- Older Render LIVE SHA: `b4312679cddf7598d542f396a45318cde9a3e590c`
- Required current completion-branch deployed SHA: **NOT YET QUALIFIED**
- Git repository: private `Electro-Anurag/employee-onboarding-companion`
- J01–J05 hosted acceptance: **NOT YET RUN**
- Real M6 inference: **NOT YET QUALIFIED**
- Independent production review: **NOT YET COMPLETED**
- Demo video: **NOT YET RECORDED**
- Owner-approved public submission/repository access: **PENDING**

A real video must capture the hosted application and role transitions; do
not synthesize or label a simulated screen recording as a working product.
Provide reviewers access to the private repository or a reviewed submission
repository only with the owner's approval.

## CI constraints

All existing workflows remain pinned to self-hosted Ubuntu ARM64
`[self-hosted, linux, ARM64, eoc-mac-ci]`. Preserve this runner requirement.
Validate the focused escalation regression on PostgreSQL and rerun only
the necessary changed-HEAD integrated/browser gates when worker capacity allows.

**Operational limitation:** No controlled backup/restore, paid worker SLA,
secure hosted S3/ClamAV document path, model inference or all-five hosted
acceptance evidence has been established merely by this repository document.

## Evidence capture and submission readiness

Use [the evidence and video guide](evaluation-demo-evidence.md) to capture
real role journeys, measured business outcomes, honest AI contribution and
actual code/host SHA. Do not publish an unqualified release as a production
system. The latest test ledger is [T01–T25](../tracking/release-test-gates-20261011.md).

## Free-web one-time synthetic demo bootstrap (no worker shell)

The zero-paid-compute Render web plan provides no interactive service shell.
The startup script `backend/start_web.sh` now offers an **explicitly gated,
one-time** call to the already tested `seed_hosted_synthetic` command after
forward migrations and before Gunicorn. Without the flag, startup does not
create or mutate any demo identities. This is not an HTTP endpoint.

1. Set the service **branch** through the Render Dashboard to
   `feature/eoc-completion-development` under the service's Settings >
   Build & Deploy. Keep auto-deploy **OFF**. Its local Blueprint definition
   now matches the intended branch. No available connected Render action
   edits an existing service's branch; do not trigger an old-branch deploy.
2. Confirm the dashboard still shows plan `free`, private PostgreSQL
   database `eoc-companion-postgres`, generated secret, `DJANGO_DEBUG=0`,
   `EOC_AI_PROVIDER=DISABLED`, and both M3 real/quarantine intake flags
   disabled. Do **not** add external database IP allowlist entries.
3. In the **private Render web service environment**, configure **four
   distinct, strong** secrets named `EOC_DEMO_HR_PASSWORD`,
   `EOC_DEMO_EMPLOYEE_PASSWORD`, `EOC_DEMO_IT_PASSWORD` and
   `EOC_DEMO_MANAGER_PASSWORD`. Create and retain them privately; **never
   share their values in chat, source or a demo recording**. Set
   `EOC_HOSTED_DEMO_BOOTSTRAP=1` only for the **first** deploy where the
   synthetic organization is absent.
4. Trigger a deployment of the **exact CI-qualified completion-branch SHA**.
   The startup migrates, verifies all secrets via Django's password policy,
   and creates an isolated synthetic-only org plus the four users in a single
   transaction. If any account already exists or bootstrap fails, startup
   **fails closed** rather than resetting accounts. This path must never be
   enabled for real employee data.
5. Once the deployment is LIVE and synthetic sign-in works, promptly set
   `EOC_HOSTED_DEMO_BOOTSTRAP=0` and remove the four bootstrap password
   environment values from the **service** after recording them securely.
   Any automatic restart after this change must run with the flag disabled;
   otherwise the command correctly refuses to seed the same org twice.
   Persisted password hashes remain in private PostgreSQL.
6. The synthetic emails are fixed by source and can be shown without secrets:
   `hr@hosted-onboarding-demo.invalid`,
   `employee@hosted-onboarding-demo.invalid`,
   `it@hosted-onboarding-demo.invalid`,
   `manager@hosted-onboarding-demo.invalid`.
   Use the real UI to create and activate the versioned 17-step case.

**Explicit limitations:** The free web can sleep. There is no paid persistent
Procrastinate worker, live provider AI, secure live S3/ClamAV intake or
operational backup. The synthetic demo is not automatically J01–J05 GO.
Full production qualification must separately address these gates.
