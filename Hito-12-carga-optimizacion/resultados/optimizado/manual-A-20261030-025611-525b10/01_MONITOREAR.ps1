Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$c = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'corrida.json') -Raw | ConvertFrom-Json
Set-Location -LiteralPath $c.raiz
$recolector = Join-Path $c.raiz "$($c.version)/scripts/registrar_base.py"

Write-Host "Monitoreando $($c.corrida). Ahora deja esta consola abierta y ejecuta 02_CARGAR en la otra."
& python $recolector recursos --perfil $c.perfil --cliente $c.cliente --salida (Join-Path $c.salida 'recursos.jsonl')
if ($LASTEXITCODE -ne 0) { throw 'El monitor termino con error. Revisa la salida.' }
