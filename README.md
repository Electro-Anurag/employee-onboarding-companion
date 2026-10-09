# Employee Onboarding Companion

**Project stage:** M0 qualified; M1 independently security-reviewed and approved; **M2 local/CI implementation qualified (9 October 2026), independent M2 review pending; real Chromium four-role browser acceptance passed in local/CI.** Not a complete end-to-end onboarding product.

Private personal GitHub repository. Governing scope: PRD v1.1 (28 functional requirements), Business Journey v1.0 (four roles, ten exception journeys, five hosted acceptance journeys), and Technical Architecture & Engineering Handoff v1.0. Neither M3–M10 implementation nor public deployment has been authorized.

## Milestones

- **M0:** Django 5.2, PostgreSQL 17, Procrastinate 3.10, transactional queue/DB effect/audit and hard-kill worker recovery — qualified.
- **M1:** Email identity, single active membership, four-role authorization, CSRF/session, invitations/reset, assignment controls, append-only auditable changes, idempotent transaction boundaries — independently reviewed GO.
- **M2:** Versioned synthetic templates and published immutable DAGs; HR case creation and activation; 17-task synthetic snapshot; AND prerequisite evaluation, blocked/ready/in-progress tasks, timezone-local schedules, typed manager-preparation attestation, HR Day 1 transition, role-scoped workspaces and case timeline — **84/84 Python tests, 2/2 frontend tests and CI build passed**. This is not all 17 tasks completeable yet.
- **Future work:** M3 evidence files/forms/policies; M4 IT/training integrations; M5 reminders and exception recovery; M6 AI; M7 dashboards/closeout; M8 hosting/operations; M9 hosted journeys/benchmarks; M10 final demonstration.

For exact source SHA, 11/12 passed gates, browser CI results, limitations and 12-item engineering checklist see [M2 qualification and tracker](docs/qualification/m2-20261009.md).

## Local synthetic demonstration

Requires Python 3.13, Node.js 22, uv 0.12.23, PostgreSQL 17 and optional Docker. Use local-only credentials and synthetic accounts. Set a non-placeholder `DJANGO_SECRET_KEY`, local `POSTGRES_*` settings and `DJANGO_DEBUG=1`. Never use this DEBUG-only bootstrap on a hosted system.

```sh
uv lock --check && uv sync --locked
(cd frontend && npm ci && npm run test && npm run build)
uv run python manage.py migrate --noinput
uv run pytest -q
uv run python manage.py seed_m2_demo --confirm-synthetic
uv run python manage.py runserver --nostatic
```

The bootstrap prints fresh credentials for HR, Employee, IT and Manager on the owner's terminal; store them privately. It fails if `DEBUG` is off, explicit confirmation is missing or demo identities already exist.

**Manual workflow:** Sign in as synthetic HR -> create default 17-task template -> publish -> create and activate case -> inspect authorized case tasks -> sign in as Manager -> complete Manager Preparation with typed evidence -> inspect changed task eligibility. The HR Day 1 action is date-gated. Document, IT/access and training completions are intentionally disabled until evidence-specific features exist.

## Qualification and security boundary

- M2 regression CI: https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37876285373\n- M2 Chromium browser CI: https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/37876285358
- Full source tested: `2cb002c1ae40731fa1530a2c02c28978c64ee672`; original main untouched.
- Real Chromium testing on a loopback Django/PostgreSQL server passed; it does **not** establish hosted browser acceptance, production least-privilege grants, operational resiliency, or independent M2 review.
- External AI services, cloud hosting, S3, email, and real employee data are not connected or used.
- M0 and M1 review evidence: [M0](docs/qualification/m0-20261008.md), [M1](docs/qualification/m1-20261008.md), [M1 independent remediation](docs/qualification/m1-third-review-remediation-20261008.md).

No paid service, external production account or public web deployment is required for current M2 local/CI use.
