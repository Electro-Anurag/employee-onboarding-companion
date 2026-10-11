#!/bin/sh
# Single production startup entrypoint, with no string-level shell re-parsing.
set -eu
echo "Applying forward-only PostgreSQL migrations..."
python manage.py migrate --noinput
# Evaluation-only path: the owner explicitly provides four distinct secrets
# via the private Render service environment and enables this one-time flag.
# The existing management command validates production mode, all credentials,
# isolation and no existing demo. Never make this an unauthenticated HTTP route.
if [ "${EOC_HOSTED_DEMO_BOOTSTRAP:-0}" = "1" ] && [ "${EOC_HOSTED_DEMO_CREDENTIAL_ROTATE:-0}" = "1" ]; then
  echo "STOP: synthetic creation and rotation flags must never be enabled together."
  exit 65
fi
if [ "${EOC_HOSTED_DEMO_BOOTSTRAP:-0}" = "1" ]; then
  echo "One-time synthetic hosted demo bootstrap explicitly enabled."
  python manage.py seed_hosted_synthetic --confirm-synthetic
fi
# Never updates passwords by default. Recovery requires separate explicit
# owner authorization on a named, existing four-user synthetic organization.
if [ "${EOC_HOSTED_DEMO_CREDENTIAL_ROTATE:-0}" = "1" ]; then
  echo "Owner-gated synthetic hosted credential recovery requested."
  python manage.py rotate_hosted_synthetic --confirm-synthetic-rotation
fi
echo "Starting Django/Gunicorn web server..."
exec gunicorn backend.config.wsgi:application \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --access-logfile - --error-logfile -
