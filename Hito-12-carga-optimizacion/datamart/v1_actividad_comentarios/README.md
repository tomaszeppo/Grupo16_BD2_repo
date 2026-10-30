# Actividad de comentarios por partido y minuto

Propuesta: [integracion Data Mart](../../docs/integracion_data_mart.md).
RF12/RF13: pregunta, fuentes, grano, medidas, transformaciones, correspondencias,
frecuencia, retraso, duplicados, faltantes, fallos y validacion documentados.
La consigna exige el diseno; esta demostracion es evidencia adicional opcional.

**Preparado, sin extraccion real ejecutada por el asistente.** No inicia cargas ni
modifica Cassandra. Escribe una carpeta local nueva con SQLite y validacion/procedencia.
El SQL es una proyeccion nueva, no una modificacion de los benchmarks historicos.

## Prueba offline de transformacion

```powershell
python -B -m unittest discover -s .\datamart\v1_actividad_comentarios -p test_proyeccion.py -v
```

## Extraccion opcional, ejecutada manualmente por el usuario

Para evitar depender de variables de la consola, desde la raiz H12 basta:

```powershell
& .\scripts\demostrar_data_mart.ps1
```

Este comando lee la corrida manual B especificada por defecto, crea una nueva proyeccion,
ejecuta el SQL de consulta en modo solo lectura y guarda la transcripcion. El asistente
no lo ejecuto. Requiere Docker activo y Python en el host. El procedimiento detallado
equivalente se conserva a continuacion.

Desde la raiz H12. Este ejemplo utiliza la corrida manual B ya verificada de 50.000 filas.
No ejecutarlo mientras hay escrituras sobre esa corrida. No ejecutar en paralelo con
otra prueba de rendimiento: la lectura compite por recursos.

```powershell
$marcaDM = Get-Date -Format 'yyyyMMdd-HHmmss'
$nombreDM = "dm-comentarios-$marcaDM"
$salidaDM = "resultados/datamart/$nombreDM"
$imagenDM = (Get-Content .\versiones\v2.2_candidata_paralelo\manifiesto_version.json -Raw | ConvertFrom-Json).ambiente_referencia.imagen_cliente
docker run --pull=never --name $nombreDM --network fixture2030-cassandra_default --mount "type=bind,source=$($PWD.Path),target=/h12" --workdir /h12 --entrypoint python $imagenDM datamart/v1_actividad_comentarios/proyectar_comentarios.py --registro /h12/resultados/optimizado/manual-B-20261030-025822-9dff16/escrituras.jsonl --salida "/h12/$salidaDM"
```

Las variables de este bloque se usan solamente dentro de la misma consola. El script
rechaza una carpeta existente. Los errores conservan evidencia y no publican validacion.
No hay limpieza automatica de contenedores, fuentes ni archivos. Para repetir, usar
otro nombre. La lectura se limita a la corrida registrada, trece buckets y 100.000 filas.

Consulta SQL posterior, en la misma consola (usa sqlite3 incluido en Python):

```powershell
python .\datamart\v1_actividad_comentarios\consultar_proyeccion.py $salidaDM
```

Guardar captura del resumen y consulta junto a la validacion. La extraccion y SQL no
se han ejecutado para preparar estos archivos. No afirmar resultados hasta ejecutarlos.
`consultas.sql` contiene las consultas de detalle/ranking y totales para otras herramientas.
