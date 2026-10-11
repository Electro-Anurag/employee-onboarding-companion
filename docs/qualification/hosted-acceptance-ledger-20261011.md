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

## Credential-private four-role hosted access qualification

A read-only authenticated probe `scripts/hosted_role_verify.py` is available
for the owner to execute **locally in a private, interactive Ubuntu shell**
against Render. It prompts for each existing demo password with hidden input
(no GitHub Actions secrets or logs). It exercises live HTTPS CSRF and
login/session handling, exact role identity, same organization, assigned case
listing, HR-only template and portfolio boundaries, in-app inbox and logout.
No business task or database document is mutated. It only reports role,
status codes and PASS/FAIL, not passwords, cookies, organization IDs or record
contents. The output must not be called J01–J05 PASS.

**Observed bootstrap attempt:** An explicitly gated one-time startup on Render
deploy `dep-db5s49t9fdbs73du3na0` at app source `3749df543…` returned
`CommandError: Hosted synthetic demo already exists; refusing to overwrite`.
The attempted deployment **failed closed** and earlier app deployment
`dep-db5rr48473hc73c6mvlg` at `ded82f9c…` remained live. The error only
proves that at least one existing-org / existing-account predicate matched,
not that all four accounts exist or that newly configured passwords match.
No duplicate-account seed, password reset or destructive DB mutation is
authorized. A request to set `EOC_HOSTED_DEMO_BOOTSTRAP=0` was blocked by
tool safety checks; the owner must disable the flag manually in the Render
Dashboard and apply the environment before further redeployments.

After the service is healthy and the flag is disabled, the owner may run:

```bash
gh api 'repos/Electro-Anurag/employee-onboarding-companion/contents/scripts/hosted_role_verify.py?ref=feature/eoc-completion-development' \
  --jq '.content' | base64 -d > /tmp/eoc-hosted-role-verify.py
chmod 600 /tmp/eoc-hosted-role-verify.py
python3 /tmp/eoc-hosted-role-verify.py
rm -f /tmp/eoc-hosted-role-verify.py
```

This is a read-only `gh api` GET for the script; never supply private
password values as command arguments, flags, shell history or CI environment.

If any role fails, inspect only the role/status code, confirm the private
existing-account credential and role presence; do not automatically retry
or re-seed. J01–J05 remain **0/5 PASS** without the actual workflows, secure
storage, persistent worker and explicitly approved model provider.

## Existing synthetic account login: HTTP 401 — qualified recovery candidate

- The interactive authenticated check returned `HOSTED_FOUR_ROLE_READ_ONLY_FAIL=HR: live sign-in HTTP 401`. The real endpoint returned `LOGIN_UNAVAILABLE` (not proof of absence) and intentionally did not retry.
- The original `seed_hosted_synthetic` is **create-only**. Four new environment-secret passwords do not modify preexisting password hashes. Its previous fail-closed result means only that an existing account or demo organization matched. No successful new bootstrap is evidenced.
- `rotate_hosted_synthetic` is a separate, owner-gated recovery command. **Do not activate it without explicit owner approval**. It requires `DEBUG=0`, `EOC_HOSTED_DEMO_CREDENTIAL_ROTATE=1`, `--confirm-synthetic-rotation` and the create-only bootstrap flag disabled. It locks the unique exact-name synthetic organization and precisely four allowlisted `@hosted-onboarding-demo.invalid` accounts and membership records. Missing, disabled, staff, additional, cross-org or incorrectly privileged identities fail closed before changes. Four distinct Django-policy-validated passwords must be provided only in private Render environment variables. It rotates existing password hashes in one PostgreSQL transaction, revokes pending reset/invitation tokens and appends a sanitized immutable audit event; it never creates an identity, changes membership, emits secrets or executes on ordinary web startup. Already-matching credentials cause a no-op.
- The private PostgreSQL external IP allowlist must stay empty. Any credential-rotation deployment must first pass the exact new integrated CI, be authorized by the owner, then have its one-time flag disabled as soon as verified. Until then **hosted login FAIL, J01-J05 0/5 PASS, release STOP**.

## Owner-approved existing synthetic credential recovery — completed

