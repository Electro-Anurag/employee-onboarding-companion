# Employee Onboarding Companion

**Project stage:** M1 identity, authorization and audit foundation qualified in local/CI (8 October 2026). **This is not yet a working end-to-end onboarding application.**

This is an independent private repository. Governing requirements: Product Requirements v1.1 (28 functional requirements), Business Journey v1.0 (four roles, ten exceptions, five hosted journeys), Architecture Handoff v1.0.

## Verified foundations

- M0: Django 5.2, PostgreSQL 17 and Procrastinate 3.10; atomic operation/audit/queued-job commit, rollback and real worker crash/recovery.
- M1: email-login and Argon2, session and CSRF enforcement, four-role membership checks, scoped employee/owner case reads, HR reassignment with optimistic version + idempotency key, immutable audit-event UPDATE/DELETE trigger and hash-chain append function, single-use invitation/reset tokens, and error/denial paths.
- CI: 23 PostgreSQL-backed tests including M0 regressions, two-session concurrent commands; restricted-role audit append/denial probe; React build, same-origin API smoke and Docker build.

See [M0 qualification](docs/qualification/m0-20261008.md) and [M1 qualification](docs/qualification/m1-20261008.md) for exact evidence and limits.

## Local development

Requires Python 3.13, Node.js 22, uv 0.12.23, PostgreSQL 17 and optional Docker. Use separate development-only credentials; never put secrets or real employee data into source or test fixtures.

```sh
uv lock --check && uv sync --locked
(cd frontend && npm ci && npm run build)
cp .env.example .env
# Set unique LOCAL credentials and database settings in .env or the shell.
# Confirm PostgreSQL 17 is running and the database exists.
uv run python manage.py migrate --noinput
uv run python manage.py procrastinate healthchecks
uv run pytest -q
uv run python manage.py runserver
```

The Django application serves the compiled frontend from the same origin. The UI includes a real session sign-in/out shell and scoped case previews; **no permanent demo account bootstrap or full employee onboarding workflow exists yet**. PostgreSQL test fixtures are synthetic and independent from a runnable public demo. The external AWS, AI and Render services are not connected.

Local database permissions require proper configuration; the CI audit role probe uses a disposable restricted role and **does not mean real application runtime credentials have been provisioned as least privileged**.

To run the M0 worker tests, use GitHub Actions M1 integration workflow. The resulting CI checks and Docker build are not a hosted-app qualification. Public publishing, paid services and M2 development require separate owner decisions.
