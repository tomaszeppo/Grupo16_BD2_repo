param([Parameter(Mandatory=$true)][string]$CarpetaCorrida)
$ErrorActionPreference = 'Stop'
$raizEntrada = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$destinoEntrada = (Resolve-Path -LiteralPath $CarpetaCorrida).Path
$permitidoEntrada = (Join-Path $raizEntrada 'resultados\optimizado') + [IO.Path]::DirectorySeparatorChar
if (-not $destinoEntrada.StartsWith($permitidoEntrada,[StringComparison]::OrdinalIgnoreCase)) { throw 'Usar carpeta de corrida preparada en resultados/optimizado' }
& (Join-Path $destinoEntrada '02_CARGAR.ps1')
