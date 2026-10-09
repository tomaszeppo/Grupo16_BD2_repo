#!/usr/bin/env bash
# cargar_y_validar.sh
# Carga masiva reproducible: vacia las tablas de comentarios, carga los CSV con
# COPY y valida el conteo por particion contra lo esperado. Con el argumento
# "dos" repite la carga una segunda vez y valida de nuevo (los totales no deben
# cambiar). Los CSV se generan antes con generar_carga_masiva.py.
#
# Uso (desde la carpeta del modulo, en bash/Git Bash):
#   bash scripts/cargar_y_validar.sh dos
# En PowerShell hay que pasar por bash.exe de Git, o correr los comandos
# del README uno por uno.

export MSYS_NO_PATHCONV=1
RED="${RED_COMPOSE:-$(basename "$PWD" | tr '[:upper:]' '[:lower:]')_default}"
OPCIONES="HEADER=true AND INGESTRATE=15000 AND MAXBATCHSIZE=10 AND NUMPROCESSES=3 AND MAXATTEMPTS=10"

cql() { docker exec fixture2030-cassandra cqlsh -e "$1"; }

validar() {
  docker run --rm --network "$RED" -v "$PWD/scripts:/scripts:ro" -v "$PWD/data:/data:ro" python:3.11-slim \
    sh -c "pip install -q cassandra-driver 2>/dev/null && python /scripts/validar_carga_masiva.py --host cassandra --datos /data"
}

cargar() {
  cql "COPY fixture2030.partidos_referencia (partido_codigo, fecha_inicio) FROM '/data/partidos_referencia.csv' WITH HEADER=true;"
  cql "COPY fixture2030.comentarios_por_partido (partido_codigo, bucket, comentario_id, usuario_id, contenido, creado_en, estado_moderacion, likes) FROM '/data/comentarios_por_partido.csv' WITH $OPCIONES;"
  cql "COPY fixture2030.comentarios_por_usuario (usuario_id, creado_en, comentario_id, partido_codigo, contenido, estado_moderacion) FROM '/data/comentarios_por_usuario.csv' WITH $OPCIONES;"
}

echo "=== Version ==="; cql "SHOW VERSION;"
if [ -z "$SALTEAR_CARGA_1" ]; then
  echo "=== Se vacian las tablas de comentarios (las de la carga de muestra no cuentan en la validacion) ==="
  cql "TRUNCATE fixture2030.comentarios_por_partido;"
  cql "TRUNCATE fixture2030.comentarios_por_usuario;"
  cql "TRUNCATE fixture2030.partidos_referencia;"
  echo "=== Carga 1 ==="; date
  cargar
  date
fi
echo "=== Validacion despues de la carga 1 ==="
validar

if [ "$1" = "dos" ]; then
  echo "=== Carga 2 (los mismos CSV, sin vaciar) ==="; date
  cargar
  date
  echo "=== Validacion despues de la carga 2 ==="
  validar
fi
