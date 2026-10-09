#!/usr/bin/env python3
"""
validar_carga_masiva.py

Compara lo que hay en Cassandra con los conteos esperados que escribe
generar_carga_masiva.py, particion por particion:

  - comentarios_por_partido: un SELECT COUNT(*) por (partido_codigo, bucket).
  - comentarios_por_usuario: un SELECT COUNT(*) por usuario_id.

Cada COUNT(*) esta acotado a una sola particion; nunca se cuenta toda la
tabla de un millon de filas. Sale con codigo 1 si alguna particion no coincide,
para poder usarlo despues de cada carga y comprobar que correr COPY dos veces
no cambia los totales.

Requiere el driver (pip install cassandra-driver, Python 3.11 o anterior).
Desde un contenedor, con las carpetas data/ y scripts/ montadas:
    python /scripts/validar_carga_masiva.py --host cassandra --datos /data

Los conteos esperados cubren solo la carga masiva: la carga de muestra
(carga_muestra.cql) usa las mismas tablas, asi que antes de la carga masiva hay
que vaciarlas con TRUNCATE (ver README).
"""

import argparse
import csv
import sys
import time
from pathlib import Path

try:
    from cassandra.cluster import Cluster
    from cassandra.concurrent import execute_concurrent_with_args
except ImportError:
    Cluster = None


def leer_esperado(ruta, columnas_clave):
    esperado = {}
    with ruta.open(encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            clave = tuple(fila[c] for c in columnas_clave)
            esperado[clave] = int(fila["filas_esperadas"])
    return esperado


def contar(session, cql, claves, concurrencia):
    sentencia = session.prepare(cql)
    resultados = execute_concurrent_with_args(session, sentencia, claves, concurrency=concurrencia)
    conteos = {}
    for clave, (ok, res) in zip(claves, resultados):
        if not ok:
            raise RuntimeError(f"Fallo el conteo de {clave}: {res}")
        conteos[clave] = res.one()[0]
    return conteos


def comparar(nombre, esperado, real):
    distintas = [(k, esperado[k], real[k]) for k in esperado if real[k] != esperado[k]]
    print(nombre)
    print(f"  particiones consultadas: {len(esperado)}")
    print(f"  filas esperadas: {sum(esperado.values())} | filas encontradas: {sum(real.values())}")
    print(f"  particiones que no coinciden: {len(distintas)}")
    for k, e, r in distintas[:10]:
        print(f"    {k}: esperadas {e}, encontradas {r}")
    return not distintas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=9042)
    parser.add_argument("--datos", default="../data", help="Carpeta con los conteo_esperado_*.csv")
    parser.add_argument("--concurrencia", type=int, default=50)
    parser.add_argument("--sin-usuarios", action="store_true",
                        help="Solo validar comentarios_por_partido (416 particiones)")
    args = parser.parse_args()

    if Cluster is None:
        print("Falta el driver: pip install cassandra-driver")
        sys.exit(2)

    datos = Path(args.datos)
    cluster = Cluster([args.host], port=args.puerto)
    session = cluster.connect("fixture2030")
    inicio = time.time()
    todo_ok = True

    crudo = leer_esperado(datos / "conteo_esperado_por_particion.csv", ["partido_codigo", "bucket"])
    esperado = {(p, int(b)): v for (p, b), v in crudo.items()}
    real = contar(session,
                  "SELECT COUNT(*) FROM comentarios_por_partido WHERE partido_codigo = ? AND bucket = ?",
                  list(esperado), args.concurrencia)
    todo_ok &= comparar("comentarios_por_partido (partido, bucket)", esperado, real)

    if not args.sin_usuarios:
        esperado_u = leer_esperado(datos / "conteo_esperado_por_usuario.csv", ["usuario_id"])
        real_u = contar(session,
                        "SELECT COUNT(*) FROM comentarios_por_usuario WHERE usuario_id = ?",
                        list(esperado_u), args.concurrencia)
        todo_ok &= comparar("comentarios_por_usuario (usuario_id)", esperado_u, real_u)

    print(f"Tiempo de validacion: {time.time() - inicio:.1f}s")
    print("RESULTADO: " + ("OK, todos los conteos coinciden" if todo_ok else "HAY DIFERENCIAS"))
    cluster.shutdown()
    sys.exit(0 if todo_ok else 1)


if __name__ == "__main__":
    main()
