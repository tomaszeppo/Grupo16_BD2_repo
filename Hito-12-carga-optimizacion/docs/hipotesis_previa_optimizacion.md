# Hipótesis previa y evaluación de optimizaciones (RF7 y sección 5.5)

Fecha: 30/10/2026. **Documento previo al cambio: no se aplicó una optimización ni se
ejecutó una nueva carga.** Se excluye la proyección del Data Mart según el alcance indicado.
Las técnicas se evalúan por pertinencia: no se propone aplicarlas todas.

## Evidencia y antecedentes

Reutilizamos el módulo Cassandra del H6 corregido y el benchmark instrumentado 2.0.
`arquitectura-hito-12.html` de main advierte sobre límites del generador; el benchmark
de H6 en correcciones también plantea un posible límite de CPU de un proceso Python.
Son antecedentes, no una demostración del cuello de nuestra corrida.

La corrida `base-20261030-002022` obtuvo 50.000 confirmaciones y registros persistidos,
cero errores, 7,985 segundos de carga y 6.261,365 escrituras/s. Registró promedio 15,870 ms,
p95 18,159 ms, p99 172,385 ms y máxima 438,623 ms. Hubo 900 operaciones mayores a 100 ms
(1,8%), repartidas en los ocho intervalos de la carga.

El cliente de un proceso alcanzó 100 operaciones en curso. En cuatro muestras útiles
su CPU fue 80,33%, 91,77%, 98,68% y 98,07%, en escala Docker por núcleo. Cassandra llegó
a 398,28% (aproximadamente cuatro núcleos), no al 398% de todo el host. La corrida es
corta y el monitor tiene pocas muestras; una quinta muestra cruza la salida del cliente
y se excluye al devolver PIDs y memoria cero.

La evidencia completa, archivos y hashes están en [RF7](RF7_analisis_y_prueba.md) y
`resultados/base/base-20261030-002022/analisis_RF7.json`.

## Hipótesis principal antes de modificar

**Posible limitación:** el cliente de un proceso, con hasta 100 operaciones concurrentes,
puede estar cerca de su capacidad para despachar solicitudes y procesar respuestas/callbacks.
El driver y la instrumentación podrían contribuir a la cola de latencias observada.

**H1:** si parte de esa cola se debe a la presión de concurrencia del cliente, reducir
el límite de 100 a 50, manteniendo un proceso, datos e instrumentación, debería mejorar
el p99 sin una pérdida importante de throughput ni de integridad.

No se afirma que el cliente sea el único cuello, que el GIL sea una causa demostrada o
que Cassandra, red, almacenamiento o pausas del entorno estén descartados. Incluso una
mejora al bajar concurrencia indicaría una configuración más conveniente en el recorrido
medido, sin aislar automáticamente el componente exacto que la produjo.

## Evaluación de cada aspecto de 5.5

| Aspecto | Situación y lectura previa | Decisión inicial |
|---|---|---|
| Estructura de la consulta | INSERT preparado, parametrizado, de ocho columnas; no hay joins ni filtrados en la operación medida | Mantener. No hay evidencia para reescribirlo como primer cambio |
| Índices o proyecciones | La prueba escribe por el modelo H6; no hay una consulta de lectura que motive un nuevo acceso secundario | No agregarlos como supuesto arreglo; justificar primero una necesidad de acceso |
| Paginación y límites | Es escritura sin páginas. Hay un volumen de 50.000 y un límite de pendientes de 100 | Paginación no pertinente; conservar volumen y evaluar el límite concurrente por separado |
| Patrón de particionamiento | Trece particiones cíclicas con cantidades casi iguales; no representa popularidad real | Mantener para aislar H1. No tenemos mediciones por réplica/partición que prueben hotspot |
| Tamaño de lote | Cada comentario es un INSERT independiente; no se usa CQL BATCH ni COPY | Mantener. 50.000 es volumen de corrida y 100 es concurrencia, no tamaño de batch del servidor |
| Concurrencia del cliente | Un proceso, máximo observado 100 y CPU cercana a un núcleo en tres muestras, con cola de latencias | Primera candidata: comparar 100 y 50; no aplicar todavía |
| Pool de conexiones | Lo gestiona el driver; no se midieron esperas ni agotamiento específico del pool | Mantener configuración y versión. No aumentar conexiones ni atribuirle la causa sin evidencia |
| Timeouts y reintentos | Timeout de diez segundos, política observada RetryPolicy, cero errores; máxima inferior a medio segundo | Mantener. No hay timeouts medidos que justifiquen cambiarlos. No se contó el número físico de reintentos |
| Caché e invalidación | Cada comentario nuevo debe confirmarse y conservarse; no es una lectura repetida cacheable | No aplicar caché como primera mejora ni introducir confirmaciones diferidas |
| Reducción de datos transferidos | Payload sintético fijo con los campos del modelo; no se demostró saturación de red | Conservar campos y contenido para comparar el mismo trabajo |
| Agregación previa | Una fila representa un comentario; se esperan 50.000 registros individuales | No agregar comentarios: reduciría escrituras cambiando el grano y el objetivo |
| Separación operacional/analítico | La fase medida escribe; conteos y análisis se realizan después. El monitor observa recursos | Mantener separación; no introducir reportes sobre datos en el intervalo medido y registrar el costo del monitor |
| Elección de fuente o modelo | Cassandra/H6 ya implementa este módulo; medimos una tabla, no la plataforma completa | Mantener fuente y modelo; no hay comparación que justifique migrarlos |

