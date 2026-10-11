# Hosted public smoke and role acceptance — 11 October 2026

**Deployment:** https://eoc-companion-web.onrender.com
**Exact app SHA deployed:** `ded82f9ca85213eb7bbc50ceb3eb81f4864b92f2`
**CI:** [38155019496](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38155019496) PASS: 224 backend, 26 frontend, production Docker, four-role synthetic Chromium. Two live storage/scanner tests skipped.
**Render deployment:** `dep-db5rr48473hc73c6mvlg` LIVE on above SHA.
**Runner:** self-hosted ARM64 `eoc-mac-ci-01`; no paid GitHub-hosted runner.

## What the no-secret smoke checks
`scripts/hosted_public_smoke.py` is a read-only HTTP suite for the **deployed SHA**; adding the script/workflow to the branch does **not** deploy additional application code. It requires HTTPS, live/ready health, real root plus static React assets, issued CSRF token, 401/UNAUTHENTICATED for anonymous identity, and denial/non-cacheability of unauthenticated case and notification API. It checks no authentication credentials, mutations, user data or paid external calls. A pass **does not** establish any J01–J05 acceptance.

## Hosted qualification ledger (do not infer success from CI)

| Journey | Requirement | Evidence / state |
| --- | --- | --- |
| J01 | HR create/activate → employee → HR document verification → IT → meeting/training → HR closeout | **BLOCKED**: hosted demo role accounts not yet evidenced, full hosted flow not executed. |
| J02 | Rejected/replaced secure document + approval/unblock | **BLOCKED**: live S3/ClamAV disabled; 2 integration live-storage tests skipped. |
| J03 | Real notification/reminder/escalation and recovery | **BLOCKED**: persistent worker not provisioned; don't claim background execution. |
| J04 | Verified provider inference, cited policy and unsupported abstention | **BLOCKED**: EOC_AI_PROVIDER=DISABLED and external API expense not approved; deterministic responses are not real AI. |
| J05 | Denied cross-employee access, command idempotency, rollback and durable audit | **BLOCKED/PARTIAL**: anonymous read smoke separate; no authenticated cross-employee, retries, rollback or durable audit hosted evidence. |

No hosted J01–J05 PASS is currently evidenced. **Release STOP** until each actual hosted journey and its infrastructure are independently verified.

## Private synthetic provisioning (owner-gated)

The current `backend/start_web.sh` only runs the existing `seed_hosted_synthetic` command when `EOC_HOSTED_DEMO_BOOTSTRAP=1`. Owner must securely set **four unique strong secrets** `EOC_DEMO_HR_PASSWORD`, `EOC_DEMO_EMPLOYEE_PASSWORD`, `EOC_DEMO_IT_PASSWORD`, `EOC_DEMO_MANAGER_PASSWORD` in the private Render service Environment. Store them privately, never in GitHub Actions logs, chat, source or documentation. Only then enable one-time flag, redeploy exact SHA; verify 4-account bootstrap log. Immediately disable flag before next restart and remove secrets from deployment environment after owner has securely recorded them. No manual database IP allowlist opening or authentication bypass. Without confirming that secure prerequisite, do **not** enable the flag: startup fails closed and can make the public service unavailable.

After provisioning, hosted role scenarios still need a secure runner-side credential source or browser operator; there is currently no tool that allows interactive authentication into the hosted React UI using secrets stored solely in Render. No action that relies on credentials can be marked executed without evidence.

## Verified hosted public run (immutable result, no role-pass inference)

- [GitHub Actions 38157805707](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38157805707) **PASS**, 2026-10-11T17:00:29Z, source-only smoke script commit `baa8403dfdd0502956a07ed907d558ab160aeaea`, HTTP target deployed application SHA `ded82f9ca85213eb7bbc50ceb3eb81f4864b92f2`.
- Actual hosted responses: `/health/live` 200, `/health/ready` 200, root 200, both immutable-production React CSS/JS assets 200, `/api/v1/auth/csrf` 200 and no-store, `/api/v1/auth/me` 401 UNAUTHENTICATED and no-store, `/api/v1/cases` 401 and no-store, `/api/v1/notifications` 403 and no-store. No credentials supplied; no unauthorized data disclosed in inspected responses. 
- J01 **BLOCKED**, J02 **BLOCKED**, J03 **BLOCKED**, J04 **BLOCKED**, J05 **BLOCKED/PARTIAL**. None passed. This adds **hosted public smoke qualification only**, not AI, storage, background work, full workflow or owner-grade security GO.
- Last inspected Render logs did not include any `Created four synthetic-only demo identities` message. Actual account existence could not be established directly because Render's private PostgreSQL database has external IP access disabled. Do not remove or modify this allowlist.
