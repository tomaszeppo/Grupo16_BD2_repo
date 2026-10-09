#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! docker compose ps --status running --services | grep -qx iris; then
  echo "ERROR: IRIS no está activo. Ejecutá bash scripts/01_inicializar.sh primero." >&2
  exit 1
fi

docker exec -i fixture2030-iris iris session IRIS <<'IRISCMDS'
Write !!,"=================================================",!
Write "PRUEBA RF5 - RECHAZO DE PROPIEDAD [Required]",!
Write "=================================================",!!

Set arbitro = ##class(Fixture.Arbitro).%New()
Set arbitro.Nombre = "Arbitro incompleto de prueba"
Set arbitro.Nacionalidad = "ARG"
Set arbitro.FechaNacimiento = $ZDateH("1985-01-01",3)
Set arbitro.Rol = "Asistente"
; Intencionalmente NO se asigna arbitro.Licencia, que esta definida como [Required].

Write "Objeto creado: Fixture.Arbitro",!
Write "Nombre=",arbitro.Nombre," | Rol=",arbitro.Rol,!
Write "Licencia: OMITIDA intencionalmente (propiedad [Required]).",!
Set sc = arbitro.%Save()
Write "Error al guardar (1 significa que IRIS rechazo el objeto): ",$System.Status.IsError(sc),!
If $System.Status.IsError(sc) Do $System.Status.DisplayError(sc)
If $System.Status.IsError(sc) Write "PRUEBA PASADA: IRIS rechazo el objeto por una propiedad obligatoria ausente.",!
If '$System.Status.IsError(sc) Write "PRUEBA FALLIDA: IRIS acepto un arbitro sin Licencia; revisar la definicion.",!
Write !!
Halt
IRISCMDS
