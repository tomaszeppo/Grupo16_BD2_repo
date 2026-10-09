#!/usr/bin/env python3
"""
prueba_rendimiento.py

Mide la tasa real de operaciones por segundo contra el Redis local del
docker-compose, para dos operaciones del modulo: la actualizacion atomica
del ranking (EVALSHA) y una lectura de cache (GET). Ambas son del tamano
que la consigna permite para un ambiente de laboratorio: un conjunto
acotado, no un benchmark industrial.

Requiere el driver oficial de Redis para Python:
    pip install redis

Uso:
    python3 prueba_rendimiento.py --operaciones 10000
"""

import argparse
import datetime
import platform
import time
import uuid

try:
    import redis
except ImportError:
    redis = None


LUA_ACTUALIZAR_RANKING = (
    "local hash_key = KEYS[1]; local zset_key = KEYS[2]; "
    "local usuario_id = ARGV[1]; local delta_puntos = tonumber(ARGV[2]); "
    "local delta_antelacion = tonumber(ARGV[3]); local antelacion_max = tonumber(ARGV[4]); "
    "local puntos = redis.call('HINCRBY', hash_key, 'puntos', delta_puntos); "
    "local antelacion = redis.call('HINCRBYFLOAT', hash_key, 'antelacion_total', delta_antelacion); "
    "redis.call('HSET', hash_key, 'actualizado_en', ARGV[5]); "
    "local score = tonumber(puntos) + (tonumber(antelacion) / antelacion_max); "
    "redis.call('ZADD', zset_key, score, usuario_id); "
    "return {puntos, antelacion, tostring(score)}"
)


def correr_prueba(n: int, host: str, puerto: int):
    if redis is None:
        print("Falta el driver: pip install redis")
        return

    r = redis.Redis(host=host, port=puerto, decode_responses=True)
    sha = r.script_load(LUA_ACTUALIZAR_RANKING)
    version = r.info("server").get("redis_version", "desconocida")

    print(f"Conectado a Redis {version} en {host}:{puerto}")

    # --- Prueba 1: actualizacion atomica del ranking (EVALSHA) ---
    inicio = time.time()
    for i in range(n):
        uid = f"user-prueba-{i % 1000:05d}"  # 1000 usuarios distintos, reutilizados
        r.evalsha(
            sha, 2,
            f"ranking:prueba:usuario:{uid}", "ranking:prueba",
            uid, 1, 1, 10_000_000,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
    elapsed_ranking = time.time() - inicio
    tasa_ranking = n / elapsed_ranking if elapsed_ranking > 0 else 0

    # --- Prueba 2: lectura de cache (GET), con la clave ya precargada ---
    r.set("cache:prueba:equipo", '{"codigo":"ARG"}', ex=300)
    inicio = time.time()
    for _ in range(n):
        r.get("cache:prueba:equipo")
    elapsed_cache = time.time() - inicio
    tasa_cache = n / elapsed_cache if elapsed_cache > 0 else 0

    # Limpieza de las claves de prueba (no son parte del modulo real)
    r.delete("ranking:prueba")
    cursor = 0
    while True:
        cursor, claves = r.scan(cursor, match="ranking:prueba:usuario:*", count=500)
        if claves:
            r.delete(*claves)
        if cursor == 0:
            break
    r.delete("cache:prueba:equipo")

    print()
    print("=== Resultado ===")
    print(f"Fecha de ejecucion (UTC): {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print(f"Version de Redis: {version}")
    print(f"Operaciones por prueba: {n}")
    print(f"EVALSHA (actualizar ranking): {elapsed_ranking:.2f}s -> {tasa_ranking:.0f} ops/seg")
    print(f"GET (lectura de cache):       {elapsed_cache:.2f}s -> {tasa_cache:.0f} ops/seg")
    print(f"Python: {platform.python_version()} — SO: {platform.platform()}")
    print()
    print("Copiar estos valores a docs/rendimiento.md junto con los recursos de")
    print("CPU/RAM asignados a Docker Desktop al momento de la prueba (RNF10).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operaciones", type=int, default=10_000,
                         help="Cantidad de operaciones por prueba (default: 10.000)")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=6379)
    args = parser.parse_args()
    correr_prueba(args.operaciones, args.host, args.puerto)
