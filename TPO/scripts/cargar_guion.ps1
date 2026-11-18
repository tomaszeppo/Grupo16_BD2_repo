param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^P-\d{2,3}$')]
    [string]$Partido
)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
docker compose run --rm --no-deps herramientas python -m seed.cargar_guion_simulacion --partido $Partido
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
