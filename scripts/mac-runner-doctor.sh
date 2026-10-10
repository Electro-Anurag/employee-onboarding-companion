#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -s)" == Linux ]] || { echo 'STOP: runner needs Linux for Docker service containers'; exit 1; }
[[ "$(uname -m)" == aarch64 ]] || { echo 'STOP: expected ARM64 Linux guest'; exit 1; }
for name in git curl docker; do command -v "$name" >/dev/null || { echo "STOP: missing $name"; exit 1; }; done
docker info >/dev/null || { echo 'STOP: Docker is unavailable'; exit 1; }
docker info --format 'Docker engine: {{.ServerVersion}}; arch: {{.Architecture}}'
df -h .
echo 'PREFLIGHT ONLY: GitHub runner registration and application CI not yet qualified.'
