#!/usr/bin/env bash
# Optional OWNER-RUN local real-model demonstration. No paid API calls.
# Never use this script with real HR/employee data or a hosted database.
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."

for tool in git docker uv curl python3; do
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
docker info >/dev/null 2>&1 || {
  echo "STOP: local Docker daemon unavailable. Do not use shared databases." >&2; exit 2;
}
tags="$(curl --fail --silent --show-error --max-time 5 http://127.0.0.1:11434/api/tags)" || {
  echo "STOP: Ollama is not serving at 127.0.0.1:11434" >&2; exit 2;
}
printf '%s' "$tags" | python3 -c 'import json,os,sys; x=json.load(sys.stdin); m=os.environ["EOC_OLLAMA_MODEL"]; assert any(v.get("name")==m or v.get("model")==m for v in x.get("models",[])), "Selected Ollama model not already installed"' || {
  echo "STOP: local model not installed. This script never pulls models." >&2; exit 2;
}

evidence_dir="$(mktemp -d "${TMPDIR:-/tmp}/eoc-real-ai-evidence.XXXXXXXX")"
image='postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3'
container_id=''
cleanup() {
  if [ -n "$container_id" ]; then docker rm -f "$container_id" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT
container_id="$(docker run --detach --rm \
  --env POSTGRES_DB=onboarding_m0 \
  --env POSTGRES_USER=onboarding \
  --env POSTGRES_PASSWORD=eoc-ephemeral-local-ai-only \
  --publish '127.0.0.1::5432' "$image")"
host_port="$(docker port "$container_id" 5432/tcp | awk -F: 'END {print $NF}')"
[[ "$host_port" =~ ^[0-9]+$ ]] || {
  echo "STOP: unable to locate the ephemeral loopback PostgreSQL port." >&2; exit 2;
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
  if docker exec "$container_id" pg_isready --quiet --username onboarding --dbname onboarding_m0; then
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
