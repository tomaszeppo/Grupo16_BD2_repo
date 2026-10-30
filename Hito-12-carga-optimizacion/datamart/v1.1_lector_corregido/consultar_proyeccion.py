"""Lector corregido: consulta una proyeccion existente, validada, en modo solo lectura."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


def separar_consultas(texto):
    """SQLite reconoce los terminadores sin confundirlos con comentarios o literales."""
    pendiente = ''
    for caracter in texto:
        pendiente += caracter
        if caracter == ';' and sqlite3.complete_statement(pendiente):
            yield pendiente
            pendiente = ''
    # Se admiten comentarios/vacios al final, pero no consultas incompletas.
    if any(linea.strip() and not linea.lstrip().startswith('--') for linea in pendiente.splitlines()):
        raise ValueError('Consulta SQL incompleta: falta terminador')


def consultar(db, texto):
    for consulta in separar_consultas(texto):
        cursor = db.execute(consulta)
        if cursor.description is None:
            continue
        yield [columna[0] for columna in cursor.description], cursor.fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('carpeta', type=Path)
    args = parser.parse_args()
    validacion = json.loads((args.carpeta/'validacion.json').read_text(encoding='utf-8'))
    ruta = args.carpeta/'actividad.sqlite'
    if validacion['estado'] != 'VALIDADO' or hashlib.sha256(ruta.read_bytes()).hexdigest() != validacion['sqlite_sha256']:
        raise ValueError('Proyeccion sin validacion o modificada')
    consultas = Path(__file__).with_name('consultas.sql').read_text(encoding='utf-8')
    db = sqlite3.connect(ruta.resolve().as_uri()+'?mode=ro', uri=True)
    try:
        for columnas, filas in consultar(db, consultas):
            print(' | '.join(columnas))
            for fila in filas:
                print(' | '.join(map(str, fila)))
            print()
    finally:
        db.close()


if __name__ == '__main__':
    main()
