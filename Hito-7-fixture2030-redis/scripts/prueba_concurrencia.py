#!/usr/bin/env python3
"""
prueba_concurrencia.py

Prueba de concurrencia real contra el Redis del docker-compose: varios procesos
en paralelo, cada uno con su propia conexion, trabajan sobre las MISMAS claves.

  Caso atomico (lo que usa el modulo):
    - INCRBY sobre un contador de visitas.
    - ZINCRBY sobre el score de un mismo usuario del ranking.
  Caso no atomico (para comparar):
    - GET, suma en el programa y SET sobre otro contador. Cuando dos procesos
      leen el mismo valor antes de que el otro escriba, se pierde una suma.

Al final, el total del caso atomico tiene que ser exactamente
procesos x repeticiones x delta. Sale con codigo 1 si no coincide. El caso no
atomico solo se informa: lo esperable es que quede por debajo.

Las claves de la prueba son propias (prueba:*) y se borran antes y despues.

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

try:
    import redis
except ImportError:
    redis = None

CONTADOR = "prueba:contador:visitas"
CONTADOR_NO_ATOMICO = "prueba:contador:visitas_no_atomico"
RANKING = "prueba:ranking"
USUARIO = "user-conc"
DELTA_VISITAS = 1
DELTA_PUNTOS = 3
DELTA_ANTELACION = 10
ANTELACION_MAX = 10000000
DELTA_SCORE = DELTA_PUNTOS + DELTA_ANTELACION / ANTELACION_MAX


def trabajador(args):
    host, puerto, repeticiones = args
    r = redis.Redis(host=host, port=puerto, decode_responses=True)
    for _ in range(repeticiones):
        r.incrby(CONTADOR, DELTA_VISITAS)
        r.zincrby(RANKING, DELTA_SCORE, USUARIO)
    for _ in range(repeticiones):
        # Lectura, suma en el programa y escritura: no es atomico.
        valor = int(r.get(CONTADOR_NO_ATOMICO) or 0)
        r.set(CONTADOR_NO_ATOMICO, valor + DELTA_VISITAS)
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
    r.delete(CONTADOR, CONTADOR_NO_ATOMICO, RANKING)

    print(f"Redis {version} | {args.procesos} procesos x {args.repeticiones} repeticiones")
    inicio = time.time()
    with multiprocessing.Pool(args.procesos) as pool:
        pool.map(trabajador, [(args.host, args.puerto, args.repeticiones)] * args.procesos)
    elapsed = time.time() - inicio

    total = args.procesos * args.repeticiones
    esperado_visitas = total * DELTA_VISITAS
    esperado_score = total * DELTA_SCORE

    visitas = int(r.get(CONTADOR))
    score = float(r.zscore(RANKING, USUARIO))
    no_atomico = int(r.get(CONTADOR_NO_ATOMICO))

    print(f"Tiempo: {elapsed:.2f}s")
    print("Caso atomico (INCRBY y ZINCRBY)")
    print(f"  visitas: esperado {esperado_visitas} | obtenido {visitas}")
    print(f"  score:   esperado {esperado_score:.7f} | obtenido {score:.7f}")
    print("Caso no atomico (GET + SET desde el programa)")
    print(f"  visitas: esperado {esperado_visitas} | obtenido {no_atomico} "
          f"(se perdieron {esperado_visitas - no_atomico} sumas)")

    ok = visitas == esperado_visitas and abs(score - esperado_score) < 1e-4
    r.delete(CONTADOR, CONTADOR_NO_ATOMICO, RANKING)
    print("RESULTADO: " + ("OK, el caso atomico no perdio ninguna actualizacion"
                           if ok else "FALLO, hay actualizaciones perdidas en el caso atomico"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
