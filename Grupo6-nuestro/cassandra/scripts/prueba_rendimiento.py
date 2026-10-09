#!/usr/bin/env python3
"""
prueba_rendimiento.py

Mide la tasa real de escritura (comentarios por segundo) contra la
Cassandra local del docker-compose, insertando en comentarios_por_partido
con escrituras concurrentes de forma asincronica.

Las filas de la prueba van a un partido ficticio (P-PRUEBA) y se borran al
terminar, asi la prueba no deja datos que alteren los conteos de la carga.
Es reproducible: semilla fija y comentario_id determinista (la misma
estrategia que generar_carga_masiva.py).

Requiere el driver oficial de Cassandra para Python (3.11 o anterior):
    pip install cassandra-driver

Uso:
    python3 prueba_rendimiento.py --rows 50000 --concurrencia 100
    python3 prueba_rendimiento.py --rows 200000 --concurrencia 100 --procesos 4

Con --procesos mayor a 1 las filas se reparten entre procesos, cada uno con su
propia conexion: un solo proceso de Python se queda sin CPU antes de llegar al
limite de la base. La tasa que se informa es el total de filas sobre el tiempo
de pared de toda la prueba.

El resultado (tasa obtenida, entorno, fecha) hay que copiarlo a mano en
docs/rendimiento.md; este script no escribe el documento.
"""

import argparse
import datetime
import multiprocessing
import platform
import random
import time
import uuid

try:
    from cassandra.cluster import Cluster
    from cassandra.concurrent import execute_concurrent_with_args
except ImportError:
    Cluster = None

PARTIDO_PRUEBA = "P-PRUEBA"
BUCKETS_PRUEBA = 13
BASE = datetime.datetime(2030, 6, 8, 18, 0, 0)
ORIGEN_UUID1 = datetime.datetime(1582, 10, 15)

INSERT_CQL = """
INSERT INTO comentarios_por_partido
    (partido_codigo, bucket, comentario_id, usuario_id, contenido, creado_en, estado_moderacion, likes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


def timeuuid(momento, contador):
    ts = (momento - ORIGEN_UUID1) // datetime.timedelta(microseconds=1) * 10
    seq = contador & 0x3FFF
    nodo = ((contador >> 14) & 0xFFFFFFFFFF) | 0x010000000000
    return uuid.UUID(fields=(ts & 0xFFFFFFFF, (ts >> 32) & 0xFFFF,
                             ((ts >> 48) & 0x0FFF) | 0x1000, (seq >> 8) | 0x80, seq & 0xFF, nodo))


def trabajo(args):
    """Corre en cada proceso: inserta su tramo de filas y devuelve (exitosas, fallidas)."""
    indice, desde, hasta, concurrencia, host, puerto = args
    cluster = Cluster([host], port=puerto)
    session = cluster.connect("fixture2030")
    insert = session.prepare(INSERT_CQL)
    azar = random.Random(2030 + indice)
    params = []
    for i in range(desde, hasta):
        momento = BASE + datetime.timedelta(milliseconds=i)
        params.append((PARTIDO_PRUEBA, i % BUCKETS_PRUEBA, timeuuid(momento, i),
                       f"user-{i % 5000:06d}", "Comentario de prueba de rendimiento",
                       momento, "visible", azar.randint(0, 10)))
    resultados = execute_concurrent_with_args(session, insert, params, concurrency=concurrencia)
    fallidas = sum(1 for ok, _ in resultados if not ok)
    cluster.shutdown()
    return len(params) - fallidas, fallidas


def correr_prueba(rows, concurrencia, host, puerto, procesos):
    if Cluster is None:
        print("Falta el driver: pip install cassandra-driver")
        return

    tramo = rows // procesos
    tareas = []
    for p in range(procesos):
        desde = p * tramo
        hasta = rows if p == procesos - 1 else desde + tramo
        tareas.append((p, desde, hasta, concurrencia, host, puerto))

    print(f"Insertando {rows} filas con concurrencia {concurrencia} por proceso y {procesos} proceso(s)...")
    inicio = time.time()
    if procesos == 1:
        salidas = [trabajo(tareas[0])]
    else:
        with multiprocessing.Pool(procesos) as pool:
            salidas = pool.map(trabajo, tareas)
    elapsed = time.time() - inicio

    exitosas = sum(s[0] for s in salidas)
    fallidas = sum(s[1] for s in salidas)
    tasa = exitosas / elapsed if elapsed > 0 else 0

    print()
    print("=== Resultado ===")
    print(f"Fecha de ejecucion (UTC): {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print(f"Filas exitosas: {exitosas} / {rows} (fallidas: {fallidas})")
    print(f"Tiempo total: {elapsed:.2f}s")
    print(f"Tasa obtenida: {tasa:.0f} escrituras/seg")
    print(f"Concurrencia por proceso: {concurrencia} | procesos: {procesos}")
    print(f"Python: {platform.python_version()} - SO: {platform.platform()}")

    # Limpieza: se borran las particiones de prueba para no dejar datos de mas.
    cluster = Cluster([host], port=puerto)
    session = cluster.connect("fixture2030")
    borrar = session.prepare("DELETE FROM comentarios_por_partido WHERE partido_codigo = ? AND bucket = ?")
    for b in range(BUCKETS_PRUEBA):
        session.execute(borrar, (PARTIDO_PRUEBA, b))
    cluster.shutdown()
    print("Filas de prueba borradas (particiones P-PRUEBA).")
    print()
    print("Copiar estos valores a docs/rendimiento.md junto con la version de")
    print("Cassandra (SHOW VERSION en cqlsh) y los recursos de CPU/RAM asignados")
    print("a Docker Desktop al momento de la prueba (RNF9).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=50_000,
                         help="Cantidad de filas a insertar en la prueba (default: 50.000)")
    parser.add_argument("--concurrencia", type=int, default=100,
                         help="Escrituras concurrentes en simultaneo por proceso (default: 100)")
    parser.add_argument("--procesos", type=int, default=1,
                         help="Procesos en paralelo, cada uno con su conexion (default: 1)")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=9042)
    args = parser.parse_args()
    correr_prueba(args.rows, args.concurrencia, args.host, args.puerto, args.procesos)
