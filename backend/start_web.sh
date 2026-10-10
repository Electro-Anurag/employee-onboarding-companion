#!/bin/sh
# Single production startup entrypoint, with no string-level shell re-parsing.
set -eu
echo "Applying forward-only PostgreSQL migrations..."
python manage.py migrate --noinput
echo "Starting Django/Gunicorn web server..."
exec gunicorn backend.config.wsgi:application \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --access-logfile - --error-logfile -
