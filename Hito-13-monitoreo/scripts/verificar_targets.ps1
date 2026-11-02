# Lista los destinos de Prometheus con su estado y el último error. Sale con código 1 si alguno está DOWN.
# -Guardar escribe la respuesta completa en evidencia/prometheus_targets_<fecha>.json.
param([switch]$Guardar)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot

$resp = Invoke-RestMethod -TimeoutSec 10 'http://127.0.0.1:9090/api/v1/targets?state=active'
$destinos = $resp.data.activeTargets
$destinos | ForEach-Object {
    [pscustomobject]@{
        job        = $_.labels.job
        componente = $_.labels.componente
        estado     = $_.health
        ultimo     = $_.lastScrape
        duracion_s = [math]::Round([double]$_.lastScrapeDuration, 3)
        error      = $_.lastError
    }
} | Format-Table -AutoSize

# Disponibilidad de las seis bases vista desde la API (ping de /health en cada recolección).
$q = Invoke-RestMethod -TimeoutSec 10 'http://127.0.0.1:9090/api/v1/query?query=fixture2030_dependencia_disponible'
Write-Host "Disponibilidad por base (1 = responde):"
$q.data.result | ForEach-Object { Write-Host ("  {0,-10} {1}" -f $_.metric.fuente, $_.value[1]) }

if ($Guardar) {
    $carpeta = Join-Path $raiz 'evidencia'
    New-Item -ItemType Directory -Force $carpeta | Out-Null
    $fecha = Get-Date -Format 'yyyyMMdd_HHmmss'
    $salida = Join-Path $carpeta "prometheus_targets_$fecha.json"
    [pscustomobject]@{
        fecha_local    = (Get-Date).ToString('s')
        commit         = (git -C $raiz rev-parse --short HEAD)
        destinos       = $resp.data.activeTargets
        disponibilidad = $q.data.result
    } | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 $salida
    Write-Host "Guardado: $salida"
}

$caidos = @($destinos | Where-Object { $_.health -ne 'up' })
if ($caidos.Count -gt 0) {
    Write-Host "Destinos DOWN: $($caidos.labels.job -join ', '). Ver docs/inventario_de_componentes.md, sección 'Si un destino está DOWN'."
    exit 1
}
Write-Host "Todos los destinos están UP."
