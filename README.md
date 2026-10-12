> **Evaluation-first scope clarification (owner, 12 October 2026):** The final deliverable is a **working, production-oriented senior-evaluation project**, not a real-production HR deployment. A functional synthetic-data hosted demo, core four-role workflows, actual tests, honest AI demonstration, GitHub documentation and a recorded walkthrough remain required. Paid 24/7 infrastructure, HA, compliance certification, long-term disaster-recovery guarantees and real employee integrations are **not evaluation submission blockers**. See [evaluation delivery contract](docs/submission/evaluation-first-delivery-contract-20261012.md). Production GO and evaluation submission GO are separate; historical production-release tracker statements below are not the evaluation exit criteria.

# Employee Onboarding Companion

**Senior evaluator quick start:** [Walkthrough, evidence and limitations](docs/submission/EVALUATOR_START_HERE.md) · [local four-role screen capture](docs/submission/evaluator-walkthrough-20261012.md) · [optional local real-model adapter](docs/submission/local-ollama-evaluation-20261012.md).


**Status (12 October 2026): ongoing development and hosted partial evaluation, NOT production release GO.** The existing Free Render web service is LIVE at application SHA `ec781ab7362da10648eea496b1402b8c317dcd4c`; newer source and documentation commits are NOT deployed. Four-role authentication and synthetic partial HR/Employee workflows were demonstrated. Hosted J01–J05 remain 0/5 full PASS.

Repository: private personal GitHub repo `Electro-Anurag/employee-onboarding-companion`.
Development branch: `feature/eoc-completion-development`.
The owner's PRD v1.1 (28 requirements), Business Journey v1.0 (four roles,
ten exception journeys, mandatory hosted J01–J05), revised 8 October brief
and architecture handoff remain authoritative. All demonstration information
must be synthetic, anonymized or public. Never upload actual employee identity
documents to the demo.

## Capabilities implemented in source

- **M0–M2:** Django 5.2/PostgreSQL, React/TypeScript, role-scoped identity
  and session security, immutable published templates, case snapshots,
  dependency-based state, typed task evidence, command idempotency and
  append-only audit.
- **M3:** employee forms, policy acknowledgement, document version/review
  and correction handoffs. Separate secure S3 quarantine/scanning source
  exists but is **not enabled** on the proposed hosted demo.
- **M4:** persisted simulated IT provisioning, equipment receipt, manager
  activities, scheduled meetings and training completion evidence.
- **M5:** in-app reminders, exception episodes and recovery, approved
  joining-date changes, owner reassignment, HR handoffs and version-bound
  48-hour escalation. The latest escalation fixture corrections require
  exact-HEAD PostgreSQL and browser requalification.
- **M6 candidate:** deterministic current-state guidance is not model AI.
  An additional explicit, read-only, opt-in model-question path uses
  case-authorized sources, exact citation validation, provider output bounds,
  per-user attempt quotas and sanitized audit. An exact whole-edition policy
  retrieval path is now implemented for tightly bounded questions even with
  model inference disabled, clearly labelled **not AI**. **No real provider
  request has been qualified**; any non-policy question without approved
  API configuration receives clearly labelled deterministic guidance.
- **M7 closeout candidate:** HR closeout command checks all applicable
  mandatory task completions with typed evidence and refuses unclosed
  exceptions. It uses the governed transaction/audit/idempotency mechanism.
  **New tests and hosted behavior remain unqualified.**

These are source descriptions, not claims of deployed feature availability.

## Deployment and submission

The checked-in `render.yaml` is a **manual**, not automatically deployed,
Blueprint proposal for Django/React Docker web, PostgreSQL and a background
Procrastinate worker. HTTPS hostname, credentials and PostgreSQL are provided
by the platform after an authorized deployment. The worker needs a paid
instance; owner approval is required. The PostgreSQL `free` tier expires
after 30 days and the free web tier sleeps on inactivity. Neither is an
acceptable production reliability guarantee.

- [Deployment, synthetic account provisioning and J01–J05 acceptance runbook](docs/submission/hosting-and-acceptance.md)
- [Technical architecture and evidence boundaries](docs/submission/technical-design.md)
- [Prior independent M1 review](docs/qualification/m1-third-review-remediation-20261008.md)
- [Earlier M2 focused re-review packet](docs/qualification/m2-astra-remediation-20261009.md)

