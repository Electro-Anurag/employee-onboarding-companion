# Hosted submission and acceptance runbook — 10 Oct 2026

Status: **prepared, not deployed or hosted-qualified**. Applies to the exact
`feature/m5-m6-parallel-development` branch. This guide is for the synthetic
demo only; it is not a production security certification.

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

- Hosted URL: **NOT YET AVAILABLE**
- Exact deployed SHA: **NOT YET VERIFIED**
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
