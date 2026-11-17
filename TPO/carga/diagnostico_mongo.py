"""Mide cuántas escrituras por segundo acepta MongoDB sin la API de por medio.

Sirve para separar dónde está el límite: si acá da mucho más que por la API, el cuello de botella es la API;
si da parecido, es la base. Compara además el costo de pedir confirmación de la mayoría de los nodos.
Escribe en una colección aparte (`diagnostico`) y la borra al terminar.

    python -m carga.diagnostico_mongo --hilos 50 --segundos 10
"""
import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

from app.config.settings import Settings
from carga.resumen import percentil

EVIDENCIA = Path(__file__).resolve().parent.parent / "evidencia"
VARIANTES = {
    "w1_sin_esperar_al_diario": WriteConcern(w=1, j=False),
    "w1_con_diario": WriteConcern(w=1, j=True),
    "mayoria": WriteConcern(w="majority"),  # la que usa la API
}


def medir(coleccion, hilos: int, segundos: float) -> dict:
    tiempos: list[float] = []
    candado = threading.Lock()
    fin = time.perf_counter() + segundos

    def trabajar(numero: int) -> None:
        propios, n = [], 0
        while time.perf_counter() < fin:
            n += 1
            t0 = time.perf_counter()
            coleccion.update_one({"_id": f"{numero}:{n % 5000}"}, {"$set": {"valor": n, "cuando": t0}}, upsert=True)
            propios.append((time.perf_counter() - t0) * 1000)
        with candado:
            tiempos.extend(propios)

    inicio = time.perf_counter()
    grupo = [threading.Thread(target=trabajar, args=(i,)) for i in range(hilos)]
    for h in grupo:
        h.start()
    for h in grupo:
        h.join()
    duracion = time.perf_counter() - inicio
    return {"escrituras": len(tiempos), "por_segundo": round(len(tiempos) / duracion, 1),
            "p50_ms": round(percentil(tiempos, 50), 1), "p95_ms": round(percentil(tiempos, 95), 1),
            "p99_ms": round(percentil(tiempos, 99), 1)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Escrituras directas a MongoDB, sin la API")
    parser.add_argument("--hilos", type=int, default=50)
    parser.add_argument("--segundos", type=float, default=10)
    parser.add_argument("--nota", action="append", default=[])
    args = parser.parse_args()

    s = Settings()
    cliente = MongoClient(s.mongo_uri, maxPoolSize=args.hilos + 10, tz_aware=True)
    db = cliente[s.mongo_db]
    inicio = datetime.now(timezone.utc)
    resultados = {}
    for nombre, garantia in VARIANTES.items():
        coleccion = db.get_collection("diagnostico", write_concern=garantia)
        coleccion.drop()
        resultados[nombre] = medir(coleccion, args.hilos, args.segundos)
        print(f"{nombre}: {resultados[nombre]}")
    db.diagnostico.drop()

    resumen = {
        "escenario": "diagnostico_mongo", "inicio": inicio.isoformat(), "commit": os.environ.get("COMMIT", "sin commit"),
        "parametros": {"hilos": args.hilos, "segundos": args.segundos},
        "entorno": {k.lower(): os.environ.get(k) for k in ("MONGO_MEMORIA", "MONGO_CPUS")} | {"nodos_de_mongodb": 3},
        "que_mide": "upsert de documentos chicos directo con el driver, sin la API, con tres garantías de escritura",
        "medicion": resultados, "notas": args.nota,
    }
    EVIDENCIA.mkdir(exist_ok=True)
    ruta = EVIDENCIA / f"diagnostico_mongo_{inicio.strftime('%Y%m%d_%H%M%S')}_resumen.json"
    ruta.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"evidencia: {ruta.relative_to(EVIDENCIA.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
