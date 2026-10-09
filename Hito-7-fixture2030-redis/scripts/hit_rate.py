#!/usr/bin/env python3
"""
hit_rate.py

Mide el hit rate de la cache con INFO stats: toma keyspace_hits y
keyspace_misses antes y despues de una microprueba y calcula la diferencia.

La microprueba hace lecturas de cache:equipo:{codigo} de los equipos de la
carga de muestra (que existen: hits) y de equipos que no estan cacheados
(misses), en una proporcion fija. Es una prueba chica y acotada, no un
benchmark: sirve para mostrar como se mide, no para predecir produccion.

Requiere: pip install redis
Uso:
    python3 hit_rate.py --lecturas 1000
"""

import argparse
import sys

try:
    import redis
except ImportError:
    redis = None

CACHEADOS = ["ARG", "BRA", "ESP", "FRA", "GER", "JPN"]
NO_CACHEADOS = ["URU", "COL", "ITA", "POR"]


def contadores(r):
    s = r.info("stats")
    return s["keyspace_hits"], s["keyspace_misses"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=6379)
    parser.add_argument("--lecturas", type=int, default=1000)
    args = parser.parse_args()
    if redis is None:
        print("Falta el driver: pip install redis")
        sys.exit(2)

    r = redis.Redis(host=args.host, port=args.puerto, decode_responses=True)
    print(f"Redis {r.info('server')['redis_version']}")
    hits_antes, misses_antes = contadores(r)
    print(f"Antes   -> keyspace_hits: {hits_antes} | keyspace_misses: {misses_antes}")

    # 7 de cada 10 lecturas son de equipos cacheados, 3 de cada 10 no.
    esperados_hits = esperados_misses = 0
    for i in range(args.lecturas):
        if i % 10 < 7:
            r.get("cache:equipo:" + CACHEADOS[i % len(CACHEADOS)])
            esperados_hits += 1
        else:
            r.get("cache:equipo:" + NO_CACHEADOS[i % len(NO_CACHEADOS)])
            esperados_misses += 1

    hits_desp, misses_desp = contadores(r)
    print(f"Despues -> keyspace_hits: {hits_desp} | keyspace_misses: {misses_desp}")
    dh, dm = hits_desp - hits_antes, misses_desp - misses_antes
    print(f"Diferencia -> hits: {dh} | misses: {dm}")
    print(f"Hit rate de la microprueba: {100 * dh / (dh + dm):.1f}% ({dh} de {dh + dm})")
    print(f"(esperado por construccion: {esperados_hits} hits y {esperados_misses} misses; "
          "si la carga de muestra no esta cargada o vencio el TTL de 300 s, hay mas misses)")


if __name__ == "__main__":
    main()
