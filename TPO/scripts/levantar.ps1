# Levanta todo el proyecto final: MongoDB (tres nodos), Neo4j, Redis y su réplica, Cassandra (dos regiones),
# InfluxDB, la API, Prometheus y Grafana. Uso, desde la carpeta TPO:  .\scripts\levantar.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Se creó .env a partir de .env.example. Completá MONGO_PASSWORD, NEO4J_PASSWORD, ADMIN_CLAVE, REDIS_PASSWORD y GRAFANA_PASSWORD y volvé a correr este script."
    exit 1
}
$faltan = "MONGO_PASSWORD", "NEO4J_PASSWORD", "ADMIN_CLAVE", "REDIS_PASSWORD", "GRAFANA_PASSWORD" | Where-Object {
    -not (Select-String -Path ".env" -Pattern "^$_=.+" -Quiet)
}
if ($faltan) {
    Write-Host "Faltan valores en .env: $($faltan -join ', '). Completalos y volvé a correr este script."
    exit 1
}

# Docker escribe su avance en la salida de error: en Windows PowerShell 5.1 eso no es una falla.
$ErrorActionPreference = "Continue"
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Esperando a la API y a las bases (Cassandra tarda un par de minutos la primera vez)..."
foreach ($intento in 1..120) {
    try {
        $salud = Invoke-RestMethod -Uri "http://127.0.0.1:8010/health/dependencias" -TimeoutSec 3
        $bases = "mongodb", "neo4j", "redis", "cassandra_america", "cassandra_europa"
        if (-not ($bases | Where-Object { $salud.$_.estado -ne "ok" })) {
            Write-Host "Listo."
            Write-Host "  Demostración: http://127.0.0.1:8010/demo/"
            Write-Host "  API:          http://127.0.0.1:8010/docs"
            Write-Host "  Grafana:      http://127.0.0.1:3001  (lectura sin ingresar; para editar, admin y GRAFANA_PASSWORD)"
            exit 0
        }
    } catch { }
    Start-Sleep -Seconds 2
}
Write-Host "La API no quedó lista. Revisar con: docker compose ps  y  docker compose logs api"
exit 1
