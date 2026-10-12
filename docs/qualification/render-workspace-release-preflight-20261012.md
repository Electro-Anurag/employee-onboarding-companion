# Render My Workspace — EOC release preflight and immutable delivery plan

**Inspected:** 12 October 2026, read-only through the connected Render workspace selected by the owner. **Status: RELEASE STOP / NO MUTATIONS AUTHORIZED BY THIS PLAN.**

This document **supersedes only the outdated current-live-SHA claim** in the historical hosted ledger. It does not rewrite prior immutable evidence, authorize billing or claim hosted acceptance.

## Verified connected resources

| Resource | Verified state |
| --- | --- |
| Workspace | `My Workspace` — `tea-db53b1ad0e5s73e27f1g` |
| Web | `eoc-companion-web` — `srv-db557b8473hc739u5l70`, [dashboard](https://dashboard.render.com/web/srv-db557b8473hc739u5l70), [public URL](https://eoc-companion-web.onrender.com), Docker, **free**, Singapore, 1 instance, auto deploy **OFF**, health `/health/ready`, manual build command `/bin/sh /app/backend/start_web.sh` |
| Live deployed revision | **`ec781ab7362da10648eea496b1402b8c317dcd4c`** via Render deploy `dep-db5v8nv79l7c73fus09g`, status **LIVE**, finished **2026-10-11 20:42 UTC**. This is **not** the completed D5/D6 development revision. |
| Database | `eoc-companion-postgres` — `dpg-db556v8473hc739u4esg-a`, [dashboard](https://dashboard.render.com/d/dpg-db556v8473hc739u4esg-a), **PostgreSQL 18**, free, Singapore, status available, no read replicas/HA, no connection pool, **expiration 2026-11-09 15:02:21 UTC** |
| Private DB access | IP allowlist **empty**. Read-only connector SQL failed as expected; **do not open the allowlist** just for inspection. Query live migration state through an approved in-service diagnostic, non-public authorized command or private network flow. No table contents were retrieved. |
| Dedicated background worker | **None currently provisioned** — only one web service in the selected workspace |
| Object storage / scanner | No Render worker/ClamAV/S3 integration qualified in the deployed environment. Repo `render.yaml` has `M3_REAL_DOCUMENT_ENABLED=0` and `M3_QUARANTINE_INTAKE_ENABLED=0`; cannot infer actual runtime flags independently from service metadata. |
| AI inference | Repo `render.yaml` sets `EOC_AI_PROVIDER=DISABLED`; no live provider-enabled J04 evidence. Actual environment values were **not** retrieved. |
| Deployment control | Auto-deploy is OFF, allowing deliberate owner-approved pinned release; a manual trigger would run forward-only migrations at startup. |
| Self-hosted CI | Owner runner `eoc-mac-ci-01`; no GitHub-hosted CI required by plan. |

**Latest development branch inspected at planning time:** `5dafa4d29ae56b53396993d834ea312dc024f88e`, documentation tail after last D6 code/test fix `b2765403e2c7f477c137351163364d8c389a1d37`. All qualification claims must be tied to their **own immutable tested SHA**; do not assume current hosted SHA equals any of those.

## Verified local/source evidence versus hosted release

- Latest D6 real MinIO/ClamAV [8/8 PASS (38219586182)](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38219586182) on `829f9e69...`.
- Quiesced same-engine PostgreSQL+MinIO snapshot recovery [PASS (38221427909)](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38221427909) on `b2765403...`.
- Full PostgreSQL/React/Docker/four-role CI [PASS (38218007460)](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38218007460) on `b6a4ac93...` (different SHA, separate real storage CI).
- D5 keyboard and targeted WCAG A/AA [PASS (38212201996)](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38212201996) on `93868cf6...`.
- Independent T17 source security review **OPEN**, final T18 exact SHA qualification **OPEN**, hosted functional J01–J05 **0/5**.

**DO NOT** mistake old live SHA `ded82f9...` in `docs/qualification/hosted-acceptance-ledger-20261011.md` for the present live state; that was an earlier historical snapshot. New observed live commit is `ec781ab7...`.

## Required sequence — no silent upgrade or destructive mutation

### Gate A: owner-approved architecture, cost, privacy and secure secrets

1. Obtain independent **T17 SOURCE REVIEW GO** or close each BLOCKER/HIGH with exact-source requalification.
2. Confirm the target is this workspace, and record an explicit **monthly cost ceiling and allowed Render plans** for persistent PostgreSQL with backup/retention; an always-on control worker; durable private versioned S3 plus actual fresh ClamAV; and a capped external model provider. **Do not infer a purchase authorization from workspace confirmation.**
3. Document legal/privacy safeguards; **synthetic-only hosted evaluation**, no identity card uploads from real people. Approve secret delivery only in the Render/private provider UI or secure authorized connector flow. Do not store secrets in source/chat/logs.
4. Decide whether to preserve/migrate the existing free database. It expires **2026-11-09** and has no evidenced backups. A production data-loss-risk migration/upgrade MUST NOT be attempted until the owner approves the preservation strategy and an independently verified backup/recovery path exists.

### Gate B: source and migration admission

1. Freeze a named immutable final candidate commit **after T17 fixes**; use only the authorized private GitHub identity.
2. Execute entire T18 suite at that immutable SHA on self-hosted ARM64: PostgreSQL/React/Docker/four-role Chromium, M3 live S3/ClamAV, D6 exact versions and coordinated offline recovery, worker crash/wake, AI negative/positive semantic contract, tenant/CSRF and axe scope.
3. **Render PostgreSQL is v18 whereas much local CI used v17.** Prove migrations (including historically populated DB constraints) on PostgreSQL 18 or an approved restored snapshot **before** running `start_web.sh`, which automatically calls `python manage.py migrate --noinput`. Check forward-only behavior and that previous release can be served without rollback of migrated schema; never rewrite historical migrations.
4. Confirm final candidate SHA and safe rollback window. Never manually trigger a deployment from an unreviewed, moving development HEAD.

### Gate C: staged owner-authorized deployment (not executed)

1. Select/approve durable DB, versioned storage, fresh scanner, always-on worker, AI provider and budget; provision through owner-authorized actions only. Preserve DB private network isolation.
2. Deploy the exact approved code SHA to an isolated **synthetic-only staging** environment. Validate runtime environment flags without printing values or secrets. Confirm maintenance/readiness health and migration state, and verify private object/version enforcement and real worker health.
3. Resolve existing synthetic HR login issues through private read-only diagnosis first; do **not** rerun `seed_hosted_synthetic` on an existing demo organization or reset passwords automatically. Any credential rotation requires a separately authorized action.
4. Run true hosted **J01–J05** at that deployed SHA; record user role, case synthetic fixture, browser trace/evidence, actual provider inference and worker traces; no real employee data. Each exact hosted pass gets linked to the SHA.
5. Produce final T25 architecture, instructions, tests, reproducible demo video and immutable tag. Declare submission GO only when T17–T25 requirements pass with no unresolved blockers.

## Current decision

**Deployment, billing/worker, DB-plan change, storage provisioning, credential rotation and provider inference remain NOT AUTHORIZED by this read-only workspace inspection.** Release STOP. Current authenticated hosted journeys remain unqualified. Do not claim “finished” merely because local CI passed.

## PostgreSQL 18 compatibility engineering action

- [Run `38232520864`](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38232520864) at `01eca42ff06be4b210c7d132f0b2efe330a1c6fa` is **PENDING**. The dedicated workflow tests current schema + full backend suite and four populated historical installations on isolated PostgreSQL 18 matching Render's major version. It neither verifies nor accesses private Render rows, backups or configuration. Do not use this as migration-approval for the existing free DB until true database preservation and exact-state review are separately established.
