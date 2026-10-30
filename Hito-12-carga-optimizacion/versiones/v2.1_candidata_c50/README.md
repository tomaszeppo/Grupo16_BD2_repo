# Versión candidata 2.1 - Concurrencia 50

**Candidata implementada, todavía sin medición real.** Base histórica: `../v2.0_base/`.
La hipótesis y la prueba propuesta existían antes del cambio. Ver
[registro de modificación M01](docs/registro_modificacion_M01.md).

## Cambios moderados

1. El perfil y la concurrencia predeterminada pasan de 100 a 50.
2. Se rechazan parámetros incompatibles antes de conectar o insertar: el perfil es
   50.000 filas, 50 operaciones en curso y un proceso. Para otro caso se crea otra versión.
3. La salida identifica `v2.1_candidata_c50` y registra el hash del perfil efectivo.

La consulta, dataset, particionamiento y medidor siguen iguales. El cambio de rendimiento
propuesto es uno: el límite de concurrencia. Los otros ajustes son controles de ejecución
y trazabilidad, realizados fuera de la fase medida. No se añade caché ni se modifica Cassandra.

## Qué significa implementada

La candidata realmente utiliza el planificador existente con un límite de 50, aunque
no se especifique `--concurrencia`. Si se usa el comando viejo con 100, falla antes de
abrir conexiones. Esto implementa el cambio; su efectividad se decidirá después de medir.

El comando anterior que apunta a `carga/prueba_rendimiento.py` en la raíz H12 sigue
correspondiendo a la referencia. Para probar B hay que apuntar explícitamente a esta carpeta.

## Preparación de una futura corrida B, desde la raíz H12

Los siguientes comandos son para una sesión posterior junto con el usuario. **No se
ejecutaron para crear esta versión.** La carga escribirá otras 50.000 filas y las conservará.

En una consola nueva o con variables nuevas:

```powershell
$marca = Get-Date -Format 'yyyyMMdd-HHmmss'
$corrida = "c50-$marca"
$partido = "H12-c050-$marca"
$cliente = "h12-c50-$marca"
$salida = Join-Path $PWD.Path "resultados\optimizado\$corrida"
New-Item -ItemType Directory -Path $salida -ErrorAction Stop
New-Item -ItemType Directory -Path (Join-Path $salida 'capturas') -ErrorAction Stop
$imagenCliente = (Get-Content .\versiones\v2.1_candidata_c50\manifiesto_version.json -Raw | ConvertFrom-Json).ambiente_referencia.imagen_cliente
Start-Transcript -Path (Join-Path $salida 'consola.txt') -NoClobber
Write-Output "Imagen cliente que se usara: $imagenCliente"
docker image inspect $imagenCliente --format '{{.Id}}'
python .\versiones\v2.1_candidata_c50\scripts\registrar_base.py entorno --cliente $cliente --salida (Join-Path $salida 'entorno.json')
```

El ID `H12-c050-...` conserva la longitud del ID de referencia `H12-base-...` y separa
sus particiones. Antes de ejecutar, verificar que recursos y versión del motor coincidan
con la referencia. Los límites y versiones observados quedan en la evidencia.

En otra consola situada en la raíz H12, reemplazar cliente y carpeta por los nuevos:

```text
python versiones/v2.1_candidata_c50/scripts/registrar_base.py recursos --cliente NOMBRE_CLIENTE --salida resultados/optimizado/ID_CORRIDA/recursos.jsonl
```

Después de iniciar el monitor, la futura carga B se ejecuta en la primera consola:

```powershell
docker run --pull=never --name $cliente --network fixture2030-cassandra_default --mount "type=bind,source=$($PWD.Path),target=/h12" --workdir /h12 --entrypoint python $imagenCliente versiones/v2.1_candidata_c50/carga/prueba_rendimiento.py --host fixture2030-cassandra --puerto 9042 --keyspace fixture2030 --rows 50000 --concurrencia 50 --procesos 1 --partido-prueba $partido --salida "/h12/resultados/optimizado/$corrida/escrituras.jsonl" --confirmar-escrituras
```

Se usa la imagen del cliente por el ID observado en la referencia. No necesita reconstruirse:
la versión se monta desde la carpeta del proyecto. Cassandra permanece en su mismo contenedor.

Verificación posterior, de solo lectura:

```powershell
docker run --pull=never --name "$cliente-verificacion" --network fixture2030-cassandra_default --mount "type=bind,source=$($PWD.Path),target=/h12" --workdir /h12 --entrypoint python $imagenCliente versiones/v2.1_candidata_c50/carga/verificar_escrituras.py --registro "/h12/resultados/optimizado/$corrida/escrituras.jsonl" --salida "/h12/resultados/optimizado/$corrida/verificacion.json"
```

Guardar el resultado incluso si hay errores y terminar la transcripción con `Stop-Transcript`.
No reintentar una corrida parcial con el mismo ID ni sobrescribir sus salidas. No hay limpieza
automática: los datos, contenedores y archivos se conservan. La línea base sigue histórica.
