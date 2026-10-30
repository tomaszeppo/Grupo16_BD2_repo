"""Valida archivos locales y hashes, sin conectar ni escribir en ninguna base."""
import argparse
import csv
import hashlib
import json
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


def validar(folder: Path):
    manifest = json.loads((folder/'manifiesto.json').read_text(encoding='utf-8'))
    assert manifest['estado'] == 'PREPARADO_NO_INSERTADO'
    for entry in manifest['archivos']:
        p=folder/entry['ruta']
        assert p.is_file() and p.stat().st_size == entry['bytes'], p
        assert hashlib.sha256(p.read_bytes()).hexdigest() == entry['sha256'], p
    neo=json.loads((folder/'neo4j_parametros.json').read_text(encoding='utf-8'))
    partidos=neo['partidos']; ids={p['id'] for p in partidos}
    assert len(partidos) == len(ids) == 32
    assert len({s['id'] for s in neo['estadios']}) == 10
    assert all(p['equipoLocal'] != p['equipoVisitante'] for p in partidos)
    assert all(p['estadio'] in {s['id'] for s in neo['estadios']} for p in partidos)
    rows=[json.loads(x) for x in (folder/'comentarios_propuestos.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows) == len({r['comentario_id'] for r in rows}) == 1920
    counts=Counter()
    for r in rows:
        assert uuid.UUID(r['comentario_id']).version == 5
        assert r['partido_referencia_h5'] in ids and r['partido_id_cassandra'] is None
        inicio=datetime.fromisoformat(r['ventana']); creado=datetime.fromisoformat(r['creado_en'])
        assert inicio.minute in (0,30) and inicio.second == 0 and inicio.tzinfo
        assert inicio <= creado < inicio+timedelta(minutes=30)
        assert len(r['contenido']) <= 280
        counts[(r['partido_referencia_h5'],r['pais'],r['ventana'])]+=1
    expected=list(csv.DictReader((folder/'datamart_conteos_esperados.csv').open(encoding='utf-8',newline='')))
    assert len(counts) == len(expected) == 128
    assert all(counts[(r['partido_referencia_h5'],r['pais'],r['ventana'])] == int(r['cantidad']) == 15 for r in expected)
    mapping=list(csv.DictReader((folder/'correspondencias_documentales.csv').open(encoding='utf-8',newline='')))
    assert len(mapping) == 8 and all(r['cassandra_h6'] == 'PENDIENTE' for r in mapping)
    for name,n in [('mongo_equipos_h10.jsonl',16),('mongo_jugadores_h10.jsonl',80)]:
        assert len([json.loads(s) for s in (folder/name).read_text(encoding='utf-8').splitlines()]) == n
    assert len((folder/'influx_muestra_h10.lp').read_text(encoding='utf-8').splitlines()) == 4800
    assert len(json.loads((folder/'iris_partidos_h10.json').read_text(encoding='utf-8'))) == 8
    print(json.dumps({'estado':'ARCHIVOS_VALIDOS_NO_INSERTADOS','archivos_con_hash':len(manifest['archivos']),'partidos_h5':32,'comentarios_propuestos':1920,'particiones_propuestas':128},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('carpeta',type=Path)
    validar(ap.parse_args().carpeta)
