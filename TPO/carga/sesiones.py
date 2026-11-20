"""Sesiones para el generador de carga.

Abrir una sesión por pedido mediría POST /sesiones y no el escenario. Antes de cada corrida se crea una
sesión por usuario (U0000001, U0000002, …) escribiendo por lotes directo en Redis, y los tokens se guardan en
un archivo local (no versionado) para reutilizarlos mientras sigan vivos.
"""
import json
import secrets
from pathlib import Path

from app.dominio.ids import id_usuario
from app.puertos.sesiones import PREFIJO

ARCHIVO = Path(__file__).resolve().parent / ".sesiones.json"
VIDA_SEGUNDOS = 6 * 3600
LOTE = 5000


def preparar(redis, cantidad: int, archivo: Path = ARCHIVO) -> list[str]:
    """Devuelve `cantidad` tokens; el token i es la sesión del usuario i+1."""
    try:
        guardados = json.loads(Path(archivo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        guardados = []
    if len(guardados) >= cantidad and all(
            redis.leer(PREFIJO + guardados[i]) == id_usuario(i + 1) for i in (0, cantidad - 1)):
        return guardados[:cantidad]
    tokens = [secrets.token_urlsafe(32) for _ in range(cantidad)]
    for inicio in range(0, cantidad, LOTE):
        lote = {PREFIJO + tokens[i]: id_usuario(i + 1) for i in range(inicio, min(cantidad, inicio + LOTE))}
        redis.guardar_varios(lote, VIDA_SEGUNDOS)
    Path(archivo).write_text(json.dumps(tokens), encoding="utf-8")
    return tokens
