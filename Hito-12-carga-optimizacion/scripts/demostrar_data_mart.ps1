param(
    [string]$Corrida = 'manual-B-20261030-025822-9dff16'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($Corrida -notmatch '^manual-[AB]-[0-9]{8}-[0-9]{6}-[a-f0-9]{6}$') { throw 'Nombre de corrida manual no valido' }
$raizDataMart = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $raizDataMart
$registroDataMart = "resultados/optimizado/$Corrida/escrituras.jsonl"
if (-not (Test-Path -LiteralPath $registroDataMart)) { throw 'No existe el registro de la corrida indicada' }
$verificacionDataMart = Get-Content -LiteralPath "resultados/optimizado/$Corrida/verificacion.json" -Raw | ConvertFrom-Json
if (-not $verificacionDataMart.criterio_completo_cumplido) { throw 'La corrida no tiene persistencia validada' }
$imagenDataMart = (Get-Content -LiteralPath 'versiones/v2.2_candidata_paralelo/manifiesto_version.json' -Raw | ConvertFrom-Json).ambiente_referencia.imagen_cliente
$idDataMart = 'dm-{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0,6))
$salidaDataMart = "resultados/datamart/$idDataMart"
if (-not (Test-Path -LiteralPath 'resultados/datamart')) {
    New-Item -ItemType Directory -Path 'resultados/datamart' -ErrorAction Stop | Out-Null
}
Start-Transcript -Path "resultados/datamart/$idDataMart.consola.txt" -NoClobber
try {
    Write-Host 'Esta demostracion SOLO LEE Cassandra y crea una proyeccion SQLite local nueva.'
    Write-Host 'No ejecutarla junto con pruebas de carga. No se insertan comentarios ni se cambia el esquema.'
    $argumentosDataMart = @('run','--pull=never','--name',$idDataMart,'--network','fixture2030-cassandra_default',
        '--mount',"type=bind,source=$raizDataMart,target=/h12",'--workdir','/h12','--entrypoint','python',$imagenDataMart,
        'datamart/v1_actividad_comentarios/proyectar_comentarios.py','--registro',"/h12/$registroDataMart",
        '--salida',"/h12/$salidaDataMart")
    & docker @argumentosDataMart
    if ($LASTEXITCODE -ne 0) { throw 'Extraccion no validada. Conservar evidencia; no continuar con SQL.' }
    Write-Host "`nCONSULTA SQL SOBRE LA PROYECCION VALIDADA"
    & python 'datamart/v1_actividad_comentarios/consultar_proyeccion.py' $salidaDataMart
    if ($LASTEXITCODE -ne 0) { throw 'Error al consultar la proyeccion local' }
    Write-Host "Guarda una captura de la consulta y de los conteos. Evidencia: $salidaDataMart"
} finally { Stop-Transcript }
