param(
    [ValidateSet('A','B')]
    [string]$Perfil = 'A'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Solo prepara archivos. No ejecuta Docker, el monitor ni cargas.
$raizH12 = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$rutaVersion = Join-Path $raizH12 'versiones\v2.2_candidata_paralelo'
$manifest = Get-Content -LiteralPath (Join-Path $rutaVersion 'manifiesto_version.json') -Raw | ConvertFrom-Json
foreach ($archivo in $manifest.archivos) {
    $hash = (Get-FileHash -LiteralPath (Join-Path $rutaVersion $archivo.ruta) -Algorithm SHA256).Hash
    if ($hash -ne $archivo.sha256) { throw "Archivo diferente del manifiesto: $($archivo.ruta)" }
}

$identificador = 'manual-{0}-{1}-{2}' -f $Perfil, (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0,6))
$relativaNueva = "resultados/optimizado/$identificador"
$carpetaNueva = Join-Path $raizH12 $relativaNueva
if (Test-Path -LiteralPath $carpetaNueva) { throw 'La carpeta ya existe. No se sobrescribe.' }
New-Item -ItemType Directory -Path $carpetaNueva -ErrorAction Stop | Out-Null
New-Item -ItemType Directory -Path (Join-Path $carpetaNueva 'capturas') -ErrorAction Stop | Out-Null

$contexto = [ordered]@{
    raiz = $raizH12
    version = 'versiones/v2.2_candidata_paralelo'
    relativa = $relativaNueva
    salida = $carpetaNueva
    perfil = $Perfil
    corrida = $identificador
    partido = "H12-$identificador"
    cliente = "h12-$($identificador.ToLowerInvariant())"
    imagen = $manifest.ambiente_referencia.imagen_cliente
    filas = 50000
    procesos = $(if ($Perfil -eq 'A') { 1 } else { 2 })
    concurrencia_por_proceso = $(if ($Perfil -eq 'A') { 100 } else { 50 })
    concurrencia_total = 100
}
$contexto | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $carpetaNueva 'corrida.json') -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $rutaVersion 'config\escenario_escritura_simple.json') -Destination (Join-Path $carpetaNueva 'escenario.json') -ErrorAction Stop

$encabezado = @'
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$c = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'corrida.json') -Raw | ConvertFrom-Json
Set-Location -LiteralPath $c.raiz
$recolector = Join-Path $c.raiz "$($c.version)/scripts/registrar_base.py"

'@

$monitor = @'
Write-Host "Monitoreando $($c.corrida). Ahora deja esta consola abierta y ejecuta 02_CARGAR en la otra."
& python $recolector recursos --perfil $c.perfil --cliente $c.cliente --salida (Join-Path $c.salida 'recursos.jsonl')
if ($LASTEXITCODE -ne 0) { throw 'El monitor termino con error. Revisa la salida.' }
'@

$carga = @'
if (Test-Path -LiteralPath (Join-Path $c.salida 'escrituras.jsonl')) { throw 'Esta corrida ya tiene resultados. Prepara otra; no se reutiliza.' }
if (-not (Test-Path -LiteralPath (Join-Path $c.salida 'recursos.jsonl'))) { throw 'Primero ejecuta 01_MONITOREAR en la segunda consola.' }
Start-Transcript -Path (Join-Path $c.salida 'consola_carga.txt') -NoClobber
try {
    Write-Host "Corrida: $($c.corrida) | Perfil $($c.perfil) | Filas: $($c.filas) | Procesos: $($c.procesos) | Concurrencia total: 100"
    & docker image inspect $c.imagen --format '{{.Id}}'
    if ($LASTEXITCODE -ne 0) { throw 'No se encontro la imagen de referencia. No se inicia la carga.' }
    & python $recolector entorno --perfil $c.perfil --cliente $c.cliente --salida (Join-Path $c.salida 'entorno.json')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo registrar el entorno. No se inicia la carga.' }
    $argumentos = @('run','--pull=never','--name',$c.cliente,'--network','fixture2030-cassandra_default',
        '--mount',"type=bind,source=$($c.raiz),target=/h12",'--workdir','/h12','--entrypoint','python',$c.imagen,
        "$($c.version)/carga/prueba_rendimiento.py",'--perfil',$c.perfil,'--host','fixture2030-cassandra',
        '--puerto','9042','--keyspace','fixture2030','--partido-prueba',$c.partido,
        '--salida',"/h12/$($c.relativa)/escrituras.jsonl",'--confirmar-escrituras')
    & docker @argumentos
    if ($LASTEXITCODE -ne 0) { throw 'La carga termino con error. Conserva todo y pasa la salida antes de repetir.' }
    Write-Host 'Saca una captura del resumen. Luego ejecuta 03_VERIFICAR.'
} finally { Stop-Transcript }
'@

$verificar = @'
if (-not (Test-Path -LiteralPath (Join-Path $c.salida 'escrituras.jsonl'))) { throw 'Todavia no existe el registro de carga.' }
if (Test-Path -LiteralPath (Join-Path $c.salida 'verificacion.json')) { throw 'Esta verificacion ya existe. No se sobrescribe.' }
Start-Transcript -Path (Join-Path $c.salida 'consola_verificacion.txt') -NoClobber
try {
    $argumentos = @('run','--pull=never','--name',"$($c.cliente)-verificacion",'--network','fixture2030-cassandra_default',
        '--mount',"type=bind,source=$($c.raiz),target=/h12",'--workdir','/h12','--entrypoint','python',$c.imagen,
        "$($c.version)/carga/verificar_escrituras.py",'--registro',"/h12/$($c.relativa)/escrituras.jsonl",
        '--salida',"/h12/$($c.relativa)/verificacion.json")
    & docker @argumentos
    if ($LASTEXITCODE -ne 0) { throw 'La verificacion requiere revision. Pasa la salida antes de continuar.' }
    Write-Host "Saca una captura de los conteos. Evidencia: $($c.salida)"
} finally { Stop-Transcript }
'@

($encabezado + "`r`n" + $monitor) | Set-Content -LiteralPath (Join-Path $carpetaNueva '01_MONITOREAR.ps1') -Encoding UTF8
($encabezado + "`r`n" + $carga) | Set-Content -LiteralPath (Join-Path $carpetaNueva '02_CARGAR.ps1') -Encoding UTF8
($encabezado + "`r`n" + $verificar) | Set-Content -LiteralPath (Join-Path $carpetaNueva '03_VERIFICAR.ps1') -Encoding UTF8

Write-Host "`nPREPARADO. No se ejecuto ninguna carga."
Write-Host "Perfil $Perfil | 50000 filas | $($contexto.procesos) proceso(s) | concurrencia total 100"
Write-Host "Carpeta: $carpetaNueva"
Write-Host "`n1. Copia esta linea a la SEGUNDA consola:"
Write-Host ("& '{0}'" -f ((Join-Path $carpetaNueva '01_MONITOREAR.ps1').Replace("'","''")))
Write-Host "`n2. Cuando el monitor este activo, ejecuta esta linea en la PRIMERA consola. INSERTA 50000 comentarios:"
Write-Host ("& '{0}'" -f ((Join-Path $carpetaNueva '02_CARGAR.ps1').Replace("'","''")))
Write-Host "`n3. Al finalizar la carga y sacar captura, ejecuta esta linea en la PRIMERA consola:"
Write-Host ("& '{0}'" -f ((Join-Path $carpetaNueva '03_VERIFICAR.ps1').Replace("'","''")))
