Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$c = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'corrida.json') -Raw | ConvertFrom-Json
Set-Location -LiteralPath $c.raiz
$recolector = Join-Path $c.raiz "$($c.version)/scripts/registrar_base.py"

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
