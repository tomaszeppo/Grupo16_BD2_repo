# Hito 12 - Pruebas de carga y optimización

Estado al 30/10/2026: **primera línea base ejecutada y verificada; RF7 documentado**.
El flujo elegido es **insertar comentarios sintéticos en el módulo Cassandra del Hito 6**,
usando el benchmark existente. Se mide una tabla por driver; la consulta HTTP queda como
herramienta complementaria. La primera corrida confirmó y conservó 50.000 comentarios.
La [candidata v2.2](versiones/v2.2_candidata_paralelo/README.md) implementa un cliente
paralelo con dos procesos y concurrencia total 100, datos idénticos e inicio coordinado.
Incluye control A y candidata B en el mismo código. Ver [registro M02](versiones/v2.2_candidata_paralelo/docs/registro_modificacion_M02.md).
Nueve pruebas offline aprobadas; rendimiento real y decisión pendientes. No se ejecutaron
cargas para prepararla. La [hipótesis H2](docs/hipotesis_M02_paralelismo.md) precede al cambio.

La [candidata v2.1](versiones/v2.1_candidata_c50/README.md) implementa el ajuste de
concurrencia a 50 (RF8), con hipótesis RF7 previa. La prueba de la candidata y su comparación
siguen pendientes: no se declara una mejora demostrada.

Ver [RF7: evidencia, hipótesis y prueba propuesta](docs/RF7_analisis_y_prueba.md).
La [hipótesis previa y evaluación de técnicas](docs/hipotesis_previa_optimizacion.md)
cubre los aspectos de 5.5, excepto Data Mart. **Toda modificación futura se hará en una
versión nueva; la anterior queda histórica**, según la [política de versiones](versiones/README.md).
La referencia está conservada en `versiones/v2.0_base/`; la candidata se creó separadamente.
El [registro M01](versiones/v2.1_candidata_c50/docs/registro_modificacion_M01.md) documenta
hipótesis, implementación, archivos afectados, riesgos, verificaciones y medición pendiente.
Se encontraron antecedentes sobre límites del generador en ambas ramas; el análisis
actual se vinculó con los archivos reales de `base-20261030-002022`. No se ejecutó
una nueva carga ni se aplicó el cambio de concurrencia propuesto para este análisis.

La sección «Hito 12 - Pruebas de carga y optimización» de la Clase 13 pide definir,
medir, observar, detectar el cuello, optimizar y repetir. La organización de carpetas
sigue la propuesta `../arquitectura-hito-12.html`; el material de clase suministrado
no fija ese árbol exacto de directorios. Ver [alcance y fuentes](docs/consigna_y_alcance.md).

## Carpetas

```text
config/           escenario propuesto y plantilla de registro por corrida
datos/            manifiesto, correspondencias y lotes preparados, sin carga
scripts/          generación y validación de archivos; no conectan a bases
carga/            pruebas de escritura Cassandra, latencia HTTP y colección GET
analitica/        modelo SQLite y comparación relacional propuestos, sin ejecución
resultados/base/  reservado para resultados reales de la línea base
resultados/optimizado/ reservado para la repetición con mejora
docs/             inventario, trazabilidad, estado y plan de avance
```

## Leer primero

1. [Estado y próximos pasos](docs/estado_y_plan.md).
2. [Inventario de las fuentes y colecciones](docs/inventario_y_colecciones.md).
3. [Condiciones antes de insertar](datos/README.md).
4. [Escenario simple de escritura](config/escenario_escritura_simple.json).
5. [Lista de capturas y archivos de evidencia](docs/lista_capturas_comentarios.md).

## Flujo seleccionado y motivo

El cliente de prueba representa escrituras de comentarios de hinchas. Reutilizamos el
módulo Cassandra y su benchmark: son componentes existentes de la cursada relacionados
con el Fixture 2030. El escenario permite observar escrituras concurrentes y comprobar
que lo aceptado quedó persistido. La consigna permite seleccionar un módulo existente;
no obliga a combinar POST/GET ni a recorrer la API. La evidencia histórica sirve de antecedente.

