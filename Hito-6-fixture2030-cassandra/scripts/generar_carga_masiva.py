#!/usr/bin/env python3
"""
generar_carga_masiva.py

Genera los archivos CSV para cargar un volumen grande de comentarios
(objetivo: mas de 1.000.000) mediante COPY FROM en cqlsh. No se conecta a
Cassandra: solo genera los archivos. La carga real se hace despues, con los
comandos COPY que quedan documentados al final de la corrida y en el README.

Es reproducible: usa una semilla fija y el comentario_id sale de la hora del
comentario y de un contador de fila, no de la hora de la corrida. Generar dos
veces produce archivos identicos, y cargar dos veces con COPY sobrescribe las
mismas filas en lugar de duplicarlas.

Ademas de los CSV a cargar, escribe los conteos esperados por particion
(conteo_esperado_por_particion.csv y conteo_esperado_por_usuario.csv) para que
validar_carga_masiva.py los compare contra Cassandra.

Uso:
    python3 generar_carga_masiva.py --target-rows 1200000 --output-dir ../data

Para probar la logica en chico antes de generar el volumen completo:
    python3 generar_carga_masiva.py --target-rows 2000 --output-dir /tmp/prueba
"""

import argparse
import csv
import datetime
import random
import time
import uuid
from collections import Counter
from pathlib import Path

# Mismos 32 partidos y mismas fechas que scripts/carga.cypher del Hito 5
# (P-01 = 2030-06-08, un partido por dia).
CANTIDAD_PARTIDOS = 32
FECHA_BASE = datetime.date(2030, 6, 8)
DURACION_PARTIDO_MIN = 130  # 90 + descuento + entretiempo, con margen
TAMANIO_BUCKET_MIN = 10
SEMILLA_POR_DEFECTO = 2030

FRASES = [
    "Que partidazo, vamos que se puede", "Ese offside estuvo re dudoso",
    "Necesitamos un cambio ya", "El arquero salvo todo",
    "Increible la jugada por izquierda", "Hay que cerrar mas atras",
    "Merecido el gol, se lo veia venir", "Arbitro vendido",
    "Que nivel el mediocampo hoy", "Falta clara y no cobro nada",
    "Vamos que todavia hay tiempo", "Grandisima atajada",
    "Este equipo no se rinde nunca", "Mal el cambio, no lo entendi",
    "Partido durisimo, mucha intensidad", "Ahi esta el gol que faltaba",
    "Penal como una casa", "Se les escapa el partido",
    "Que control, que categoria", "Final de infarto esto",
]


# Inicio del calendario gregoriano, que es el origen de la marca de tiempo
# de un UUID version 1 (en intervalos de 100 nanosegundos).
_ORIGEN_UUID1 = datetime.datetime(1582, 10, 15)
_BIT_MULTICAST = 0x010000000000  # el "nodo" es inventado, no una MAC real


def timeuuid_desde(momento: datetime.datetime, contador: int) -> uuid.UUID:
    """Arma un timeuuid (UUID v1) estable a partir de `momento` y del numero de fila.

    uuid.uuid1() usaria la hora en que corre el script y valores al azar:
    cada corrida produciria ids distintos y recargar duplicaria filas. Aca la
    marca de tiempo es la de `momento` (el orden de clustering coincide con
    la hora real del comentario) y el contador de fila ocupa la secuencia de
    reloj y el nodo, asi dos filas con la misma hora tienen ids distintos y
    la misma fila siempre tiene el mismo id."""
    ts = (momento - _ORIGEN_UUID1) // datetime.timedelta(microseconds=1) * 10
    clock_seq = contador & 0x3FFF
    nodo = ((contador >> 14) & 0xFFFFFFFFFF) | _BIT_MULTICAST
    return uuid.UUID(fields=(
        ts & 0xFFFFFFFF,
        (ts >> 32) & 0xFFFF,
        ((ts >> 48) & 0x0FFF) | 0x1000,
        (clock_seq >> 8) | 0x80,
        clock_seq & 0xFF,
        nodo,
    ))


