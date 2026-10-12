#!/usr/bin/env bash
# Optional OWNER-RUN local real-model demonstration. No paid API calls.
# Never use this script with real HR/employee data or a hosted database.
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."

for tool in git uv curl python3; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "STOP: required local command not installed: $tool" >&2; exit 2;
  }
done
test -z "${DATABASE_URL:-}" || {
  echo "STOP: DATABASE_URL is set. Run only with a disposable local PostgreSQL container." >&2; exit 2;
}
test "${EOC_AI_PROVIDER:-OLLAMA_LOCAL}" = "OLLAMA_LOCAL" || {
  echo "STOP: real AI evidence uses only local Ollama, never a paid provider." >&2; exit 2;
}
export EOC_AI_PROVIDER=OLLAMA_LOCAL
: "${EOC_OLLAMA_MODEL:?Set EOC_OLLAMA_MODEL to an already installed local model (example: gpt-oss:20b)}"
[[ "$EOC_OLLAMA_MODEL" =~ ^[A-Za-z0-9_.:-]{3,80}$ ]] || {
  echo "STOP: invalid local model identifier" >&2; exit 2;
}
git diff --quiet && git diff --cached --quiet || {
  echo "STOP: uncommitted tracked changes would make the evidence SHA ambiguous." >&2; exit 2;
}
git rev-parse --verify HEAD >/dev/null
tags="$(curl --fail --silent --show-error --max-time 5 http://127.0.0.1:11434/api/tags)" || {
  echo "STOP: Ollama is not serving at 127.0.0.1:11434" >&2; exit 2;
}
printf '%s' "$tags" | python3 -c 'import json,os,sys; x=json.load(sys.stdin); m=os.environ["EOC_OLLAMA_MODEL"]; assert any(v.get("name")==m or v.get("model")==m for v in x.get("models",[])), "Selected Ollama model not already installed"' || {
  echo "STOP: local model not installed. This script never pulls models." >&2; exit 2;
}

evidence_dir="$(mktemp -d "${TMPDIR:-/tmp}/eoc-real-ai-evidence.XXXXXXXX")"
workspace="$(mktemp -d "${TMPDIR:-/tmp}/eoc-ai-pg.XXXXXXXX")"
image='postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3'
container_id=''
native_postgres_started=0
pgbin=''
cleanup() {
  if [ "$native_postgres_started" = 1 ]; then
    "$pgbin/pg_ctl" -D "$workspace/data" -m immediate -w stop >/dev/null 2>&1 || true
  fi
  if [ -n "$container_id" ]; then
    docker rm -f "$container_id" >/dev/null 2>&1 || true
  fi
  rm -rf "$workspace"
}
trap cleanup EXIT

# Prefer Docker if already running. Docker-free macOS: install Homebrew
# postgresql@17, then start a new, disposable, SCRAM-authenticated cluster.
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  engine=docker
  container_id="$(docker run --detach --rm \
    --env POSTGRES_DB=onboarding_m0 \
    --env POSTGRES_USER=onboarding \
    --env POSTGRES_PASSWORD=eoc-ephemeral-local-ai-only \
    --publish '127.0.0.1::5432' "$image")"
  host_port="$(docker port "$container_id" 5432/tcp | awk -F: 'END {print $NF}')"
