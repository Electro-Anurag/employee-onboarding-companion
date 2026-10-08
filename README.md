# Employee Onboarding Companion

**Current status:** M0 local/CI foundation qualification only. This is **not** a working onboarding product.

Private, independent project. Governing documents: Product Requirements v1.1, Business Journey v1.0, Architecture Handoff v1.0.

## M0 objective

Prove a Django 5.2 + PostgreSQL 17 + Procrastinate 3.10 foundation with **atomic business + audit + durable-job insertion** and idempotent job replay. The frontend currently displays a truthful foundation status page.

## Prerequisites

Python 3.13, Node.js 22, PostgreSQL 17, uv, npm and (for local Compose) Docker. **The `uv.lock` and `frontend/package-lock.json` must be generated against live registries and committed before Docker/reproducible installation is qualified.** Their absence indicates incomplete M0, not success.

For a local qualification with a reachable Postgres database:

```sh
uv lock
uv sync --locked
cd frontend && npm install --package-lock-only && npm ci && npm run build && cd ..
export DJANGO_SECRET_KEY='replace-with-local-random-secret'
export POSTGRES_HOST='127.0.0.1' POSTGRES_PORT=5432
export POSTGRES_DB='onboarding_m0' POSTGRES_USER='onboarding'
export POSTGRES_PASSWORD='set-locally-not-in-repository'
uv run python manage.py migrate
uv run python manage.py procrastinate healthchecks
uv run pytest -q
uv run python manage.py runserver
```

Worker (separate shell): `uv run python manage.py procrastinate worker`.

Use `docker compose` after lockfiles exist, providing `.env` values; run `python manage.py migrate` before starting workers. Docker Compose cannot be tested in this execution environment and is **not** claimed as verified.

No demo credentials, secrets, private employee information, cloud keys, or integration accounts belong in this repo.

## Scope and qualification

See `docs/decisions/0001-m0.md` and the CI workflow. Run real PostgreSQL integration/recovery checks before claiming M0 complete.

CI additionally runs `scripts/m0_worker_recovery.py`: it intentionally terminates a real background worker after domain commit but before job acknowledgment; the test must recover/retry the stalled job without duplicate business effects. No public deployment or paid provisioning is authorized. The five final hosted product journeys belong to later milestones.
