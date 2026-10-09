#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p "$HOME/docker/data/iris"
# No borrar el directorio durable al reiniciar: contiene la base IRIS.
docker compose up -d
docker compose ps
