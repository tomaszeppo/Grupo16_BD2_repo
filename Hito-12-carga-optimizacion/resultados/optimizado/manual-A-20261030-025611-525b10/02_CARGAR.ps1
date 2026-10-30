Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$c = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'corrida.json') -Raw | ConvertFrom-Json
Set-Location -LiteralPath $c.raiz
$recolector = Join-Path $c.raiz "$($c.version)/scripts/registrar_base.py"

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
