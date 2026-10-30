# Candidata v2.2: cliente paralelo

Implementa M02/RF8, con [hipótesis previa H2](../../docs/hipotesis_M02_paralelismo.md)
y [registro completo de modificación](docs/registro_modificacion_M02.md).
**Sin carga real ni mejora medida todavía.** v2.0 y v2.1 permanecen históricas.

| Perfil | Filas | Procesos | Concurrencia por proceso | Máximo total configurado |
|---|---:|---:|---:|---:|
| A, control de esta versión | 50.000 | 1 | 100 | 100 |
| B, candidata predeterminada | 50.000 | 2 | 50 | 100 |

Cada trabajador tiene su sesión preparada, usa spawn y espera una barrera antes de
medir. Los datos son idénticos por índice global en ambos perfiles y respecto de la
base de un proceso (excepto el ID exclusivo de corrida). Se conserva el medidor original.
Cambiar solamente `--procesos 2` en el código viejo no implementa este experimento.

## Validación offline

Desde la raíz del Hito 12:

```powershell
python -B -m unittest discover -s .\versiones\v2.2_candidata_paralelo\tests -v
```

Nueve pruebas aprobadas. La generación en memoria y el ensayo de coordinación entre
dos procesos no conectan con Docker ni con bases y no insertan datos.

## Ejecución futura, junto con el usuario

No se ejecutaron estos comandos para preparar la versión. Cada corrida escribe y
conserva 50.000 filas. A continuación se prepara **una** corrida; cambiar `$perfil`
para cada condición del protocolo. No ejecutar dos cargas a la vez.

Primera consola, situada en la raíz del Hito 12:

```powershell
$perfil = 'B' # usar 'A' para el control nuevo
$marca = Get-Date -Format 'yyyyMMdd-HHmmss'
$corrida = "m02-$perfil-$marca"
$partido = "H12-$corrida"
$cliente = "h12-$corrida"
$salida = Join-Path $PWD.Path "resultados\optimizado\$corrida"
New-Item -ItemType Directory -Path $salida -ErrorAction Stop
New-Item -ItemType Directory -Path (Join-Path $salida 'capturas') -ErrorAction Stop
Copy-Item .\versiones\v2.2_candidata_paralelo\config\escenario_escritura_simple.json (Join-Path $salida 'escenario.json') -ErrorAction Stop
$imagenCliente = (Get-Content .\versiones\v2.2_candidata_paralelo\manifiesto_version.json -Raw | ConvertFrom-Json).ambiente_referencia.imagen_cliente
Start-Transcript -Path (Join-Path $salida 'consola.txt') -NoClobber
Write-Output "Perfil=$perfil | Corrida=$corrida | Cliente=$cliente"
docker image inspect $imagenCliente --format '{{.Id}}'
python .\versiones\v2.2_candidata_paralelo\scripts\registrar_base.py entorno --perfil $perfil --cliente $cliente --salida (Join-Path $salida 'entorno.json')
```

En la segunda consola, desde la misma raíz, reemplazar los dos marcadores por los
valores mostrados arriba e iniciar el monitor antes de la carga:

```text
python versiones/v2.2_candidata_paralelo/scripts/registrar_base.py recursos --cliente NOMBRE_CLIENTE --salida resultados/optimizado/ID_CORRIDA/recursos.jsonl
```

Primera consola, después de iniciar el monitor:

```powershell
docker run --pull=never --name $cliente --network fixture2030-cassandra_default --mount "type=bind,source=$($PWD.Path),target=/h12" --workdir /h12 --entrypoint python $imagenCliente versiones/v2.2_candidata_paralelo/carga/prueba_rendimiento.py --perfil $perfil --host fixture2030-cassandra --puerto 9042 --keyspace fixture2030 --partido-prueba $partido --salida "/h12/resultados/optimizado/$corrida/escrituras.jsonl" --confirmar-escrituras
```

El perfil fija filas/concurrencia/procesos; no hace falta repetirlos. Una combinación
incompatible se rechaza antes de conectar. El monitor termina al finalizar el cliente.
Luego verificar persistencia, sin borrar ni reinsertar:

```powershell
docker run --pull=never --name "$cliente-verificacion" --network fixture2030-cassandra_default --mount "type=bind,source=$($PWD.Path),target=/h12" --workdir /h12 --entrypoint python $imagenCliente versiones/v2.2_candidata_paralelo/carga/verificar_escrituras.py --registro "/h12/resultados/optimizado/$corrida/escrituras.jsonl" --salida "/h12/resultados/optimizado/$corrida/verificacion.json"
Stop-Transcript
```

Guardar capturas del perfil/entorno, resumen de carga, recursos y verificación. Conservar
también todos los JSONL: B tiene dos archivos de operaciones, A tiene uno. No reutilizar
IDs, nombres ni salidas aunque una corrida falle. No hay limpieza automática.
Repeticiones, umbrales, riesgos y decisión pendiente están en el registro M02.
