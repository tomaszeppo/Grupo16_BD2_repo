#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! docker compose ps --status running --services | grep -qx iris; then
  echo "ERROR: IRIS no está activo. Ejecutá bash scripts/01_inicializar.sh primero." >&2
  exit 1
fi
docker exec -i fixture2030-iris iris session IRIS <<'IRISCMDS'
Do ##class(Fixture.Demo).Run()
Halt
IRISCMDS