| Punto de la consigna | Definición para este flujo |
|---|---|
| Usuario / consumidor | Proceso de benchmark que representa publicaciones de comentarios de hinchas |
| Datos recibidos | ID exclusivo de corrida/partido sintético, bucket, timeuuid, usuario, contenido, fecha, estado de moderación y likes |
| Fuente | Cassandra, tabla comentarios_por_partido del modelo H6 corregido |
| Tipo de operación | Inserción; verificación posterior mediante lecturas por partición |
| Respuesta esperada | Driver confirma o informa fallo por inserción; resumen de exitosas/fallidas, duración y escrituras/s. No hay códigos HTTP en este escenario |
| Volumen / frecuencia | 50.000 intentos, hasta 100 en curso, un proceso. Sin tasa fija: se mide la obtenida. Sin rampa ni calentamiento separado; finaliza al completar intentos o ante error/interrupción |
| Éxito | 50.000 escrituras exitosas, cero fallidas y conteos de las 13 particiones iguales a lo esperado |
| Errores / degradación | Conexión, esquema, timeout/rechazo, escrituras fallidas, interrupción y diferencias de persistencia; registrar errores y duración |

El generador masivo es opcional para este escenario: el benchmark genera sus propias filas.
Su millón de comentarios es un volumen total entre partidos; no es el volumen de esta corrida
ni una frecuencia HTTP. Los 13 buckets del benchmark se asignan cíclicamente; no se presenta
esta distribución como simulación temporal fiel de un partido.

## Herramientas incorporadas

Las copias se adaptaron dentro de H12 y conservan sus originales en los hitos anteriores.
[Procedencia y commits](docs/procedencia_scripts_carga.json).

| Archivo H12 | Origen | Función y alcance |
|---|---|---|
| `scripts/generar_carga_masiva.py` | H6, rama correcciones | Genera CSV reproducibles y conteos esperados. Solo crea archivos en un directorio nuevo |
| `carga/prueba_rendimiento.py` | H6, rama correcciones | Mide escrituras concurrentes directamente contra Cassandra. Inserta y conserva datos; requiere activación explícita |
| `carga/medir_latencia.py` | H10, main | Mide GET de comentarios por HTTP, secuencialmente; registra muestras y percentiles sin escribir datos de dominio |
| `scripts/esquema_comentarios_h6.cql` | H6, correcciones | Prepara el modelo con CREATE IF NOT EXISTS; sin cargas ni borrados |
| `carga/verificar_escrituras.py` | Apoyo H12 | Lee las 13 particiones de una corrida y contrasta conteos; no modifica datos |

Las dependencias de las dos herramientas de medición están en `carga/requirements.txt`.
El generador usa la biblioteca estándar de Python. Registrar las versiones reales de
Python, drivers y motores con cada corrida. Los comandos siguientes son ejemplos de
ejecución posterior: reemplazar los valores entre `<...>` y crear una carpeta nueva por
corrida bajo `resultados/base/` o `resultados/optimizado/`.

### Preparar el volumen masivo

Desde la carpeta H12:

```text
python scripts/generar_carga_masiva.py --target-rows 1200000 --usuarios 50000 --semilla 2030 --output-dir datos/carga_masiva/lote_01
```

El generador reparte el volumen entre 32 partidos, concentra el 70% en los primeros cinco
y distribuye cada partido en 13 buckets de diez minutos, con una duración sintética de
130 minutos. Los IDs son reproducibles. Produce:

- `partidos_referencia.csv`;
- `comentarios_por_partido.csv` y `comentarios_por_usuario.csv`;
- `conteo_esperado_por_particion.csv` y `conteo_esperado_por_usuario.csv`;
- `manifiesto.json`, con parámetros, cantidad real y hashes SHA-256.

El reparto usa divisiones enteras: el objetivo 1.200.000 genera **1.199.770 comentarios**
con los parámetros originales. Usar siempre la cantidad real del manifiesto. Los 50.000
usuarios son el universo configurado; el manifiesto también informa los presentes.
La salida debe ser nueva. No se conecta a Cassandra ni importa los CSV.

### Medir escrituras directas a Cassandra

```text
python carga/prueba_rendimiento.py --host <HOST_CASSANDRA> --puerto <PUERTO> --keyspace <KEYSPACE> --rows 50000 --concurrencia 100 --procesos 1 --partido-prueba H12-base-r01 --salida resultados/base/r01/escrituras.jsonl --confirmar-escrituras
```