- Owner explicitly approved rotating the **four existing synthetic HR/Employee/IT/Manager passwords** to their already stored private Render environment secret values.
- Exact code review/integrated qualification: [GitHub Actions 38161181552](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38161181552) **PASS** at application SHA `9877c015e0d7c83417f51471d95ccb3a80d45818`: **228 backend passed / 2 live-storage tests skipped**, **26 frontend passed**, exact-SHA production Docker built, full four-role local Chromium passed.
- One-time Render rotation deployment `dep-db5t3snlot8c7383nhl0` entered `Owner-gated synthetic hosted credential recovery requested.` after successful forward-only migrations. Render app log at **2026-10-11T18:15:28Z** confirmed **`Synthetic hosted credential recovery completed for 4 existing demo role(s). No usernames, secrets or hashes disclosed.`** The command returns success only after a single atomic PostgreSQL transaction that updates the allowlisted existing password hashes, revokes outstanding reset/invite tokens and appends sanitized immutable audit evidence. Do not claim independently queried audit evidence: database remains private.
- Immediately set `EOC_HOSTED_DEMO_CREDENTIAL_ROTATE=0` using the connected Render environment update, which automatically triggered disabled-normal startup deployment `dep-db5t4nd9fdbs73e1dbig`. **LIVE** at exact application SHA `9877c015e0d7c83417f51471d95ccb3a80d45818` with no migrations pending, Gunicorn started and readiness HTTP 200 confirmed. Neither paid worker nor real S3/ClamAV nor external AI provider was enabled.
- The rotation is a **credential recovery PASS**, not proof that four role HTTP sign-ins pass: no private demo passwords were read by tools or printed. Await a new `scripts/hosted_role_verify.py` check from owner's trusted interactive terminal. Avoid recording the passwords in shell history, chat, logs or videos. J01–J05 remain **0/5 PASS** until actual hosted business journeys are executed and verified.

## 11 October hosted four-role authentication verified (owner-run private shell)

- Owner executed `scripts/hosted_role_verify.py` in a private Ubuntu ARM64 terminal and supplied credentials through hidden prompts, never as chat text or CI configuration. Timestamp: **2026-10-11T18:23:03.456150+00:00**.
- `HOSTED_FOUR_ROLE_READ_ONLY_PASS` was reported after **four real hosted sign-in/sign-out sessions**. HR: login 200, cases 200, templates 200, portfolio 200, inbox 200, logout 200. EMPLOYEE, IT, MANAGER each: login 200, cases 200, templates 403, portfolio 404, inbox 200, logout 200. The script separately verifies current identity role, all four in the same synthetic organization, logout rendering `/auth/me` 401, private no-store API headers, and CSRF issuance. No secret values were shared.
- Render independently confirms the **LIVE** application `dep-db5t4nd9fdbs73e1dbig` runs code SHA `9877c015e0d7c83417f51471d95ccb3a80d45818`, free-tier web, auto-deploy OFF. The prior verifier printed `DEPLOYED_APP_SHA_EXPECTED=ded82f9…`: that is a **stale script constant**, not a remotely observed SHA, and must not override the direct Render deployment evidence.
- **New gate:** HOSTED_4_ROLE_AUTH = **PASS**. **J01–J05 remain 0/5 full PASS**. J01 authenticated participants now exist and are qualified for next read-only journey inventory and controlled synthetic business actions; J02 secure S3/scanner still disabled, J03 persistent worker missing, J04 real provider inference disabled, J05 cross-employee access/rollback/idempotency not yet hosted-qualified.

## 11 October J01 preflight HR login 401 (no business mutation)

- Owner's first `scripts/hosted_journey_preflight.py` attempt stopped at HR authentication with `HR: sign-in HTTP 401; no automatic retry`. None of the business-journey inventory was executed and J01–J05 remain **0/5 full PASS**. Previously authenticated four-role read-only verification at 18:23 UTC remains **PASS**.
- Render access logs later show login responses of **401** at 18:29:54, 18:33:19, 18:34:40 and 18:37:40 UTC from `EOC-private-role-gate/1.0`; the access logs do **not** identify which accounts were attempted. The backend returns HTTP 429 for a rate-limit denial, so the observed 401s are not *themselves* evidence of throttle exhaustion. Login credentials or actor admission were rejected, but there is not enough evidence to distinguish operator entry/copy differences from account-status changes.
- The previous `hosted_role_verify.py` and the new `hosted_journey_preflight.py` use equivalent CSRF, cookies, endpoint and email conventions; no code difference explaining a 401 was found.
- `hosted_journey_preflight.py` now asks for the same password **twice locally** and aborts before the login call if the entries disagree. It does not trim, echo, store or transmit the confirmation value; only one login is submitted after agreement. Avoid rerunning repeatedly: 5 attempts per account / 15m including successful logins. Safe conservative retry window: after **18:53 UTC on 11 Oct (00:23 IST on 12 Oct)**, assuming no additional attempts have occurred. Use the exact previously successful account password entered into the role verifier; do not repeat credential rotation or weaken rate limits to force a pass.

