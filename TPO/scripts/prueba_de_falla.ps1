# Falla controlada durante una carga de pronósticos. Detiene un contenedor del TPO, espera y lo vuelve a levantar.
# No borra datos ni volúmenes.
# Uso, desde la carpeta TPO:  .\scripts\prueba_de_falla.ps1 primario           (apaga con orden el primario de MongoDB)
#                             .\scripts\prueba_de_falla.ps1 primario -Brusco   (lo mata sin aviso, como un corte)
#                             .\scripts\prueba_de_falla.ps1 neo4j -Brusco      (mata Neo4j)
#                             .\scripts\prueba_de_falla.ps1 europa -Brusco -Partido P-10
#                                 (mata la región Europa de Cassandra durante un partido en vivo con espectadores;
#                                  al final compara cuántos comentarios tiene cada región)
# Apagar con orden y cortar de golpe no son lo mismo: en el primer caso MongoDB traspasa el mando antes de salir.
param(
    [Parameter(Mandatory = $true)][ValidateSet("primario", "neo4j", "europa")][string]$Que,
    [switch]$Brusco, [int]$Usuarios = 100000, [int]$Concurrencia = 20,
    [int]$Duracion = 90, [int]$SegundoDeLaFalla = 30, [int]$SegundosCaido = 30,
    [string]$Partido = "P-10", [int]$Espectadores = 500
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
} elseif ($Que -eq "europa") {
    $servicio = "cassandra_europa"
    # El partido arranca después de abrir las conexiones (5 s + 1 s cada 500 espectadores): se corre la falla
    # para que caiga cerca del minuto $SegundoDeLaFalla del partido.
    $SegundoDeLaFalla = $SegundoDeLaFalla + 5 + [math]::Ceiling($Espectadores / 500)
} else {
    # El primario puede ser cualquiera de los tres: se le pregunta al conjunto.
    $primario = docker compose exec -T mongo2 mongosh --quiet -u $env:MONGO_USER -p $env:MONGO_PASSWORD --authenticationDatabase admin --eval "rs.status().members.find(m => m.stateStr === 'PRIMARY').name"
    $servicio = ($primario -split ":")[0].Trim()
}
$accion = if ($Brusco) { "kill" } else { "stop" }
$etiqueta = if ($Brusco) { "${Que}_corte_brusco" } else { $Que }
$como = if ($Brusco) { "Se mató sin aviso (docker compose kill)" } else { "Se apagó con orden (docker compose stop)" }
Write-Host "'$servicio': $como cerca del segundo $SegundoDeLaFalla; se lo levanta $SegundosCaido segundos después."
# De acá en adelante, docker escribe avisos en la salida de error: en Windows PowerShell 5.1 eso no es una falla.
$ErrorActionPreference = "Continue"

if ($Que -eq "europa") {
    $carga = Start-Job -ScriptBlock {
        param($carpeta, $espectadores, $partido, $etiqueta, $servicio, $segundo, $caido, $como)
        Set-Location $carpeta
        docker compose run --rm herramientas python -m carga.ejecutar vivo --espectadores $espectadores --partido $partido `
            --comentan 0.1 --etiqueta $etiqueta `
            --nota "$como el contenedor $servicio cerca del segundo $segundo de la corrida y se lo volvió a levantar $caido segundos después."
    } -ArgumentList (Get-Location).Path, $Espectadores, $Partido, "cassandra_$etiqueta", $servicio, $SegundoDeLaFalla, $SegundosCaido, $como
} else {
    $carga = Start-Job -ScriptBlock {
        param($carpeta, $usuarios, $concurrencia, $duracion, $etiqueta, $servicio, $segundo, $caido, $como)
        Set-Location $carpeta
        docker compose run --rm herramientas python -m carga.ejecutar caida --usuarios $usuarios --concurrencia $concurrencia `
            --duracion $duracion --etiqueta $etiqueta `
            --nota "$como el contenedor $servicio cerca del segundo $segundo y se lo volvió a levantar $caido segundos después."
    } -ArgumentList (Get-Location).Path, $Usuarios, $Concurrencia, $Duracion, $etiqueta, $servicio, $SegundoDeLaFalla, $SegundosCaido, $como
}

Start-Sleep -Seconds ($SegundoDeLaFalla + 3)   # el contenedor de herramientas tarda unos segundos en arrancar
Write-Host "$(Get-Date -Format HH:mm:ss) deteniendo $servicio"
docker compose $accion $servicio | Out-Null
Start-Sleep -Seconds $SegundosCaido
Write-Host "$(Get-Date -Format HH:mm:ss) levantando $servicio"
docker compose start $servicio | Out-Null

Receive-Job $carga -Wait | Select-Object -Last 3
Remove-Job $carga

if ($Que -eq "europa") {
    # Cada región tiene que tener todos los comentarios del partido: lo escrito en América durante el corte le
    # llega a Europa al volver (hinted handoff). Se cuenta en cada nodo leyendo SOLO su copia (LOCAL_ONE).
    while ((docker compose ps $servicio --format "{{.Status}}") -notmatch "healthy") { Start-Sleep 2 }
    Start-Sleep 20
    $consulta = "CONSISTENCY LOCAL_ONE; SELECT pais, count(*) FROM fixture2030.comentarios_por_partido_pais WHERE partido_id = '$Partido' GROUP BY partido_id, pais, ventana ALLOW FILTERING;"
    $salida = "evidencia\cassandra_${etiqueta}_$(Get-Date -Format yyyyMMdd_HHmmss)_conteo_por_region.txt"
    "Comentarios del partido $Partido contados en cada región, leyendo solo su copia (commit $env:COMMIT)." | Out-File $salida -Encoding utf8
    foreach ($nodo in "cassandra_america", "cassandra_europa") {
        "`n== $nodo ==" | Out-File $salida -Append -Encoding utf8
        docker compose exec -T $nodo cqlsh -e $consulta | Out-File $salida -Append -Encoding utf8
    }
    Get-Content $salida
}
Write-Host "La línea de tiempo por segundo queda en el resumen de la corrida (campo linea_de_tiempo)."
