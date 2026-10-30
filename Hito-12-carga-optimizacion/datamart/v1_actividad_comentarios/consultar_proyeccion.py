"""Consulta de solo lectura sobre una proyeccion local validada."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('carpeta',type=Path)
    args=parser.parse_args()
    validacion=json.loads((args.carpeta/'validacion.json').read_text(encoding='utf-8'))
    ruta=args.carpeta/'actividad.sqlite'
    if validacion['estado']!='VALIDADO' or hashlib.sha256(ruta.read_bytes()).hexdigest()!=validacion['sqlite_sha256']:
        raise ValueError('Proyeccion sin validacion o modificada')
    db=sqlite3.connect(ruta.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        consultas=Path(__file__).with_name('consultas.sql').read_text(encoding='utf-8')
        for consulta in consultas.split(';'):
            if not consulta.strip():continue
            cursor=db.execute(consulta)
            print(' | '.join(c[0] for c in cursor.description))
            for fila in cursor:print(' | '.join(map(str,fila)))
            print()
    finally:db.close()


if __name__=='__main__':main()