def formato_cqlsh(momento: datetime.datetime) -> str:
    """Timestamp en el formato que entiende COPY FROM de cqlsh.

    Ojo: con el formato ISO de isoformat() ('2030-06-08T18:00:41.896710'),
    COPY en Cassandra 5 se queda solo con la fecha y guarda 00:00:00, sin
    avisar nada. Con espacio en vez de 'T', milisegundos y zona horaria
    explicita lo toma bien (verificado contra el contenedor)."""
    return momento.strftime("%Y-%m-%d %H:%M:%S.") + f"{momento.microsecond // 1000:03d}+0000"


def partidos_referencia():
    partidos = []
    for n in range(1, CANTIDAD_PARTIDOS + 1):
        codigo = f"P-{n:02d}"
        fecha = FECHA_BASE + datetime.timedelta(days=n - 1)
        kickoff = datetime.datetime.combine(fecha, datetime.time(18, 0, 0))
        partidos.append((codigo, kickoff))
    return partidos


def distribucion_de_volumen(partidos, target_rows):
    """5 partidos 'populares' concentran el 70% del volumen; el resto se
    reparte parejo entre los otros 27. Asi se prueba la logica de bucket
    justo donde mas hace falta: los partidos con mas trafico."""
    populares = set(p[0] for p in partidos[:5])
    volumen_populares = int(target_rows * 0.70)
    volumen_resto = target_rows - volumen_populares

    reparto = {}
    for codigo, _ in partidos:
        if codigo in populares:
            reparto[codigo] = volumen_populares // len(populares)
        else:
            reparto[codigo] = volumen_resto // (len(partidos) - len(populares))
    return reparto


