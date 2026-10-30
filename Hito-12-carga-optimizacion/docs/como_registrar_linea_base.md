# Ejecutar la línea base instrumentada

No se ejecutó el benchmark durante esta actualización. Se conserva el comando de carga
del tutorial, con las variables de la misma consola (`$corrida`, `$partido`, `$cliente`,
`$salida`). El bind mount incorpora los nuevos archivos sin reconstruir la imagen.

## Antes de la carga, en la consola principal

Guardar archivos nuevos, conservando `escenario.json` y las capturas de la versión anterior:

```powershell
[System.IO.File]::Copy((Resolve-Path .\config\escenario_escritura_simple.json).Path, (Join-Path $salida 'escenario_instrumentado.json'), $false)
Get-FileHash .\carga\prueba_rendimiento.py -Algorithm SHA256
Get-FileHash .\carga\metricas_operaciones.py -Algorithm SHA256
python .\scripts\registrar_base.py entorno --cliente $cliente --salida (Join-Path $salida 'entorno_instrumentado.json')
```

Una ruta ya existente se rechaza; no reintentar sobrescribiendo. Crear otro nombre para
un registro nuevo si hace falta conservar varias capturas de entorno. Los comandos del
registrador solo leen el motor y Docker, no ejecutan inserciones ni cambios de esquema.

Tomar captura nueva del código como `00c_codigo_instrumentado.png`. Actualizar la captura
de escenario para mostrar duración, sostenimiento y métricas definidas; conservar las viejas.

## Monitor en la segunda consola, antes de iniciar la prueba

Entrar a H12 en esa consola y reemplazar los valores de ejemplo por el ID de corrida y
cliente de la primera consola. Las variables de PowerShell no pasan de una ventana a otra.

```text
python scripts/registrar_base.py recursos --cliente NOMBRE_CLIENTE --salida resultados/base/ID_CORRIDA/recursos.jsonl --intervalo 2 --max-segundos 600
```

Esperar el mensaje de monitor activo y después ejecutar el benchmark desde la primera
consola. Capturar recursos con cliente running, no solo Cassandra antes/después. Si la
prueba tarda más que el máximo del monitor, extenderlo o registrar la falta de cobertura.
El monitor no corta la carga al terminar; Ctrl+C en él solo interrumpe la observación.

## Benchmark, en la primera consola

```powershell
docker run --pull=never --name $cliente --network fixture2030-cassandra_default --mount "type=bind,source=$($PWD.Path),target=/h12" --workdir /h12 --entrypoint python fixture2030-api-api carga/prueba_rendimiento.py --host fixture2030-cassandra --puerto 9042 --keyspace fixture2030 --rows 50000 --concurrencia 100 --procesos 1 --partido-prueba $partido --salida "/h12/resultados/base/$corrida/escrituras.jsonl" --confirmar-escrituras
```

Este paso sí inserta datos. No usar un ID que haya participado en una corrida anterior,
incluso parcial. Los errores individuales se guardan; los fallos fatales también. El
resultado debe identificarse como `2.0-instrumentado`. La instrumentación mantiene
INSERT, filas, distribución, semilla y concurrencia; añade medición y conteos completos.

## Persistencia, cuando termine

```powershell
docker run --pull=never --name "$cliente-verificacion" --network fixture2030-cassandra_default --mount "type=bind,source=$($PWD.Path),target=/h12" --workdir /h12 --entrypoint python fixture2030-api-api carga/verificar_escrituras.py --registro "/h12/resultados/base/$corrida/escrituras.jsonl" --salida "/h12/resultados/base/$corrida/verificacion.json"
```

Solo lee particiones. Distingue igualdad de conteos del cumplimiento completo de la corrida
(confirmaciones, ausencia de errores e inconclusos y persistencia). No se borra nada.

## Qué conservar

- `entorno_instrumentado.json` y `escenario_instrumentado.json`.
- `consola.txt`, manteniendo la transcripción activa.
- `escrituras.jsonl`: parámetros efectivos, versiones, resumen, errores y serie por segundo.
- `escrituras.operaciones.p00.jsonl`: muestras individuales, incluso errores.
- `recursos.jsonl`: muestreo real del host y contenedores.
- `verificacion.json` y capturas del resultado/persistencia/recursos.
- Observaciones de estabilidad completadas con `config/observaciones_corrida.template.md`.

Nada de lo anterior es un resultado exitoso hasta ejecutar y revisar. No editar resultados
para que coincidan con lo previsto. Si el monitor no captó la carga o una corrida quedó
interrumpida, anotarlo como limitación, conservarla y planificar la repetición correspondiente.
