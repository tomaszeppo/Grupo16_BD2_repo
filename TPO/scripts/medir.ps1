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

# Docker escribe su avance en la salida de error: en Windows PowerShell 5.1 eso no es una falla. Las fallas de
# verdad se detectan por el código de salida.
$ErrorActionPreference = "Continue"
function Herramienta { docker compose run --rm herramientas @args; if ($LASTEXITCODE -ne 0) { throw "Falló: $args" } }
function Esperar-Api {
    foreach ($i in 1..60) {
        try { Invoke-RestMethod "http://127.0.0.1:8010/health" -TimeoutSec 2 | Out-Null; return } catch { Start-Sleep 1 }
    }
    throw "La API no respondió."
}
function Esperar-Ranking {
    foreach ($i in 1..120) {
        try { Invoke-RestMethod "http://127.0.0.1:8010/ranking?limit=1" -TimeoutSec 15 | Out-Null; return } catch { Start-Sleep 2 }
    }
    throw "El ranking no respondió."
}

Write-Host "== Preparación =="
Herramienta python -m seed.run --reiniciar --dias-hasta-inicio 3
Herramienta python -m carga.poblar --usuarios $UsuariosChico --partidos P-06
Herramienta python -m carga.poblar --usuarios $Usuarios --partidos P-05
Herramienta python -m carga.poblar --usuarios $UsuariosChico --partidos P-12
Herramienta python -m carga.poblar --usuarios $Usuarios --partidos P-11

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

Write-Host "== 4. Cierre de partido y ranking por MongoDB (REDIS_ENABLED=false), para comparar =="
# Va antes que el de Redis: así, cuando Redis arma su ranking por primera vez, ya toma estos puntajes de MongoDB.
$env:REDIS_ENABLED = "false"
docker compose up -d api | Out-Null
Esperar-Api
Herramienta python -m carga.ejecutar cierre_partido --partido P-12 --etiqueta "${UsuariosChico}_pronosticos_mongodb"
Herramienta python -m carga.ejecutar cierre_partido --partido P-11 --etiqueta "${Usuarios}_pronosticos_mongodb"
foreach ($c in 10, 50) {
    Herramienta python -m carga.ejecutar posicion_ranking --usuarios $Usuarios --concurrencia $c --duracion $Duracion --etiqueta "c${c}_mongodb"
}
Remove-Item Env:REDIS_ENABLED
docker compose up -d api | Out-Null
Esperar-Api

Write-Host "== 5. Cierre de partido y ranking por Redis (lo que levanta Compose) =="
Esperar-Ranking  # la primera consulta arma el ranking de Redis desde MongoDB: no es parte de lo que se mide
Herramienta python -m carga.ejecutar cierre_partido --partido P-06 --etiqueta "${UsuariosChico}_pronosticos_redis"
Herramienta python -m carga.ejecutar cierre_partido --partido P-05 --etiqueta "${Usuarios}_pronosticos_redis"
Herramienta python -m scripts.recalcular_puntajes
foreach ($c in 10, 50) {
    Herramienta python -m carga.ejecutar posicion_ranking --usuarios $Usuarios --concurrencia $c --duracion $Duracion --etiqueta "c${c}_redis"
}

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

Write-Host "== 8. Partido en vivo: espectadores con la conexión abierta y comentarios =="
# Cada nivel usa un partido distinto (una simulación terminada no se repite). Los usuarios ya los creó la preparación.
Herramienta python -m carga.ejecutar vivo --espectadores 500 --comentan 0.05 --partido P-07 --etiqueta "500_espectadores"
Herramienta python -m carga.ejecutar vivo --espectadores 1000 --comentan 0.05 --partido P-08 --etiqueta "1000_espectadores"
Herramienta python -m carga.ejecutar vivo --espectadores 2000 --comentan 0.05 --partido P-09 --etiqueta "2000_espectadores"

Write-Host "== 9. Atraso de la réplica de Redis =="
Herramienta python -m scripts.medir_replica_redis --muestras 1000

Write-Host "Listo. Las pruebas de falla se corren aparte:  .\scripts\prueba_de_falla.ps1 primario,  .\scripts\prueba_de_falla.ps1 neo4j -Brusco  y  .\scripts\prueba_de_falla.ps1 europa -Brusco -Partido P-10"
