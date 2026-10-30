# Caso base de comentarios: instrumentación 2.0

La línea base se obtendrá al ejecutar esta versión antes de optimizar. No hay resultados
reales de carga producidos durante esta modificación. La versión anterior y su configuración
se conservaron en `docs/versiones/pre_instrumentacion/`. No se alteraron sus capturas ni transcripciones.

| Aspecto | Caso base definido |
|---|---|
| Flujo / consumidor | Cliente de benchmark que representa escrituras de comentarios del Fixture 2030 |
| Módulo | H6 corregido, Cassandra, tabla comentarios_por_partido |
| Operación | INSERT preparado por driver; no intervienen API ni Neo4j |
| Datos | 50.000 comentarios ficticios; 5.000 usuarios, diez comentarios por usuario; contenido fijo, likes deterministas |
| Generación | Semilla 2030 en un proceso, timeuuid y fecha derivados del índice; no usa CSV del generador masivo |
| Distribución | 13 buckets cíclicos: dos con 3.847 filas y once con 3.846; ID H12 exclusivo por corrida |
| Concurrencia / rampa | Hasta 100 operaciones en curso, un proceso, rampa 0; se registra el pico observado del cliente |
| Sostenimiento | El planificador repone operaciones hasta agotar el lote; el número en curso disminuye al drenar las últimas |
| Frecuencia | Sin tasa fija de llegada; cliente de ciclo cerrado, la tasa obtenida se mide |
| Duración / fin | Hasta completar intentos, error fatal o interrupción. Errores individuales se registran sin cortar el lote al primero |
| Calentamiento | Sin corrida separada; conexión y prepare se excluyen de latencia por operación y del intervalo principal de carga |
| Latencia | Cliente: desde execute_async hasta callback o excepción síncrona; incluye driver, red y reintentos implícitos. No es tiempo puro de Cassandra ni incluye espera previa al envío |
| Estadísticos | Mínima, promedio, p50, p95, p99 y máxima, para todas las terminadas, confirmadas y errores por separado |
| Percentiles | Rango más cercano ceil(q*n), combinando muestras individuales de todos los procesos, no promedios de percentiles |
| Throughput principal | Confirmaciones exitosas / intervalo de carga; también intentos/s y tasa sobre tiempo total del cliente |
| Tiempo total | Incluye conexiones, generación, arranque de procesos y exportación de muestras; se informa separado |
| Resultados cliente | Previstas, iniciadas, con resultado, confirmadas, errores, inconclusas y no intentadas |
| Errores | Clase de excepción, datos estructurados disponibles, tasa y causas agregadas; errores de conexión/esquema/fase separados |
| Persistencia | SELECT COUNT por cada una de las 13 particiones, sin conteo global; compara esperado, guardado y confirmaciones del cliente |
| Éxito | 50.000 confirmadas, cero errores/inconclusas/no intentadas/fallos de fase, y todos los conteos esperados presentes |
| Recursos | Serie host Windows CPU/RAM y docker stats de Cassandra/cliente: CPU, memoria, red, BlockIO y PIDs; fecha y ventana de muestreo real |
| Estabilidad | Resultados por segundo, errores y recursos para observar variación; registrar intervenciones y pausas. No se declara estable solo por terminar |
| Límites | Una tabla, un nodo previsto y un partido sintético; no simula popularidad entre partidos, ventanas reales, doble escritura, tráfico HTTP ni todo el TPO |

Las operaciones con timeout u otro error se denominan **sin confirmación**, no necesariamente
rechazadas por Cassandra. Algunas pueden haberse persistido. Los conteos posteriores permiten
contrastar eso; no se inventa un conteo de rechazos definitivos del servidor. Un intento lógico
del driver puede incluir reintentos físicos, que no se cuentan como comentarios adicionales.

## Registro exigido por la sección 5.4

| Requisito | Archivo / evidencia |
|---|---|
| Commit o versión | entorno_instrumentado.json: git y hashes de los archivos locales; escrituras.jsonl: versión 2.0 y hashes del benchmark/métricas |
| Configuración API/productos | API no interviene; esquema observado, límites Docker, réplica del keyspace, consistencia, política de reintento, timeout y protocolo registrados |
| Imágenes/clientes observados | IDs reales Docker, versión Cassandra/CQL, Python y cassandra-driver |
| Cantidad/distribución | Escenario instrumentado y parámetros efectivos en el evento inicio; muestras y verificación posterior |
| Duración/concurrencia | Tiempo de carga, tiempo total, límite configurado y pico del cliente por proceso |
| Latencias/throughput/errores | Resumen escrituras.jsonl y escrituras.operaciones.p00.jsonl con cada respuesta |
| Recursos | recursos.jsonl, no solo una captura; ausencias se marcan como no disponibles |
| Cantidades y estabilidad | Contadores del cliente, verificacion.json, serie por segundo y observaciones de la sesión |

Las muestras de Docker registran contadores de red y disco acumulados, no latencia física
del disco. CPU Docker puede superar 100% (más de un núcleo); la CPU del host usa 0-100% global.
La primera lectura de CPU host es nula hasta disponer de dos muestras. Si una prueba es muy
corta puede haber pocas muestras: se debe declarar esa limitación. El monitor no detiene
el benchmark y termina al observar el contenedor cliente finalizado, por Ctrl+C o por su máximo.
No se mide aquí el total de conexiones del servidor ni los requests físicos por reintento.

## Cómo repetir sin reemplazar evidencia

1. Usar un ID de corrida nuevo y directorio vacío, el mismo escenario y código instrumentado.
2. Guardar entorno y escenario instrumentados antes de la carga; conservar el snapshot previo.
3. Iniciar el monitor de recursos antes del benchmark y mantener las otras cargas controladas.
4. Ejecutar el mismo comando del tutorial: la imagen existente ve la versión nueva por bind mount;
   no requiere reconstruirse. Escribir un partido H12 exclusivo, no un ID ya usado.
5. Guardar resumen y muestras; verificar las trece particiones y las confirmaciones del cliente.
6. Conservar también errores, corridas parciales y recursos. Una interrupción forzada puede dejar
   muestras incompletas: no atribuir cero errores ni todas las filas a un resultado incompleto.
7. Repetir la mejora con la misma instrumentación. No comparar directamente la tasa v1 (total)
   con la v2 (intervalo de carga): mantener la misma definición de tiempo en ambas versiones.

Los archivos actuales de la corrida `base-20261030-002022` pertenecen al inicio previo.
La incorporación de métricas cambia el hash del código. Guardar una nueva captura del hash
y `escenario_instrumentado.json`; conservar los archivos y capturas anteriores.