def generar(target_rows: int, output_dir: Path, cantidad_usuarios: int, semilla: int):
    output_dir.mkdir(parents=True, exist_ok=True)
    azar = random.Random(semilla)
    partidos = partidos_referencia()
    reparto = distribucion_de_volumen(partidos, target_rows)

    ruta_ref = output_dir / "partidos_referencia.csv"
    ruta_partido = output_dir / "comentarios_por_partido.csv"
    ruta_usuario = output_dir / "comentarios_por_usuario.csv"
    ruta_esp_particion = output_dir / "conteo_esperado_por_particion.csv"
    ruta_esp_usuario = output_dir / "conteo_esperado_por_usuario.csv"
    esperado_por_particion = {}
    esperado_por_usuario = Counter()

    with ruta_ref.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["partido_codigo", "fecha_inicio"])
        for codigo, kickoff in partidos:
            w.writerow([codigo, formato_cqlsh(kickoff)])

    inicio = time.time()
    total_escrito = 0
    max_filas_por_bucket = 0

    with ruta_partido.open("w", newline="", encoding="utf-8") as fp, \
         ruta_usuario.open("w", newline="", encoding="utf-8") as fu:
        wp = csv.writer(fp)
        wu = csv.writer(fu)
        wp.writerow(["partido_codigo", "bucket", "comentario_id", "usuario_id",
                     "contenido", "creado_en", "estado_moderacion", "likes"])
        wu.writerow(["usuario_id", "creado_en", "comentario_id",
                     "partido_codigo", "contenido", "estado_moderacion"])

        cantidad_buckets = DURACION_PARTIDO_MIN // TAMANIO_BUCKET_MIN

        for codigo, kickoff in partidos:
            filas_partido = reparto[codigo]
            if filas_partido == 0:
                continue
            filas_por_bucket = filas_partido // cantidad_buckets
            max_filas_por_bucket = max(max_filas_por_bucket, filas_por_bucket)

            for bucket in range(cantidad_buckets):
                for _ in range(filas_por_bucket):
                    minuto = bucket * TAMANIO_BUCKET_MIN + azar.uniform(0, TAMANIO_BUCKET_MIN)
                    creado_en = kickoff + datetime.timedelta(minutes=minuto)
                    # Cassandra guarda timestamp con precision de milisegundos:
                    # se trunca aca para que creado_en y la hora del timeuuid
                    # queden exactamente iguales en la base.
                    creado_en = creado_en.replace(microsecond=creado_en.microsecond // 1000 * 1000)
                    cid = timeuuid_desde(creado_en, total_escrito)
                    usuario = f"user-{azar.randint(1, cantidad_usuarios):06d}"
                    contenido = azar.choice(FRASES)
                    estado = "reportado" if azar.random() < 0.01 else "visible"
                    likes = azar.randint(0, 50)

                    wp.writerow([codigo, bucket, cid, usuario, contenido,
                                 formato_cqlsh(creado_en), estado, likes])
                    wu.writerow([usuario, formato_cqlsh(creado_en), cid,
                                 codigo, contenido, estado])
                    esperado_por_usuario[usuario] += 1
                    total_escrito += 1
                esperado_por_particion[(codigo, bucket)] = filas_por_bucket

    with ruta_esp_particion.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["partido_codigo", "bucket", "filas_esperadas"])
        for (codigo, bucket), filas in esperado_por_particion.items():
            w.writerow([codigo, bucket, filas])
    with ruta_esp_usuario.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["usuario_id", "filas_esperadas"])
        for usuario in sorted(esperado_por_usuario):
            w.writerow([usuario, esperado_por_usuario[usuario]])

    elapsed = time.time() - inicio
    print(f"Filas generadas: {total_escrito}")
    print(f"Tiempo de generacion: {elapsed:.1f}s ({total_escrito/elapsed:.0f} filas/seg)")
    print(f"Maximo de filas en un mismo bucket (una sola particion): {max_filas_por_bucket}")
    print(f"Particiones esperadas: {len(esperado_por_particion)} (partido, bucket) y {len(esperado_por_usuario)} usuarios")
    print(f"Semilla: {semilla}")
    print(f"Archivos en: {output_dir}")
    print()
    # cqlsh corre adentro del contenedor, asi que la ruta del CSV tiene que
    # ser la del montaje (/data), no la del host. Esto asume que se genero
    # en la carpeta data/ del proyecto (la que monta el docker-compose.yml).
    print("Para cargar con cqlsh (COPY no valida el esquema, correr esquema.cql antes).")
    print("Se puede ejecutar mas de una vez: los ids son estables, la segunda carga sobrescribe.")
    print("Despues, validar con validar_carga_masiva.py (conteo por particion contra el esperado).")
    # Las dos tablas grandes van con un ritmo mas moderado que el de COPY por
    # defecto. Con los valores por defecto, en un nodo unico de Docker
    # Desktop, comentarios_por_usuario se saturo (el CSV no viene ordenado
    # por usuario_id, asi que cada batch toca muchas particiones distintas):
    # WriteTimeout en cadena y COPY abortando con ~65.000 filas sin cargar.
    # La tabla principal aguanto mejor pero tambien tuvo algunos timeouts
    # durante pausas largas del recolector de basura de Java.
    opciones = "HEADER=true AND INGESTRATE=15000 AND MAXBATCHSIZE=10 AND NUMPROCESSES=3 AND MAXATTEMPTS=10"
    print("Las rutas /data/... son las de adentro del contenedor:")
    print(f"  docker exec fixture2030-cassandra cqlsh -e \"COPY fixture2030.partidos_referencia "
          f"(partido_codigo, fecha_inicio) FROM '/data/{ruta_ref.name}' WITH HEADER=true;\"")
    print(f"  docker exec fixture2030-cassandra cqlsh -e \"COPY fixture2030.comentarios_por_partido "
          f"(partido_codigo, bucket, comentario_id, usuario_id, contenido, creado_en, "
          f"estado_moderacion, likes) FROM '/data/{ruta_partido.name}' WITH {opciones};\"")
    print(f"  docker exec fixture2030-cassandra cqlsh -e \"COPY fixture2030.comentarios_por_usuario "
          f"(usuario_id, creado_en, comentario_id, partido_codigo, contenido, estado_moderacion) "
          f"FROM '/data/{ruta_usuario.name}' WITH {opciones};\"")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-rows", type=int, default=1_200_000,
                         help="Cantidad total de comentarios a generar (default: 1.200.000)")
    parser.add_argument("--output-dir", type=str, default="../data",
                         help="Carpeta donde escribir los CSV (default: ../data)")
    parser.add_argument("--usuarios", type=int, default=50_000,
                         help="Cantidad de usuarios distintos a repartir entre los comentarios")
    parser.add_argument("--semilla", type=int, default=SEMILLA_POR_DEFECTO,
                         help="Semilla del generador al azar (default: %d)" % SEMILLA_POR_DEFECTO)
    args = parser.parse_args()
    generar(args.target_rows, Path(args.output_dir), args.usuarios, args.semilla)
