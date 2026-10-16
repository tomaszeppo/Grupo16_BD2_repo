"""Genera openapi/openapi.yaml a partir de la aplicación (fuente de verdad: el código)."""
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from app.main import create_app  # noqa: E402

destino = RAIZ / "openapi" / "openapi.yaml"
destino.parent.mkdir(exist_ok=True)
destino.write_text(yaml.safe_dump(create_app().openapi(), sort_keys=False, allow_unicode=True), encoding="utf-8")
print(f"escrito {destino}")
