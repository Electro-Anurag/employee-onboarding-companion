#!/bin/sh
# Dedicated control queue only. DO NOT use as Render free web command.
set -eu
if [ "${EOC_RUN_CONTROL_WORKER:-0}" != "1" ]; then
  echo "STOP: dedicated control worker needs EOC_RUN_CONTROL_WORKER=1" >&2
  exit 64
fi
if [ "${DJANGO_DEBUG:-}" != "0" ]; then
  echo "STOP: dedicated control worker requires DJANGO_DEBUG=0" >&2
  exit 65
fi
if [ -z "${DATABASE_URL:-}" ]; then
  echo "STOP: private PostgreSQL DATABASE_URL missing" >&2
  exit 66
fi
if [ "${EOC_HOSTED_DEMO_BOOTSTRAP:-0}" = "1" ] ||
   [ "${EOC_HOSTED_DEMO_CREDENTIAL_ROTATE:-0}" = "1" ] ||
   [ "${EOC_HOSTED_DEMO_CREDENTIAL_DIAGNOSE:-0}" = "1" ]; then
  echo "STOP: one-time demo bootstrap, rotation or diagnostic flag is forbidden" >&2
  exit 67
fi
python manage.py check
python manage.py procrastinate healthchecks
echo "EOC_CONTROL_WORKER_PREFLIGHT_PASS"
exec python manage.py procrastinate worker --queues control