else
  engine=homebrew-postgresql17
  command -v brew >/dev/null 2>&1 || {
    echo "STOP: Docker not available and Homebrew missing. Do not use shared databases." >&2; exit 2;
  }
  pgprefix="$(brew --prefix postgresql@17 2>/dev/null || true)"
  pgbin="$pgprefix/bin"
  for exe in initdb pg_ctl pg_isready createdb; do
    [ -x "$pgbin/$exe" ] || {
      echo "STOP: PostgreSQL 17 binary missing ($exe). Run: brew install postgresql@17" >&2; exit 2;
    }
  done
  # Homebrew pre-release macOS may stage versioned files in Cellar but fail
  # linking sharedir when the service's post-install setup fails. Never touch
  # Homebrew's global/default database or modify its symlinks. Point initdb
  # directly to a REAL postgres.bki from this formula's local keg (-L).
  pgcellar="$(brew --cellar postgresql@17 2>/dev/null || true)"
  pgshare_file=''
  for candidate in "$pgprefix/share/postgresql@17/postgres.bki" \
                   "$pgprefix/share/postgresql/postgres.bki"; do
    if [ -f "$candidate" ]; then pgshare_file="$candidate"; break; fi
  done
  if [ -z "$pgshare_file" ] && [ -d "$pgcellar" ]; then
    pgshare_file="$(find "$pgcellar" -type f -name postgres.bki -print -quit 2>/dev/null || true)"
  fi
  if [ -z "$pgshare_file" ] || [ ! -f "$pgshare_file" ]; then
    echo "STOP: Homebrew PostgreSQL 17 install incomplete: postgres.bki is absent." >&2
    echo "Inspect: find \"$(brew --cellar postgresql@17)\" -name postgres.bki -print" >&2
    echo "Do not copy or link PostgreSQL system directories into place." >&2
    exit 2
  fi
  pgshare="$(dirname "$pgshare_file")"
  echo "Using formula-local PostgreSQL shared files: $pgshare"
  # The server backend independently resolves timezone and extension files
  # from the executable's COMPILED bindir/sharedir relationship. initdb -L
  # changes only initdb's own inputs. A partially installed Homebrew keg
  # can therefore still fail despite a valid postgres.bki.
  #
  # Make an entirely PRIVATE relocatable layout inside our temporary test
  # directory. Copy executable bytes (not global links) to the compiled
  # bindir-relative location, and point its sibling share/lib dirs at the
  # already downloaded formula-local content. No /opt/homebrew mutation.
  [ -x "$pgbin/pg_config" ] && [ -x "$pgbin/postgres" ] || {
    echo "STOP: incomplete PostgreSQL keg: pg_config or postgres missing." >&2
    exit 2
  }
  compiled_bind="$("$pgbin/pg_config" --bindir)"
  compiled_share="$("$pgbin/pg_config" --sharedir)"
  compiled_pkglib="$("$pgbin/pg_config" --pkglibdir)"
  compiled_root="$(python3 - "$compiled_bind" "$compiled_share" "$compiled_pkglib" <<'PY'
import os, sys
p = sys.argv[1:]
if any(not os.path.isabs(x) for x in p):
    raise SystemExit("postgres paths must be absolute")
root = os.path.commonpath(p)
if root == "/" or not root.startswith("/opt/homebrew"):
    raise SystemExit("STOP: unexpected compiled PostgreSQL prefix")
print(root)
PY
)"
  stage_root="$workspace/staged-install"
  stage_bin="$stage_root/${compiled_bind#"$compiled_root"/}"
  stage_share="$stage_root/${compiled_share#"$compiled_root"/}"
  stage_pkglib="$stage_root/${compiled_pkglib#"$compiled_root"/}"
  if [ "$stage_bin" = "$stage_share" ] || [ "$stage_pkglib" = "$stage_share" ]; then
    echo "STOP: unsafe PostgreSQL relocation layout." >&2; exit 2
  fi
  mkdir -p "$stage_bin" "$(dirname "$stage_share")" "$(dirname "$stage_pkglib")"
  for exe in postgres initdb pg_ctl pg_isready createdb; do
    cp "$pgbin/$exe" "$stage_bin/$exe"
    chmod u+x "$stage_bin/$exe"
  done
  ln -s "$pgshare" "$stage_share"
  pkg_source=''
  for candidate in "$pgprefix/lib/postgresql@17" "$pgprefix/lib/postgresql" \
                   "$pgprefix/lib"; do
    if [ -d "$candidate" ] && [ -f "$candidate/plpgsql.so" ]; then
      pkg_source="$candidate"; break
    fi
  done
  if [ -z "$pkg_source" ]; then
    plpgsql_file="$(find "$pgcellar" -type f -name plpgsql.so -print -quit 2>/dev/null || true)"
    [ -z "$plpgsql_file" ] || pkg_source="$(dirname "$plpgsql_file")"
  fi
  if [ -n "$pkg_source" ] && [ ! -e "$stage_pkglib" ]; then
    ln -s "$pkg_source" "$stage_pkglib"
  fi
  pgbin="$stage_bin"
  echo "Using isolated relocatable PostgreSQL executable layout (no Homebrew service)."
  # Bind only to local 127.0.0.1 on a currently unoccupied ephemeral port.
  host_port="$(python3 - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
  printf '%s\n' 'eoc-ephemeral-local-ai-only' > "$workspace/db-password"
  chmod 600 "$workspace/db-password"
  "$pgbin/initdb" -L "$pgshare" -D "$workspace/data" --username=onboarding \
    --auth-host=scram-sha-256 --auth-local=scram-sha-256 \
    --pwfile="$workspace/db-password" --no-instructions \
    > "$workspace/initdb.log" 2>&1 || {
      echo "STOP: isolated initdb failed; no existing database was used." >&2
      tail -n 12 "$workspace/initdb.log" >&2 || true
      exit 2;
    }
  "$pgbin/pg_ctl" -D "$workspace/data" -w -t 30 \
    -o "-h 127.0.0.1 -p $host_port -k /tmp" \
    -l "$workspace/postgres.log" start >/dev/null 2>&1 || {
      echo "STOP: temporary loopback PostgreSQL did not start." >&2; exit 2;
    }
  native_postgres_started=1
  PGPASSWORD=eoc-ephemeral-local-ai-only "$pgbin/createdb" \
    -h 127.0.0.1 -p "$host_port" -U onboarding onboarding_m0
