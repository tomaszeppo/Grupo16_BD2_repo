"""Prepara datos de volumen para las mediciones, escribiendo directo en MongoDB.

Es preparación, no medición: crear cientos de miles de usuarios por la API tardaría mucho y no es lo que se
quiere medir. Todo lo que este script escribe queda anotado en el resumen de la corrida que lo use.

    python -m carga.poblar --usuarios 100000                       usuarios U0000001…U0100000
    python -m carga.poblar --usuarios 100000 --partidos P-03,P-04   además, un pronóstico de cada usuario por partido
    python -m carga.poblar --usuarios 100000 --puntajes             además, puntajes inventados (para medir el ranking)
"""
import argparse
import random
import sys
import time
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient, UpdateOne

from app.config.settings import Settings
from app.dominio.ids import id_pronostico, id_usuario
from seed import cargar_mongo

LOTE = 5000
PAISES = ["ARG", "BRA", "URU", "ESP", "POR", "MAR", "MEX", "FRA", "GER", "ITA"]


def poblar_usuarios(db, cantidad: int, ahora: datetime) -> None:
    for desde in range(1, cantidad + 1, LOTE):
        hasta = min(desde + LOTE, cantidad + 1)
        db.usuarios.bulk_write([
            UpdateOne({"_id": id_usuario(n)},
                      {"$setOnInsert": {"nombre": f"Hincha {n}", "pais": PAISES[n % len(PAISES)], "creado_en": ahora}},
                      upsert=True)
            for n in range(desde, hasta)], ordered=False)
    # Las altas por la API siguen numerando después del último usuario creado acá.
    db.contadores.update_one({"_id": "usuarios"}, {"$max": {"valor": cantidad}}, upsert=True)


def poblar_pronosticos(db, cantidad: int, partido: str, ahora: datetime, rng: random.Random) -> None:
    """Un pronóstico por usuario para el partido, cargado en algún momento de los últimos seis días."""
    db.pronosticos.delete_many({"partido_id": partido})
    for desde in range(1, cantidad + 1, LOTE):
        docs = []
        for n in range(desde, min(desde + LOTE, cantidad + 1)):
            cargado = ahora - timedelta(seconds=rng.randint(60, 6 * 86400))
            usuario = id_usuario(n)
            docs.append({"_id": id_pronostico(usuario, partido), "usuario_id": usuario, "partido_id": partido,
                         "goles_local": rng.choice([0, 0, 1, 1, 1, 2, 2, 3]),
                         "goles_visitante": rng.choice([0, 0, 1, 1, 1, 2, 2, 3]),
                         "cargado_en": cargado, "creado_en": cargado})
        db.pronosticos.insert_many(docs, ordered=False)


def poblar_puntajes(db, cantidad: int, rng: random.Random) -> None:
    """Puntajes inventados con muchos empates, como pasaría con millones de usuarios y pocos puntos posibles."""
    db.puntajes.delete_many({})
    for desde in range(1, cantidad + 1, LOTE):
        docs = []
        for n in range(desde, min(desde + LOTE, cantidad + 1)):
            exactos = rng.randint(0, 6)
            docs.append({"_id": id_usuario(n), "puntos": exactos * 3 + rng.randint(0, 10), "exactos": exactos,
                         "tiempo_seg": rng.randint(0, 2_000_000), "aplicados": ["P-01", "P-02"]})
        db.puntajes.insert_many(docs, ordered=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Datos de volumen para las pruebas de carga")
    parser.add_argument("--usuarios", type=int, required=True)
    parser.add_argument("--partidos", default="", help="ids separados por coma; un pronóstico por usuario en cada uno")
    parser.add_argument("--puntajes", action="store_true", help="carga puntajes inventados para todos los usuarios")
    parser.add_argument("--semilla", type=int, default=2030)
    args = parser.parse_args()

    s = Settings()
    cliente = MongoClient(s.mongo_uri, w="majority", tz_aware=True)
    db = cliente[s.mongo_db]
    cargar_mongo.preparar(db)
    rng = random.Random(args.semilla)
    ahora = datetime.now(timezone.utc)

    inicio = time.perf_counter()
    poblar_usuarios(db, args.usuarios, ahora)
    print(f"usuarios: {db.usuarios.estimated_document_count()}")
    for partido in [p for p in args.partidos.split(",") if p]:
        poblar_pronosticos(db, args.usuarios, partido, ahora, rng)
        print(f"pronósticos de {partido}: {db.pronosticos.count_documents({'partido_id': partido})}")
    if args.puntajes:
        poblar_puntajes(db, args.usuarios, rng)
        print(f"puntajes: {db.puntajes.estimated_document_count()}")
    print(f"listo en {time.perf_counter() - inicio:.1f} s (escritura directa en MongoDB, sin pasar por la API)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
