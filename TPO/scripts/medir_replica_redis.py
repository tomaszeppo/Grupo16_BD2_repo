"""Cuánto tarda un cambio en llegar a la réplica de Redis (la copia de lectura de "la otra región").

Escribe una marca en el primario y la busca en la réplica cada milisegundo, hasta encontrarla o hasta el tope.
Es el atraso que vería, por ejemplo, la tabla del ranking leída desde la réplica de otra región.

    docker compose run --rm herramientas python -m scripts.medir_replica_redis --muestras 1000

Deja el resumen en evidencia/replica_redis_<fecha>_<hora>_resumen.json.
"""
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from carga.resumen import percentil

EVIDENCIA = Path(__file__).resolve().parent.parent / "evidencia"


def resumir_atrasos(atrasos_ms: list[float | None], tope_ms: float) -> dict:
    """`None` = la marca no apareció en la réplica antes del tope."""
    llegaron = [a for a in atrasos_ms if a is not None]
    medida = (lambda p: round(percentil(llegaron, p), 3)) if llegaron else (lambda p: None)
    return {"muestras": len(atrasos_ms), "tope_ms": tope_ms, "sin_llegar": len(atrasos_ms) - len(llegaron),
            "p50_ms": medida(50), "p95_ms": medida(95), "p99_ms": medida(99),
            "max_ms": round(max(llegaron), 3) if llegaron else None}


def medir(primario, replica, muestras: int, intervalo_ms: float, tope_ms: float) -> list[float | None]:
    atrasos = []
    for n in range(muestras):
        clave, valor = f"medicion:replica:{n}", str(time.time_ns())
        primario.set(clave, valor, ex=60)
        inicio = time.perf_counter()
        atraso = None
        while (time.perf_counter() - inicio) * 1000 < tope_ms:
            if replica.get(clave) == valor:
                atraso = (time.perf_counter() - inicio) * 1000
                break
            time.sleep(0.001)
        atrasos.append(atraso)
        time.sleep(intervalo_ms / 1000)
    return atrasos


def main() -> int:
    import redis

    from app.config.settings import get_settings

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--muestras", type=int, default=1000)
    parser.add_argument("--intervalo-ms", type=float, default=10)
    parser.add_argument("--tope-ms", type=float, default=2000)
    args = parser.parse_args()
    s = get_settings()
    opciones = {"password": s.redis_password or None, "decode_responses": True, "socket_timeout": 5}
    primario = redis.Redis.from_url(s.redis_url, **opciones)
    replica = redis.Redis.from_url(s.redis_replica_url, **opciones)
    estado = replica.info("replication")
    resumen = {"commit": os.environ.get("COMMIT", "sin commit"), "fecha": datetime.now().isoformat(timespec="seconds"),
               "replica": {"rol": estado.get("role"), "enlace": estado.get("master_link_status")},
               **resumir_atrasos(medir(primario, replica, args.muestras, args.intervalo_ms, args.tope_ms), args.tope_ms)}
    EVIDENCIA.mkdir(exist_ok=True)
    ruta = EVIDENCIA / f"replica_redis_{datetime.now():%Y%m%d_%H%M%S}_resumen.json"
    ruta.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"réplica de Redis: p50 {resumen['p50_ms']} ms, p95 {resumen['p95_ms']} ms, p99 {resumen['p99_ms']} ms, "
          f"máx {resumen['max_ms']} ms, sin llegar {resumen['sin_llegar']} de {resumen['muestras']}")
    print(f"evidencia: {ruta.relative_to(EVIDENCIA.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
