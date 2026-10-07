#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

bash scripts/inicializacion.sh
python3 scripts/carga_lotes.py --matches 8 --batch-size 2000 --workers 2
bash scripts/consultas_temporales.sh
bash scripts/agregaciones.sh
bash scripts/validacion.sh
python3 scripts/medir.py --matches 1 --batch-size 2000 --workers 1
bash scripts/capturar_evidencia.sh
