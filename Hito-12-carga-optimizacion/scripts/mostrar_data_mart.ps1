param([string]$Carpeta = 'resultados/datamart/dm-20261030-032514-c7dd32')
$ErrorActionPreference = 'Stop'
$raizLectura = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$rutaLectura = if ([IO.Path]::IsPathRooted($Carpeta)) { $Carpeta } else { Join-Path $raizLectura $Carpeta }
& python (Join-Path $raizLectura 'datamart/v1.1_lector_corregido/consultar_proyeccion.py') $rutaLectura
if ($LASTEXITCODE -ne 0) { throw 'No se pudo consultar la proyeccion validada' }
