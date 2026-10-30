#!/usr/bin/env python3
"""H12: benchmark de escrituras directas a Cassandra, adaptado del H6 corregido.
Requiere host, puerto, keyspace, ID H12 exclusivo, salida nueva y --confirmar-escrituras.
Los registros permanecen en la base. No hay limpieza automatica ni llamadas a la API.
Consultar README y --help para los parametros. Requiere cassandra-driver instalado.
"""

import argparse
import datetime
import hashlib
from importlib.metadata import version
import json
import multiprocessing
import platform
import random
import re
import time
import uuid
from pathlib import Path

from metricas_operaciones import SesionMedida, detalle_error, resumir

try:
    from cassandra.cluster import Cluster
    from cassandra.concurrent import execute_concurrent_with_args
except ImportError:
    Cluster = None

PARTIDO_PRUEBA = "P-PRUEBA"
VERSION_BENCHMARK = '2.0-instrumentado'
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
    """Mantiene el planificador del driver y registra cada confirmación o error."""
    indice, desde, hasta, concurrencia, host, puerto, keyspace, partido, ruta = args
    cluster=None;medida=None;inicio=None;fin=None
    resultado={'proceso':indice,'muestras':ruta,'inicio_ns':None,'fin_ns':None,'error_fase':None}
    try:
        cluster=Cluster([host],port=puerto,connect_timeout=10)
        session=cluster.connect(keyspace);session.default_timeout=10
        from cassandra.cluster import EXEC_PROFILE_DEFAULT
        profile=session.get_execution_profile(EXEC_PROFILE_DEFAULT)
        resultado['driver']={'version':version('cassandra-driver'),'protocolo':cluster.protocol_version,
            'consistencia':profile.consistency_level,'retry_policy':type(profile.retry_policy).__name__,
            'timeout_s':10,'paginador':'execute_concurrent_with_args','raise_on_first_error':False}
        insert=session.prepare(INSERT_CQL)
        azar=random.Random(2030+indice);params=[]
        for i in range(desde,hasta):
            momento=BASE+datetime.timedelta(milliseconds=i)
            params.append((partido,i%BUCKETS_PRUEBA,timeuuid(momento,i),f'user-{i%5000:06d}',
                           'Comentario de prueba de rendimiento',momento,'visible',azar.randint(0,10)))
        medida=SesionMedida(session,indice,desde)
        inicio=time.perf_counter_ns()
        resultados=execute_concurrent_with_args(medida,insert,params,concurrency=concurrencia,
                                                raise_on_first_error=False)
        fin=time.perf_counter_ns()
        resultado['respuestas_planificador']=len(resultados)
        resultado['errores_planificador']=sum(not ok for ok,_ in resultados)
    except Exception as exc:
        resultado['error_fase']=detalle_error(exc)
    finally:
        if inicio is not None and fin is None:fin=time.perf_counter_ns()
        if cluster is not None:
            try:cluster.shutdown()
            except Exception as exc:
                if resultado['error_fase'] is None:resultado['error_fase']=detalle_error(exc)
        muestras=medida.muestras if medida else []
        if muestras:fin=max(fin or 0,max(m['fin_monotonico_ns'] for m in muestras))
        # Ruta reservada por el padre: append conserva el archivo exclusivo y sus datos.
        with Path(ruta).open('a',encoding='utf-8') as archivo:
            for muestra in muestras:archivo.write(json.dumps(muestra)+'\n')
        resultado.update(inicio_ns=inicio,fin_ns=fin,
                         max_en_curso=medida.max_en_curso if medida else 0,
                         iniciadas=medida.siguiente-desde if medida else 0,
                         muestras_registradas=len(muestras))
    return resultado