El ejemplo heredado usa 50.000 filas y 100 escrituras concurrentes por proceso. Otra
configuración existente es 200.000 filas, concurrencia 100 y cuatro procesos: hasta 400
operaciones concurrentes entre procesos. Son alternativas configurables, no requisitos
numéricos del profesor ni corridas ejecutadas del H12.

El script requiere el esquema `comentarios_por_partido` del H6 corregido y conserva los
registros en 13 particiones del partido de prueba. Antes de insertar, rechaza un ID H12
que ya contenga datos. Cada corrida debe usar un identificador nuevo y exclusivo; el
entorno de prueba no debe tener otros escritores sobre esas mismas particiones.
La copia H12 elimina la limpieza automática del original: **no ejecuta DELETE ni TRUNCATE**.
Requiere `--confirmar-escrituras`; la preparación de este hito no ejecutó ese benchmark.

Guarda configuración, inicio y resultado en un JSONL nuevo: escrituras exitosas/fallidas,
duración y escrituras/s. Si falla después de comenzar, conserva datos y registra el tipo
de error; no reusar el ID de una corrida parcial. Se separan tasa durante la carga y tasa
sobre tiempo total (incluye conexiones, preparación y exportación de muestras). Esta prueba escribe una tabla y no
mide Neo4j, la API, la doble escritura del módulo ni la idempotencia HTTP.

### Medir consultas de comentarios por la API

```text
python carga/medir_latencia.py --base-url <URL_API> --partido <ID_PARTIDO> --pais ARG --ventana <INICIO_VENTANA_ISO_UTC> --n 50 --calentamiento 5 --salida resultados/base/r01/latencia.json
```

La copia está enfocada en GET de comentarios. Hace cinco requests de calentamiento y
50 medidos por defecto, con concurrencia uno. Registra muestras, estados HTTP,
request_id, errores de transporte, cantidad de elementos, tiempo total, RPS y
p50/p95/p99 de las respuestas válidas. El calentamiento queda fuera de las métricas.
Una lista vacía con contrato válido es un éxito; una respuesta de error no se cuenta
como exitosa. No prueba todavía toda la integridad semántica ni las páginas siguientes.

El ID debe ser válido para la API elegida y la ventana debe incluir zona y comenzar a
`:00` o `:30` UTC en el contrato actual del H10. Los resultados se guardan en un archivo
nuevo; el script no publica comentarios ni modifica sesiones.

## Correspondencia entre herramientas y consigna

| Etapa | Material disponible | Trabajo pendiente |
|---|---|---|
| Definir escenario | Escritura directa de 50.000 filas, concurrencia 100, un proceso, sin rampa | Registrar destino/versión efectiva en la evidencia y planificar repeticiones |
| Establecer línea base | Benchmark Cassandra y medición HTTP | Ejecutar y conservar corridas del escenario elegido |
| Observar capas | Muestras HTTP, conteos, tasa y errores de escritura | Capturar API, Neo4j/Cassandra, host, red y recursos del generador; validar datos aceptados |
| Detectar cuello | Resultados futuros de las herramientas | Relacionar el límite con una causa comprobable |
| Optimizar | Sin cambio elegido de antemano | Justificar e implementar una mejora según la línea base |
| Repetir y comparar | Directorios base/optimizado | Mismo dataset y condiciones, comparación cuantitativa, costos y límites |

Estos scripts aportan generación, un benchmark directo y una medición HTTP complementaria.
La carga combinada por API no es requisito de este escenario. La optimización debe responder
al cuello observado. La instrumentación 2.0 registra latencia mínima/promedio/p50/p95/p99/máxima
por operación, muestras individuales, errores por tipo y resultados por segundo. Mantener
esta misma instrumentación al comparar base y optimizado.

## Evidencia de la línea base instrumentada (sección 5.4)

Ver [caso base y definiciones de las métricas](docs/caso_base_reproducible.md).
`scripts/registrar_base.py` registra el entorno o monitorea recursos por lectura, sin
ejecutar cargas ni crear tablas. Usar archivos nuevos:

```text
python scripts/registrar_base.py entorno --cliente <NOMBRE_CLIENTE> --salida <CARPETA_CORRIDA>/entorno_instrumentado.json
python scripts/registrar_base.py recursos --cliente <NOMBRE_CLIENTE> --salida <CARPETA_CORRIDA>/recursos.jsonl
```

El segundo comando se deja en otra consola **antes** de lanzar el benchmark. Guarda
CPU/RAM del host Windows y CPU, memoria, red, BlockIO y PIDs de Cassandra/cliente por Docker.
El monitor termina cuando observa el cliente finalizado, al alcanzar su máximo (600 s
por defecto, configurable con `--max-segundos`) o con Ctrl+C. No detiene el benchmark.

El benchmark conserva la interfaz de ejecución. Además de `escrituras.jsonl`, crea
`escrituras.operaciones.p00.jsonl` (uno por proceso) con cada latencia y resultado.
El resumen distingue operaciones confirmadas, errores, inconclusas y no intentadas.
Un timeout no prueba rechazo del servidor: se contrasta con el verificador de persistencia.
Los errores no interrumpen el lote al primero; los fallos fatales se registran por separado.

Se conservó la versión previa en `docs/versiones/pre_instrumentacion/`. El código cambió
de hash: guardar una captura nueva del código y un `escenario_instrumentado.json`,
conservando snapshots anteriores. Las verificaciones de la instrumentación fueron aisladas,
con futuros falsos; no se ejecutó una carga contra Cassandra para probar estos cambios.

**Compatibilidad pendiente:** el H6 de correcciones usa `comentarios_por_partido`,
`comentarios_por_usuario` y buckets de diez minutos; la API H10 activa consume
`comentarios_por_partido_pais` y ventanas UTC de 30 minutos. Los CSV no se importan
directamente en ese esquema. Elegir y adaptar el modelo antes de cualquier carga.
Los detalles de máquina y configuración de cada ejecución se registran en su evidencia.

`config/escenario.json` y `config/escenario_comentarios.json` conservan las propuestas
anteriores (consultar partidos y combinar comentarios HTTP). La referencia vigente es
`config/escenario_escritura_simple.json`.

## Data Mart: actividad de comentarios

La [propuesta de integracion analitica](docs/integracion_data_mart.md) cubre RF12,
RF13, RNF12 y 5.7: actividad por partido/minuto, fuentes y procedencia, grano, medidas,
transformaciones, refresco, retraso, duplicados, faltantes, fallos y validacion.
El [prototipo v1](datamart/v1_actividad_comentarios/README.md) permite leer una corrida
Cassandra ya cerrada y crear una proyeccion SQLite local. Cuatro pruebas de transformacion
offline aprobadas. Extraccion real pendiente de ejecucion manual por el usuario.
No modifica Cassandra ni ejecuta cargas. Para la demostracion opcional:

```powershell
& .\scripts\demostrar_data_mart.ps1
```

La propuesta es suficiente para el alcance de Data Mart de la consigna; la demo aporta
evidencia adicional y no constituye un BI completo ni una medicion de produccion.

## Material preparado previamente

`datos/preparados/lote_20261029_01/` contiene 32 partidos de referencia del Hito 5,
10 estadios, 8 correspondencias documentales con el laboratorio Hito 10 y 1.920
comentarios sintéticos propuestos para 128 particiones. También incluye archivos
de apoyo de MongoDB, InfluxDB e IRIS del perfil Hito 10. Estos perfiles no se mezclan.
El manifiesto registra el commit, los orígenes, las cantidades y los SHA-256.

Para regenerar en **otra carpeta nueva**, sin tocar bases:

```text
python scripts/preparar_datos.py --salida datos/preparados/lote_NUEVO
python scripts/validar_archivos.py datos/preparados/lote_NUEVO
```

No hay un importador automático. Las consultas propuestas en `datos/plantillas/`
son material de revisión y no se ejecutaron. La colección de `carga/` solo contiene GET;
la colección original del Hito 10 contiene POST y DELETE y no debe ejecutarse completa
para una revisión que deba preservar el estado.

Los resultados históricos del Hito 10 no son una línea base del Hito 12.