fi
[[ "$host_port" =~ ^[0-9]+$ ]] || {
  echo "STOP: unable to locate isolated loopback PostgreSQL port." >&2; exit 2;
}
export POSTGRES_HOST=127.0.0.1
export POSTGRES_PORT="$host_port"
export POSTGRES_DB=onboarding_m0
export POSTGRES_USER=onboarding
export POSTGRES_PASSWORD=eoc-ephemeral-local-ai-only
export DJANGO_SECRET_KEY=eoc-only-temporary-local-test-secret
export DJANGO_DEBUG=1
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver
export EOC_RUN_REAL_OLLAMA_TEST=1
unset OPENAI_API_KEY

ready=0
for _ in $(seq 1 50); do
  if [ "$engine" = docker ]; then
    ready_command=(docker exec "$container_id" pg_isready --quiet --username onboarding --dbname onboarding_m0)
  else
    ready_command=("$pgbin/pg_isready" -q -h 127.0.0.1 -p "$host_port" -U onboarding -d onboarding_m0)
  fi
  if "${ready_command[@]}"; then
    ready=1; break
  fi
  sleep 1
done
[ "$ready" = 1 ] || { echo "STOP: local PostgreSQL failed readiness" >&2; exit 2; }

{
  echo "EOC REAL-LOCAL-AI EVIDENCE (SYNTHETIC ONLY)"
  echo "source_sha=$(git rev-parse HEAD)"
  echo "test=backend/ai/tests/test_ollama_live_synthetic.py"
  echo "model=$EOC_OLLAMA_MODEL"
  echo "timestamp_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "context=disposable_local_postgresql_and_loopback_ollama"
  echo "postgres_runtime=$engine"
  echo "provider=OLLAMA_LOCAL"
  echo "hosted_qualification=no"
} > "$evidence_dir/provenance.txt"
echo "Private evidence directory: $evidence_dir"
echo "Running real Ollama through Django authorization and validator; only synthetic inputs."
uv sync --locked
uv run python manage.py check
set +e
uv run pytest -q -s backend/ai/tests/test_ollama_live_synthetic.py \
  2>&1 | tee "$evidence_dir/admission-test.log"
test_status=${PIPESTATUS[0]}
set -e
if [ "$test_status" -ne 0 ]; then
  printf 'admission=FAIL\n' >> "$evidence_dir/provenance.txt"
  echo "REAL AI ADMISSION FAILED. Do not claim a validated model demonstration."
  echo "Evidence retained privately: $evidence_dir"
  exit "$test_status"
fi
printf 'admission=PASS\n' >> "$evidence_dir/provenance.txt"
echo "REAL AI ADMISSION PASS: scope is the three synthetic questions only."
echo "Evidence retained privately: $evidence_dir"
echo "Inspect real model modes in admission-test.log; no raw answer text was stored by the test."
