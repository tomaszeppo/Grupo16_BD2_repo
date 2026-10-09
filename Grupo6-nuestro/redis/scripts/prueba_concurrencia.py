#!/usr/bin/env python3
"""
prueba_concurrencia.py

Prueba de concurrencia real contra el Redis del docker-compose: varios
procesos en paralelo, cada uno con su propia conexion, ejecutan

  - EVALSHA del script de ranking (actualizar_ranking.lua) sobre el MISMO
    usuario, y
  - INCR sobre el MISMO contador de likes.

Si las operaciones fueran de leer-sumar-escribir desde la aplicacion, se
perderian actualizaciones. Al final, el total tiene que ser exactamente
procesos x repeticiones x delta. El programa sale con codigo 1 si no coincide.

Las claves de la prueba son propias (prueba:*) y se borran antes y despues,
asi no tocan los datos de muestra y la prueba se puede repetir.

Requiere: pip install redis
Uso:
    python3 prueba_concurrencia.py --procesos 8 --repeticiones 5000
    # desde un contenedor de la red del compose:
    python prueba_concurrencia.py --host redis
"""

import argparse
import multiprocessing
import sys
import time
from pathlib import Path

try:
    import redis
except ImportError:
    redis = None

CLAVE_HASH = "prueba:ranking:usuario:user-conc"
CLAVE_ZSET = "prueba:ranking"
CLAVE_LIKES = "prueba:likes:comentario:conc"
USUARIO = "user-conc"
DELTA_PUNTOS = 3
DELTA_ANTELACION = 10
ANTELACION_MAX = 10000000


def leer_script():
    ruta = Path(__file__).with_name("actualizar_ranking.lua")
    return ruta.read_text(encoding="utf-8")


def trabajador(args):
    host, puerto, sha, repeticiones = args
    r = redis.Redis(host=host, port=puerto, decode_responses=True)
    for _ in range(repeticiones):
        r.evalsha(sha, 2, CLAVE_HASH, CLAVE_ZSET, USUARIO,
                  DELTA_PUNTOS, DELTA_ANTELACION, ANTELACION_MAX, "2030-07-20T22:00:00")
        r.incr(CLAVE_LIKES)
    return repeticiones


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=6379)
    parser.add_argument("--procesos", type=int, default=8)
    parser.add_argument("--repeticiones", type=int, default=5000)
    args = parser.parse_args()

    if redis is None:
        print("Falta el driver: pip install redis")
        sys.exit(2)

    r = redis.Redis(host=args.host, port=args.puerto, decode_responses=True)
    version = r.info("server").get("redis_version", "desconocida")
    r.delete(CLAVE_HASH, CLAVE_ZSET, CLAVE_LIKES)
    sha = r.script_load(leer_script())

    print(f"Redis {version} | {args.procesos} procesos x {args.repeticiones} repeticiones")
    inicio = time.time()
    with multiprocessing.Pool(args.procesos) as pool:
        pool.map(trabajador, [(args.host, args.puerto, sha, args.repeticiones)] * args.procesos)
    elapsed = time.time() - inicio

    total = args.procesos * args.repeticiones
    esperado_puntos = total * DELTA_PUNTOS
    esperado_antelacion = total * DELTA_ANTELACION
    esperado_likes = total

    puntos = int(r.hget(CLAVE_HASH, "puntos"))
    antelacion = float(r.hget(CLAVE_HASH, "antelacion_total"))
    likes = int(r.get(CLAVE_LIKES))
    score = float(r.zscore(CLAVE_ZSET, USUARIO))
    esperado_score = esperado_puntos + esperado_antelacion / ANTELACION_MAX

    print(f"Tiempo: {elapsed:.2f}s ({2 * total / elapsed:.0f} operaciones/seg entre EVALSHA e INCR)")
    print(f"puntos:     esperado {esperado_puntos} | obtenido {puntos}")
    print(f"antelacion: esperado {esperado_antelacion} | obtenido {antelacion:.0f}")
    print(f"likes:      esperado {esperado_likes} | obtenido {likes}")
    print(f"score:      esperado {esperado_score:.7f} | obtenido {score:.7f}")

    ok = (puntos == esperado_puntos and int(antelacion) == esperado_antelacion
          and likes == esperado_likes and abs(score - esperado_score) < 1e-6)
    r.delete(CLAVE_HASH, CLAVE_ZSET, CLAVE_LIKES)
    print("RESULTADO: " + ("OK, no se perdio ninguna actualizacion" if ok else "FALLO, hay actualizaciones perdidas"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