def correr_prueba(rows, concurrencia, host, puerto, procesos, keyspace, partido, salida):
    if Cluster is None:
        raise RuntimeError("Falta el driver: pip install cassandra-driver")

    if min(rows, concurrencia, procesos) <= 0 or procesos > rows:
        raise ValueError("Filas, concurrencia y procesos deben ser positivos; procesos <= filas")
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', keyspace) or keyspace.lower().startswith('system'):
        raise ValueError("Keyspace de laboratorio no valido")
    if not re.fullmatch(r'H12-[A-Za-z0-9_-]{1,60}', partido):
        raise ValueError("La particion de prueba debe usar un ID H12- exclusivo de esta corrida")
    # Se reserva una salida nueva antes de conectar: ninguna corrida pisa evidencia previa.
    with Path(salida).open('x', encoding='utf-8') as archivo:
        configuracion = dict(rows=rows, concurrencia_por_proceso=concurrencia, procesos=procesos,
                             keyspace=keyspace, partido_prueba=partido, host=host, puerto=puerto,
                             rampa_s=0,sostenimiento='Hasta agotar el lote; disminuye al drenar los ultimos pendientes',
                             semilla_base=2030,usuarios=5000,buckets=13,timeout_operacion_s=10)
        scripts=[Path(__file__),Path(__file__).with_name('metricas_operaciones.py')]
        huellas={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in scripts}
        archivo.write(json.dumps({'evento':'inicio','fecha_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'version_benchmark':VERSION_BENCHMARK,'configuracion':configuracion,'codigo_sha256':huellas})+'\n'); archivo.flush()
        rutas=[Path(salida).with_name(Path(salida).stem+f'.operaciones.p{i:02d}.jsonl') for i in range(procesos)]
        for ruta in rutas:
            with ruta.open('x',encoding='utf-8'):pass
        cluster = Cluster([host], port=puerto, connect_timeout=10)
        try:
            session = cluster.connect(keyspace)
            session.default_timeout=10
            local=session.execute('SELECT release_version,cql_version,cluster_name,data_center FROM system.local').one()
            replication=session.execute('SELECT replication FROM system_schema.keyspaces WHERE keyspace_name=%s',(keyspace,)).one()
            archivo.write(json.dumps({'evento':'producto_observado','version':local.release_version,
                'cql_version':local.cql_version,'cluster_name':local.cluster_name,'data_center':local.data_center,
                'replication':dict(replication.replication) if replication else None})+'\n');archivo.flush()
            # Leer todas las particiones de la corrida impide reutilizar datos anteriores.
            consulta = session.prepare('SELECT comentario_id FROM comentarios_por_partido WHERE partido_codigo=? AND bucket=? LIMIT 1')
            for bucket in range(BUCKETS_PRUEBA):
                if session.execute(consulta, (partido,bucket)).one():
                    raise ValueError('La particion de esta corrida ya contiene datos; usar un ID nuevo')
        except Exception as exc:
            archivo.write(json.dumps({'evento':'preflight_fallido','tipo':type(exc).__name__})+'\n')
            raise
        finally:
            cluster.shutdown()
        try:
            resultado = ejecutar(rows, concurrencia, host, puerto, procesos, keyspace, partido,rutas)
            archivo.write(json.dumps({'evento':'resultado',**resultado})+'\n')
            return resultado
        except BaseException as exc:
            archivo.write(json.dumps({'evento':'fallo','tipo':type(exc).__name__, 'datos_parciales_conservados':True})+'\n')
            raise


def ejecutar(rows, concurrencia, host, puerto, procesos, keyspace, partido,rutas):

    tramo = rows // procesos
    tareas = []
    for p in range(procesos):
        desde = p * tramo
        hasta = rows if p == procesos - 1 else desde + tramo
        tareas.append((p, desde, hasta, concurrencia, host, puerto, keyspace, partido,str(rutas[p])))

    print(f"Benchmark {VERSION_BENCHMARK}")
    print(f"Insertando {rows} filas con concurrencia {concurrencia} por proceso y {procesos} proceso(s)...")
    inicio = time.perf_counter()
    if procesos == 1:
        salidas = [trabajo(tareas[0])]
    else:
        with multiprocessing.Pool(procesos) as pool:
            salidas = pool.map(trabajo, tareas)
    elapsed = time.perf_counter() - inicio
    muestras=[]
    for ruta in rutas:
        with ruta.open(encoding='utf-8') as raw:muestras.extend(json.loads(line) for line in raw if line.strip())
    starts=[s['inicio_ns'] for s in salidas if s['inicio_ns'] is not None]
    ends=[s['fin_ns'] for s in salidas if s['fin_ns'] is not None]
    resumen=resumir(muestras,rows,elapsed,min(starts) if starts else None,max(ends) if ends else None,
                    iniciadas=sum(s['iniciadas'] for s in salidas))
    errores_fase=[s['error_fase'] for s in salidas if s['error_fase']]
    resumen.update(fecha_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        python=platform.python_version(),sistema=platform.platform(),version_benchmark=VERSION_BENCHMARK,
        datos_conservados=True,procesos=salidas,errores_fase=errores_fase)
    exitosas=resumen['exitosas'];fallidas=resumen['fallidas'];tasa=resumen['escrituras_por_segundo']

    print()
    print("=== Resultado ===")
    print(f"Fecha de ejecucion (UTC): {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print(f"Filas exitosas: {exitosas} / {rows} (fallidas: {fallidas})")
    print(f"Intentadas: {resumen['intentadas']} | Con resultado: {resumen['con_resultado']} | Inconclusas: {resumen['sin_resultado']}")
    print(f"No intentadas: {resumen['no_intentadas']}; errores de fase: {len(errores_fase)}")
    print(f"Tiempo de carga: {resumen['segundos_carga']:.3f}s | Cliente total: {elapsed:.3f}s")
    print(f"Tasa obtenida: {tasa:.0f} escrituras/seg")
    print(f"Concurrencia por proceso: {concurrencia} | procesos: {procesos}")
    print(f"Pico observado por proceso: {[s['max_en_curso'] for s in salidas]}")
    print(f"Python: {platform.python_version()} - SO: {platform.platform()}")
    for nombre,datos in [('Todas',resumen['latencia_todos_ms']),('Confirmadas',resumen['latencia_confirmadas_ms'])]:
        print(f"Latencias {nombre} (ms): "+' | '.join(f'{k}={datos[k]:.3f}' if datos[k] is not None else f'{k}=N/D' for k in ('min','promedio','p50','p95','p99','max')))
    error_pct=resumen['tasa_error_porcentaje']
    print(f"Tasa de error: {f'{error_pct:.3f}%' if error_pct is not None else 'N/D'} | Tipos: {resumen['errores_por_tipo']}")
    if errores_fase:print(f'Errores de fase: {errores_fase}')
    print('Una operacion sin confirmacion puede haber persistido: verificar conteos despues.')

    print(f'Datos conservados en {partido}; evidencia en el archivo indicado por --salida.')
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=50_000,
                         help="Cantidad de filas a insertar en la prueba (default: 50.000)")
    parser.add_argument("--concurrencia", type=int, default=100,
                         help="Escrituras concurrentes en simultaneo por proceso (default: 100)")
    parser.add_argument("--procesos", type=int, default=1,
                         help="Procesos en paralelo, cada uno con su conexion (default: 1)")
    parser.add_argument("--host", required=True)
    parser.add_argument("--puerto", type=int, required=True)
    parser.add_argument("--keyspace", required=True)
    parser.add_argument("--partido-prueba", required=True, help="ID H12- nuevo por corrida")
    parser.add_argument("--salida", type=Path, required=True, help="JSONL nuevo; carpeta existente")
    parser.add_argument("--confirmar-escrituras", action="store_true")
    args = parser.parse_args()
    if not args.confirmar_escrituras:
        parser.error('Esta prueba inserta y conserva datos. Revisar destino y usar --confirmar-escrituras.')
    resultado = correr_prueba(args.rows, args.concurrencia, args.host, args.puerto, args.procesos,
                             args.keyspace, args.partido_prueba, args.salida)
    raise SystemExit(1 if resultado['fallidas'] or resultado['no_intentadas'] or resultado['sin_resultado'] or resultado['errores_fase'] else 0)
