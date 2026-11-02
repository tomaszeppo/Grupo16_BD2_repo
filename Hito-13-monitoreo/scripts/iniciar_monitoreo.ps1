# Levanta la API instrumentada, Prometheus, Grafana y los exportadores.
# Requiere las bases del Hito 10 en marcha (red fixture2030_net). No toca sus contenedores ni volúmenes.
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    throw "Se creó .env desde .env.example. Completar GRAFANA_ADMIN_PASSWORD y volver a ejecutar."
}
if (-not (Test-Path '..\Hito-10-fixture2030-APIREST\.env')) {
    throw "Falta el .env del Hito 10. Seguir su README (scripts/levantar_servicios.sh) antes de este paso."
}
# docker escribe su progreso en stderr; en PowerShell 5.1 eso cortaría el script con 'Stop', así que se decide por el código de salida.
$ErrorActionPreference = 'Continue'
docker network inspect fixture2030_net *> $null
if ($LASTEXITCODE -ne 0) {
    throw "No existe la red fixture2030_net: levantar primero las bases del Hito 10."
}

# Las credenciales de MongoDB del exportador salen del .env del Hito 10; por eso van los dos archivos.
$archivosEnv = @('--env-file', '.env', '--env-file', '..\Hito-10-fixture2030-APIREST\.env')
docker compose @archivosEnv up -d --build 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { throw "docker compose up falló" }
$ErrorActionPreference = 'Stop'

Write-Host "Esperando que la API instrumentada responda en http://127.0.0.1:8001/health ..."
$listo = $false
foreach ($i in 1..30) {
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 'http://127.0.0.1:8001/health' | Out-Null
        $listo = $true; break
    } catch {
        # 503 (alguna base degradada) también indica que la API responde.
        if ($_.Exception.Response) { $listo = $true; break }
        Start-Sleep -Seconds 2
    }
}
if (-not $listo) { throw "La API instrumentada no respondió. Ver: docker logs fixture2030-monitoreo-api_metricas-1" }

Write-Host ""
Write-Host "API con métricas: http://127.0.0.1:8001/docs  (métricas en /metrics)"
Write-Host "Prometheus:       http://127.0.0.1:9090/targets"
Write-Host "Grafana:          http://127.0.0.1:3000  (usuario admin, contraseña en .env)"
Write-Host "Siguiente paso:   & .\scripts\verificar_targets.ps1"
