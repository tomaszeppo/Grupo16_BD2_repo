# Falla controlada durante una carga de pronósticos. Detiene un contenedor del TPO, espera y lo vuelve a levantar.
# No borra datos ni volúmenes.
# Uso, desde la carpeta TPO:  .\scripts\prueba_de_falla.ps1 primario           (apaga con orden el primario de MongoDB)
#                             .\scripts\prueba_de_falla.ps1 primario -Brusco   (lo mata sin aviso, como un corte)
#                             .\scripts\prueba_de_falla.ps1 neo4j -Brusco      (mata Neo4j)
# Apagar con orden y cortar de golpe no son lo mismo: en el primer caso MongoDB traspasa el mando antes de salir.
param(
    [Parameter(Mandatory = $true)][ValidateSet("primario", "neo4j")][string]$Que,
    [switch]$Brusco, [int]$Usuarios = 100000, [int]$Concurrencia = 20,
    [int]$Duracion = 90, [int]$SegundoDeLaFalla = 30, [int]$SegundosCaido = 30
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
Get-Content .env | Where-Object { $_ -match "^(MONGO_USER|MONGO_PASSWORD)=" } | ForEach-Object {
    $par = $_ -split "=", 2; Set-Item "Env:$($par[0])" $par[1]
}
$env:COMMIT = (git rev-parse --short HEAD 2>$null)
if (-not $env:COMMIT) { $env:COMMIT = "sin commit" }

if ($Que -eq "neo4j") {
    $servicio = "neo4j"
} else {
    # El primario puede ser cualquiera de los tres: se le pregunta al conjunto.
    $primario = docker compose exec -T mongo2 mongosh --quiet -u $env:MONGO_USER -p $env:MONGO_PASSWORD --authenticationDatabase admin --eval "rs.status().members.find(m => m.stateStr === 'PRIMARY').name"
    $servicio = ($primario -split ":")[0].Trim()
}
$accion = if ($Brusco) { "kill" } else { "stop" }
$etiqueta = if ($Brusco) { "${Que}_corte_brusco" } else { $Que }
$como = if ($Brusco) { "Se mató sin aviso (docker compose kill)" } else { "Se apagó con orden (docker compose stop)" }
Write-Host "'$servicio': $como cerca del segundo $SegundoDeLaFalla; se lo levanta $SegundosCaido segundos después."

$carga = Start-Job -ScriptBlock {
    param($carpeta, $usuarios, $concurrencia, $duracion, $etiqueta, $servicio, $segundo, $caido, $como)
    Set-Location $carpeta
    docker compose run --rm herramientas python -m carga.ejecutar caida --usuarios $usuarios --concurrencia $concurrencia `
        --duracion $duracion --etiqueta $etiqueta `
        --nota "$como el contenedor $servicio cerca del segundo $segundo y se lo volvió a levantar $caido segundos después."
} -ArgumentList (Get-Location).Path, $Usuarios, $Concurrencia, $Duracion, $etiqueta, $servicio, $SegundoDeLaFalla, $SegundosCaido, $como

Start-Sleep -Seconds ($SegundoDeLaFalla + 3)   # el contenedor de herramientas tarda unos segundos en arrancar
Write-Host "$(Get-Date -Format HH:mm:ss) deteniendo $servicio"
docker compose $accion $servicio | Out-Null
Start-Sleep -Seconds $SegundosCaido
Write-Host "$(Get-Date -Format HH:mm:ss) levantando $servicio"
docker compose start $servicio | Out-Null

Receive-Job $carga -Wait | Select-Object -Last 3
Remove-Job $carga
Write-Host "La línea de tiempo por segundo queda en el resumen de la corrida (campo linea_de_tiempo)."
