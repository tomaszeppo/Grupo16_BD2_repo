# Repite todas las mediciones de rendimiento. Tarda unos 15 minutos y BORRA los datos de laboratorio al empezar.
# Uso, desde la carpeta TPO:  .\scripts\medir.ps1
#                             .\scripts\medir.ps1 -Usuarios 50000 -Duracion 20
# Cada corrida deja su evidencia en evidencia\. Para que los números sean comparables conviene no tener
# otros contenedores pesados corriendo al mismo tiempo.
param([int]$Usuarios = 100000, [int]$UsuariosChico = 20000, [int]$Duracion = 30)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$env:COMMIT = (git rev-parse --short HEAD 2>$null)
if (-not $env:COMMIT) { $env:COMMIT = "sin commit" }

function Herramienta { docker compose run --rm herramientas @args; if ($LASTEXITCODE -ne 0) { throw "Falló: $args" } }
function Esperar-Api {
    foreach ($i in 1..60) {
        try { Invoke-RestMethod "http://127.0.0.1:8010/health" -TimeoutSec 2 | Out-Null; return } catch { Start-Sleep 1 }
    }
    throw "La API no respondió."
}

Write-Host "== Preparación =="
Herramienta python -m seed.run --reiniciar --dias-hasta-inicio 3
Herramienta python -m carga.poblar --usuarios $UsuariosChico --partidos P-06
Herramienta python -m carga.poblar --usuarios $Usuarios --partidos P-05

Write-Host "== 1. Pico de pronósticos (tres niveles de concurrencia) =="
foreach ($c in 10, 50, 200) {
    Herramienta python -m carga.ejecutar pico_pronosticos --usuarios $Usuarios --concurrencia $c --duracion $Duracion --etiqueta "c$c"
}

Write-Host "== 2. Lecturas del fixture en Neo4j =="
foreach ($c in 10, 50, 200) {
    Herramienta python -m carga.ejecutar lecturas_fixture --concurrencia $c --duracion $Duracion --etiqueta "c$c"
}

Write-Host "== 3. Pronósticos y lecturas a la vez =="
Herramienta python -m carga.ejecutar pico_mixto --usuarios $Usuarios --concurrencia 50 --duracion $Duracion

Write-Host "== 4. Cierre de partido con dos volúmenes de pronósticos =="
Herramienta python -m carga.ejecutar cierre_partido --partido P-06 --etiqueta "${UsuariosChico}_pronosticos"
Herramienta python -m carga.ejecutar cierre_partido --partido P-05 --etiqueta "${Usuarios}_pronosticos"
Herramienta python -m scripts.recalcular_puntajes

Write-Host "== 5. Puesto en el ranking leyendo de MongoDB =="
foreach ($c in 10, 50) {
    Herramienta python -m carga.ejecutar posicion_ranking --usuarios $Usuarios --concurrencia $c --duracion $Duracion --etiqueta "c$c"
}

Write-Host "== 5 bis. Escrituras directas a MongoDB, sin la API =="
Herramienta python -m carga.diagnostico_mongo --hilos 50 --segundos 10

Write-Host "== 6. Pronósticos sin la copia del calendario (cada pedido consulta Neo4j) =="
$env:CALENDARIO_TTL_SEGUNDOS = "0"
docker compose up -d api | Out-Null
Esperar-Api
Herramienta python -m carga.ejecutar pico_pronosticos --usuarios $Usuarios --concurrencia 50 --duracion $Duracion --etiqueta "sin_copia_del_calendario"
Remove-Item Env:CALENDARIO_TTL_SEGUNDOS
docker compose up -d api | Out-Null
Esperar-Api

Write-Host "== 7. La API con 4 CPU y 4 procesos =="
$env:API_CPUS = "4.0"; $env:API_PROCESOS = "4"
docker compose up -d api | Out-Null
Esperar-Api
foreach ($c in 50, 200) {
    Herramienta python -m carga.ejecutar pico_pronosticos --usuarios $Usuarios --concurrencia $c --duracion $Duracion --etiqueta "c${c}_api_4cpu_4procesos"
    Herramienta python -m carga.ejecutar lecturas_fixture --concurrencia $c --duracion $Duracion --etiqueta "c${c}_api_4cpu_4procesos"
}
Remove-Item Env:API_CPUS; Remove-Item Env:API_PROCESOS
docker compose up -d api | Out-Null
Esperar-Api

Write-Host "Listo. Las pruebas de falla se corren aparte:  .\scripts\prueba_de_falla.ps1 primario   y   .\scripts\prueba_de_falla.ps1 neo4j -Brusco"