## Prueba propuesta, todavía no ejecutada

| Condición | A: referencia | B: candidata |
|---|---|---|
| Volumen | 50.000 | 50.000 |
| Concurrencia | 100 | 50 |
| Procesos | 1 | 1 |
| Rampa / calentamiento separado | 0 / no | 0 / no |
| Datos y generación | Semilla 2030, 5.000 usuarios, mismas reglas y trece buckets | Iguales, salvo el ID exclusivo de corrida, de igual longitud |
| Medición y entorno | Instrumentación 2.0, mismos recursos, driver, consulta, esquema, timeout, retry policy y pool | Sin cambios |

La única variable experimental es la concurrencia. El protocolo detallado de repeticiones
y decisión está en `config/prueba_RF7_concurrencia.json` y RF7. Sus tolerancias son propuestas
del equipo, no exigencias del profesor: deben fijarse antes de medir, no ajustarse al resultado.

Se compararán throughput, p50/p95/p99, máximos, errores, recursos y persistencia, conservando
todas las corridas y su variación. Si B pierde demasiado throughput, no mejora p99 o las
diferencias no son consistentes, H1 se rechazará en esos términos o quedará no concluyente.
La tabla crecerá al conservar los registros; cachés, compactaciones y tareas compartidas
pueden variar y deberán constar como límites. No se borrarán datos para igualar el estado.

## Registro previo de la modificación candidata M01

| Campo solicitado | Registro actual |
|---|---|
| Problema / hipótesis | H1: posible presión del cliente de un proceso con concurrencia 100 y cola de latencias |
| Cambio implementado | **Ninguno todavía.** Se propone concurrencia 50, sin cambiar otras variables |
| Archivos o configuración afectados | Futura carpeta `versiones/v2.1_candidata_c50/`, copia nueva del medidor y configuración B; la referencia `versiones/v2.0_base/` queda histórica |
| Posible costo o riesgo | Menor throughput, mayor duración, costo de repeticiones y más almacenamiento; sesgos por crecimiento de tabla y entorno |
| Prueba ejecutada después | Pendiente; comparación A/B con las mismas mediciones y verificación de persistencia |
| Resultado medido | Solo referencia A: 6.261,365 escrituras/s y p99 172,385 ms, con 50.000 confirmadas/persistidas y cero errores. No hay resultado B |
| Decisión final | Pendiente de evidencia; no se declara una mejora demostrada |

Después se completarán rutas/versiones reales, fecha, diff, resultados y decisión. Cada
hipótesis o cambio tendrá su registro; no se reescribirá el planteo previo después de medir.

## Versionado y conservación

Se congeló `versiones/v2.0_base/`: los seis archivos identificados por SHA-256 en el
entorno coinciden byte por byte con los de la línea base. Se incluye también la declaración
de dependencias, distinguiéndola de las versiones realmente instaladas. El manifiesto
identifica hashes, imagen y versiones observadas. Los datos crudos siguen en su carpeta.

**Regla para próximas tareas:** cualquier modificación experimental, incluso solo un
parámetro, se hará en una versión nueva, dejando intactos código, configuración, datos
y resultados históricos. La variante B todavía no fue creada ni ejecutada.

La versión del experimento distingue A/B; el instrumento debe permanecer igual para
compararlos. Si cambia el medidor, se identificará y se generará otra referencia comparable
antes de atribuir mejoras al sistema. Ver [política de versiones](../versiones/README.md).
