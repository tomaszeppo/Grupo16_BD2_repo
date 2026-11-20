# Detiene los contenedores del TPO. Los datos se conservan salvo que se pida borrarlos.
# Uso, desde la carpeta TPO:  .\scripts\limpiar.ps1            (detiene)
#                             .\scripts\limpiar.ps1 -BorrarDatos  (detiene y borra los volúmenes de este proyecto)
param([switch]$BorrarDatos)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if ($BorrarDatos) {
    docker compose --profile herramientas down --volumes
    # Volumen de la versión anterior con un solo nodo de Cassandra, si quedó.
    docker volume rm fixture2030-tpo_cassandra_datos 2>$null | Out-Null
} else {
    docker compose --profile herramientas down
}