## 12 October hosted J01 preflight — CSRF transport timeout, service wake observed

- Owner's subsequent read-only J01 preflight stopped at `Transport failure on /api/v1/auth/csrf: TimeoutError`, **before the HR password prompt or any login POST**. No credential or onboarding business mutation was attempted; earlier verified role authentication still stands.
- At approximately **20:23:44 UTC on 11 Oct**, the free-tier Render web application independently started again, ran migrations (none pending), began Gunicorn at **20:24:05 UTC**, then supplied `/health/ready` HTTP **200** repeatedly. No matching `/api/v1/auth/csrf` request was logged in the queried 20:15–20:35 UTC window. This is consistent with a cold-start/wake-up timeout; exact upstream network origin is unproved.
- The change to `scripts/hosted_journey_preflight.py` performs a bounded **public GET** readiness warm-up before credentials are requested and retries only the two allowlisted paths (`/health/ready`, `/api/v1/auth/csrf`) after transport error or HTTP 502/503/504; maximum 3 requests with 4-second gaps. Authentication POST and all domain commands are never retried automatically. Offline unittest fixture covers wake success, refusal, exhaustion and safe path allowlist.
- Application deploy SHA remains `9877c015e0d7c83417f51471d95ccb3a80d45818`; this change is probe/tooling and documentation only. J01–J05 full hosted acceptance remains **0/5 PASS**. Avoid manual web-service restart and credential rotation; only retry preflight after the nonsecret offline tooling CI passes.

- **Verification result:** [GitHub Actions run 38172286839](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38172286839) **PASS** at source-tooling commit `afcba3db7caf322d2e2aa4198fdd01f8b3cd6cf0`: 5 offline bounded safe-GET retry tests passed, no live password login or domain mutation performed. This does not advance J01–J05 from 0/5 PASS. Owner should retry the updated private preflight when ready.

## 12 Oct: persistent hosted HR HTTP 401 after correct-looking terminal double entry

- Owner reports HR password entered correctly; `hosted_journey_preflight.py` warm-up completed, local two-prompt confirmation matched, but exactly one HR sign-in request returned HTTP **401**. This is **not** an HTTP 429 throttle denial, nor a CSRF transport failure. Render logs corroborate the latest 401. Do not shift blame to the operator or mark credential rotation as undone: four role sessions already passed at 18:21–18:23 UTC.
- The app is still **LIVE** on `9877c015e0d7c83417f51471d95ccb3a80d45818`. The subsequent cold-start did not migrate or rotate accounts (rotation was disabled). Previous sign-in test and preflight use the same hosted route and common HTTP helper. The detailed cause of the 401 is **unresolved**.
- A **read-only server-side diagnostic candidate** `diagnose_hosted_synthetic` has been added with a separate explicit flag and positive command confirmation. For exactly four synthetic `.invalid` identities it checks private Render environment values against existing stored hashes, Django's configured auth backend, current user/member role, without session, login attempt, login-throttle increment, credential mutation, audit write, or secret/hash output. No diagnostic is enabled by default and no deployment is authorized merely by committing it.
- Before enabling in Render, require exact-SHA integrated CI PASS and owner authorization for a one-time read-only deployment. If confirmed, set `EOC_HOSTED_DEMO_CREDENTIAL_DIAGNOSE=1` only for a single deployment, inspect the role-coded status lines, set back to `0` immediately, and verify normal deployment. No paid infrastructure, external AI, database-IP allowlist modification, or account rotation.
- **Release state unchanged:** hosted four-role historical auth PASS, subsequent HR read-only inventory login FAIL, J01–J05 **0/5 full PASS**.
