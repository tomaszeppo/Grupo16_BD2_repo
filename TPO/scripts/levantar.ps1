# Levanta MongoDB (tres nodos), Neo4j y la API. Uso, desde la carpeta TPO:  .\scripts\levantar.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Se creó .env a partir de .env.example. Completá MONGO_PASSWORD, NEO4J_PASSWORD y ADMIN_CLAVE y volvé a correr este script."
    exit 1
}

docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Esperando a la API..."
foreach ($intento in 1..60) {
    try {
        $salud = Invoke-RestMethod -Uri "http://127.0.0.1:8010/health/dependencias" -TimeoutSec 3
        if ($salud.mongodb.estado -eq "ok" -and $salud.neo4j.estado -eq "ok") {
            Write-Host "Listo. API: http://127.0.0.1:8010/docs   Demostración: http://127.0.0.1:8010/demo/"
            exit 0
        }
    } catch { }
    Start-Sleep -Seconds 2
}
Write-Host "La API no quedó lista. Revisar con: docker compose ps  y  docker compose logs api"
exit 1
