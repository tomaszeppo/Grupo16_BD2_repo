"""Demo H12: SELECT acotado a una corrida cerrada en Cassandra -> nuevo SQLite local.
No modifica Cassandra. No inicia cargas, no crea tablas remotas ni elimina archivos.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def agregar(filas, partido, max_filas):
    grupos = {}
    vistos = set()
    buckets = Counter()
    for fila in filas:
        if len(vistos) >= max_filas:
            raise ValueError('Limite de filas excedido; no se publica la proyeccion')
        identidad = (partido, str(fila.comentario_id))
        if identidad in vistos:
            raise ValueError('Comentario duplicado entre filas/buckets; revisar fuente')
        vistos.add(identidad)
        if fila.creado_en is None or not fila.usuario_id or fila.likes is None or fila.likes < 0:
            raise ValueError('Fecha, usuario o likes faltantes/invalidos; no se publica')
        fecha = fila.creado_en
        # El driver entrega timestamps Cassandra en UTC, habitualmente sin tzinfo.
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        minuto = fecha.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat()
        grupo = grupos.setdefault(minuto, dict(comentarios=0, usuarios=set(), visibles=0, likes=0))
        grupo['comentarios'] += 1
        grupo['usuarios'].add(fila.usuario_id)
        grupo['visibles'] += fila.estado_moderacion == 'visible'
        grupo['likes'] += fila.likes
        buckets[fila.bucket] += 1
    registros = [(partido, minuto, g['comentarios'], len(g['usuarios']), g['visibles'],
                  g['comentarios']-g['visibles'], g['likes']) for minuto, g in sorted(grupos.items())]
    return registros, len(vistos), buckets


def main(args):
    eventos = [json.loads(l) for l in args.registro.read_text(encoding='utf-8').splitlines() if l.strip()]
    config = next(e['configuracion'] for e in eventos if e.get('evento') == 'inicio')
    resultado = next(e for e in reversed(eventos) if e.get('evento') == 'resultado')
    keyspace = config['keyspace']; partido = config['partido_prueba']; esperadas = config['rows']
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', keyspace) or keyspace.lower().startswith('system'):
        raise ValueError('Keyspace invalido')
    if not re.fullmatch(r'H12-[A-Za-z0-9_-]{1,60}', partido) or not 0 < esperadas <= args.max_filas:
        raise ValueError('Solo corrida H12 y volumen acotado')
    if resultado['exitosas'] != esperadas or any(resultado[k] for k in ('fallidas','sin_resultado','no_intentadas','errores_fase')):
        raise ValueError('Se requiere una corrida terminada sin errores')
    args.salida.mkdir(parents=True, exist_ok=False)
    inicio = datetime.now(timezone.utc).isoformat()
    base = dict(inicio_extraccion_utc=inicio, fuente='Cassandra fixture2030.comentarios_por_partido',
                keyspace=keyspace, partido=partido, registro_sha256=hashlib.sha256(args.registro.read_bytes()).hexdigest(),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                modo='Solo SELECT en fuente; nueva proyeccion local; sin datos individuales de usuarios',
                supuestos='Corrida de laboratorio cerrada, sin escrituras concurrentes; no es snapshot distribuido')
    cluster = None
    try:
        from cassandra.cluster import Cluster
        cluster = Cluster([config['host']], port=config['puerto'], connect_timeout=10)
        sesion = cluster.connect(keyspace); sesion.default_timeout = 30
        consulta = sesion.prepare('SELECT bucket,comentario_id,usuario_id,creado_en,estado_moderacion,likes '
                                 'FROM comentarios_por_partido WHERE partido_codigo=? AND bucket=?')
        def filas():
            for bucket in range(13):
                sentencia = consulta.bind((partido, bucket))
                sentencia.fetch_size = 1000
                yield from sesion.execute(sentencia)
        registros, total, buckets = agregar(filas(), partido, args.max_filas)
        esperados = {b: esperadas//13 + int(b < esperadas % 13) for b in range(13)}
        if total != esperadas or any(buckets[b] != n for b,n in esperados.items()):
            raise ValueError('Conteos de origen no coinciden con la corrida')
        ruta_db = args.salida/'actividad.sqlite'
        with ruta_db.open('xb'):
            pass
        with sqlite3.connect(ruta_db) as db:
            db.execute('BEGIN')
            db.execute('CREATE TABLE actividad_comentarios (partido_codigo TEXT NOT NULL, minuto_utc TEXT NOT NULL, '
                       'comentarios INTEGER NOT NULL, usuarios_activos INTEGER NOT NULL, comentarios_visibles INTEGER NOT NULL, '
                       'comentarios_otro_estado INTEGER NOT NULL, likes_total INTEGER NOT NULL, PRIMARY KEY(partido_codigo,minuto_utc))')
            db.executemany('INSERT INTO actividad_comentarios VALUES (?,?,?,?,?,?,?)', registros)
            assert db.execute('SELECT SUM(comentarios) FROM actividad_comentarios').fetchone()[0] == total
        base.update(estado='VALIDADO',fin_extraccion_utc=datetime.now(timezone.utc).isoformat(),
                    filas_fuente=total,filas_proyeccion=len(registros),conteos_por_bucket=dict(buckets),
                    sqlite_sha256=hashlib.sha256(ruta_db.read_bytes()).hexdigest())
        with (args.salida/'validacion.json').open('x',encoding='utf-8') as f:
            json.dump(base,f,ensure_ascii=False,indent=2)
        print('Proyeccion VALIDADA. Filas fuente:',total,'| Filas analiticas:',len(registros))
        print('Partido | Minuto UTC | Comentarios | Usuarios activos | Visibles | Otros estados | Likes')
        for fila in registros:
            print(' | '.join(map(str,fila)))
        print('Conteos por bucket coinciden. Evidencia:',args.salida)
    except Exception as exc:
        base.update(estado='FALLIDO_NO_PUBLICAR',tipo_error=type(exc).__name__)
        with (args.salida/'fallo.json').open('x',encoding='utf-8') as f:
            json.dump(base,f,ensure_ascii=False,indent=2)
        raise
    finally:
        if cluster is not None:
            cluster.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registro',type=Path,required=True)
    parser.add_argument('--salida',type=Path,required=True,help='Carpeta nueva dentro del volumen montado')
    parser.add_argument('--max-filas',type=int,default=100000)
    main(parser.parse_args())
