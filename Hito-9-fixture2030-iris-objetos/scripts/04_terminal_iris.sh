#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker exec -it fixture2030-iris iris session IRIS
