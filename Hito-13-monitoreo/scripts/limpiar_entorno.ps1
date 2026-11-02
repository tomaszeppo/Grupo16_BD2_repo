# Detiene los contenedores del monitoreo. No borra volúmenes, datos ni evidencia, y no toca las bases del Hito 10.
# Para volver a levantar: & .\scripts\iniciar_monitoreo.ps1
Set-Location (Split-Path -Parent $PSScriptRoot)
$archivosEnv = @('--env-file', '.env', '--env-file', '..\Hito-10-fixture2030-APIREST\.env')
docker compose @archivosEnv stop 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { throw "docker compose stop falló" }
Write-Host "Contenedores del monitoreo detenidos. Volúmenes prometheus_data y grafana_data conservados."
Write-Host "Las bases del Hito 10 siguen en marcha; para detenerlas sin perder datos ver su README (docker compose stop)."
