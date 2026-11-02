# Ejecuta los momentos de la demo sobre la API instrumentada y guarda la evidencia en evidencia/.
#   -Momento pico    ráfaga de comentarios por país (3.000 a 50/s por defecto)
#   -Momento estado  P-03: Programado -> En juego -> Finalizado (no tiene vuelta atrás; ver README para repetir)
#   -Momento falla   detiene Redis 75 s con tráfico de fondo y lo vuelve a iniciar (no borra su volumen)
#   -Momento todo    los tres en orden y al final las capturas del panel de toda la ventana
param(
    [ValidateSet('pico', 'estado', 'falla', 'todo')][string]$Momento = 'todo',
    [int]$Cantidad = 3000,
    [double]$Tasa = 50,
    [string]$PartidoEstado = 'P-03'
)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$python = Join-Path $raiz '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw "Falta el entorno de Python: python -m venv .venv; .venv\Scripts\pip install -r requirements-scripts.txt"
}

function Paso($nombre, [string[]]$argumentos) {
    & $python scripts\prueba_controlada.py $nombre @argumentos
    if ($LASTEXITCODE -ne 0) { throw "Falló el momento $nombre" }
}

$desde = (Get-Date).ToUniversalTime().AddSeconds(-30).ToString('yyyy-MM-ddTHH:mm:ss+00:00')
if ($Momento -in 'pico', 'todo')   { Paso 'pico' @('--cantidad', $Cantidad, '--tasa', $Tasa) }
if ($Momento -eq 'todo')           { Start-Sleep -Seconds 20 }
if ($Momento -in 'estado', 'todo') { Paso 'estado' @('--partido-estado', $PartidoEstado) }
if ($Momento -in 'falla', 'todo')  { Paso 'falla' @() }
$hasta = (Get-Date).ToUniversalTime().AddSeconds(15).ToString('yyyy-MM-ddTHH:mm:ss+00:00')

Start-Sleep -Seconds 15
Paso 'capturar' @('--desde', $desde, '--hasta', $hasta, '--nombre', "demo_$(Get-Date -Format 'yyyyMMdd_HHmmss')_$Momento")