**Unverified current-SHA final deliverables:** fresh deployment of the
completion branch; live four-role sign-in on that SHA; real model inference;
successful hosted J01–J05; video of actual hosted interactions; release
and security qualification. The existing Free Render web is LIVE at `https://eoc-companion-web.onrender.com` on SHA `ec781ab7362da10648eea496b1402b8c317dcd4c` (last independently checked 12 October); this does **not** qualify newer branch source, the absent persistent worker or the five complete hosted journeys.
See [submission evidence and recording plan](docs/submission/evaluation-demo-evidence.md). Independent SOURCE GO is not production GO.

### Local-only synthetic development

Use PostgreSQL 17, Python 3.13, Node.js 22, uv and private test secrets.
Set `DJANGO_SECRET_KEY`, local `POSTGRES_*` and `DJANGO_DEBUG=1`.
The local seeds must never run in public DEBUG mode.

```sh
uv sync --frozen
(cd frontend && npm ci && npm test && npm run build)
uv run python manage.py migrate --noinput
uv run pytest -q
uv run python manage.py seed_m2_demo --confirm-synthetic
uv run python manage.py runserver --nostatic
```

The separate `seed_hosted_synthetic` command is not part of deployment
startup, requires production mode plus two explicit gates, uses four
separately configured private role passwords and prints no credentials.
See the hosting runbook for the exact, safe one-time procedure.

### Self-hosted CI

All existing GitHub Actions workflows are required to run on
`[self-hosted, linux, ARM64, eoc-mac-ci]` via the owner's Mac-hosted
Ubuntu ARM64 runner. Do not fall back to `ubuntu-latest` or assume that
an old passing SHA covers the current branch.

An **older** complete M5 Chromium run passed, an older M3–M4 Chromium
run passed, and an older M5–M6 PostgreSQL regression reported
**165 passed, 2 skipped, 2 setup errors** before the historical-date
fixture was corrected. The previous focused M5 escalation run reported
11 passed and 2 fixture errors before that same correction. These
are historical diagnostics; **fresh exact-HEAD acceptance remains open**.

## Architectural principle

Human owners alone may authorize workflow mutations. Models receive
only case-authorized synthetic context and have no permission to execute
approvals, issue IT access, upload files or change case state. Case
authorization, evidence requirements, audit and idempotency remain
server-side. No external identity or HR integration is implied.

## Submission quick reference

The [real walkthrough and evidence matrix](docs/submission/evaluation-demo-evidence.md)
separates source claims from hosted demonstrations and gives the owner a
six-minute YouTube recording plan. The [T01–T25 exact-SHA tracker](docs/tracking/release-test-gates-20261011.md)
remains authoritative for production/release qualification. Never label the
old LIVE Render SHA as the current completion branch.

### M5 control worker development update — 12 October 2026

The branch has an existing one-minute periodic reminder reconcile, plus a bounded five-minute abandoned-job retry restricted to two M5 task identities, a separate explicit-flag dedicated worker startup and a reviewed but **unapplied paid Starter-worker proposal** in `render.full.yaml`. Focused self-hosted [run 38178074575](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38178074575) **PASS**: 16 focused tests, actual killed worker after DB commit before ACK, successful stale-job retry with one active reminder, and actual minute-cron periodic scheduling. Details: [M5 background processing](docs/operations/background-processing.md).

The production Free web **does not have a continuously running control worker**. Do not claim J03 or uninterrupted reminders without an authorized worker deployment and real hosted evidence. The old worker branch listed in `render.full.yaml` has been corrected to the completion branch; applying that paid manifest remains a separate owner decision.

**M6 update (12 Oct):** [Full integrated CI 38180256254](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38180256254) PASS at `c2e0d8b323fcbb3b7f84ad78bad5a570c38dbd30`: 253 backend PASS / 2 live storage SKIP, 26 React PASS, Docker PASS, four-role Chromium PASS. Narrow model question-to-source relevance admission and malformed-provider response denial are qualified in offline synthetic CI. Hosted real AI inference remains DISABLED and J04 remains BLOCKED. See [M6 operations](docs/operations/ai-admission.md).
