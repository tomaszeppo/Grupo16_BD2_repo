# M02 - Cliente paralelo con presupuesto global de concurrencia

Estado: implementado como candidata; rendimiento real pendiente. Fecha: 30/10/2026.
Requisitos: RF7, RF8 y registro de cambios de 5.5.

| Campo requerido | Registro |
|---|---|
| Problema e hipótesis | La base confirmó 50.000 escrituras a 6.261,365/s, con p99 172,385 ms. El cliente superó 90% de un núcleo en tres de cuatro muestras útiles. H2: repartir envío y callbacks entre dos procesos podría aliviar una limitación del cliente, conservando 100 operaciones en curso totales. Es una limitación posible; las muestras no demuestran su causa. |
| Cambio implementado | Perfil B: dos procesos creados con spawn, cada uno con sesión e INSERT preparado propios y concurrencia 50. Generación por índice global conserva exactamente los datos del control. Barrera después de preparar ambos trabajadores, antes de medir. Perfil A: un proceso, concurrencia 100, dentro de esta misma versión. |
| Archivos/configuración afectados | `carga/prueba_rendimiento.py`, nuevo `carga/perfil_paralelo.py`, `config/escenario_escritura_simple.json` y `scripts/registrar_base.py`. Tests y documentación propios. El medidor, verificador, esquema y dependencias declaradas son copias idénticas de v2.0. |
| Costo o riesgo | Más sesiones/conexiones, CPU y memoria; preparación y sincronización adicionales; posibilidad de trasladar la presión a Cassandra o empeorar rendimiento. Repetir genera nuevos datos que se conservan. Los dos trabajadores pueden terminar en momentos diferentes, reduciendo la concurrencia efectiva al final. |
| Prueba ejecutada después | Nueve pruebas offline aprobadas: igualdad de las 50.000 filas, perfiles, rechazo previo a conexión, barrera, spawn real con dos procesos sin operaciones, fallo de preparación, orden prepare/barrera/envío simulado, identidad de instrumentos y coherencia de configuración. No hubo conexiones ni cargas contra Cassandra. |
| Resultado medido | Se verificó funcionamiento y comparabilidad offline. Throughput, latencias, consumo y persistencia de la candidata: **sin medir**. La línea base histórica no es un resultado de B. |
| Decisión final del equipo | Pendiente de comparación A/B real; candidata disponible para evaluar, sin mejora demostrada. |

## Por qué estos cambios responden a la hipótesis

La concurrencia acota el trabajo en curso; el paralelismo reparte el trabajo del cliente
entre procesos que pueden usar núcleos distintos. En B no se duplica el presupuesto:
2 × 50 = 100, igual al control 1 × 100. Si el único proceso limita el suministro de
operaciones o el procesamiento de respuestas, esta distribución podría mejorar la tasa
y/o la cola de latencias. Si el límite está en Cassandra u otro recurso compartido,
podría no ayudar. También cambian las sesiones/pools; una mejora no demostraría por
sí sola que el GIL era el responsable.

El H6 ya ofrecía multiprocessing: el aporte es configurarlo como candidata controlada
y corregir la comparabilidad. Con el generador anterior, la semilla 2030 + proceso
alteraba los likes al repartir filas. Ahora cada tramo toma su parte de la misma
secuencia global de la base de un proceso. El salto de valores aleatorios y el hash
de datos se calculan antes de medir. Los IDs de corrida deben ser nuevos.

La barrera evita que un trabajador envíe mientras el otro todavía genera datos.
Su espera máxima es 60 s; un fallo previo aborta la barrera y se registra como error
de fase. Esto no promete arranque simultáneo exacto ni elimina el costo de spawn.
El tiempo total del cliente incluye esa preparación; el tiempo de carga la excluye.

## Prueba de rendimiento propuesta, todavía no ejecutada

1. Usar A y B de **v2.2**, con la misma imagen del cliente, Cassandra, límites, esquema,
   consulta, datos, instrumentación y monitor. La base histórica queda como antecedente.
2. Tres corridas por perfil, orden A1, B1, B2, A2, A3, B3; nuevas carpetas e IDs de igual
   longitud. Mantener la política de calentamiento de la base y registrar variación de
   entorno, crecimiento de tabla y posibles tareas de fondo. No hacer cargas simultáneas.
3. Registrar parámetros, hashes, tiempo total y de carga, throughput, muestras por
   operación, p95/p99 globales, errores por tipo, CPU/RAM/red/disco y persistencia.
   Los percentiles se calculan sobre las muestras individuales combinadas, no promediando
   percentiles de trabajadores. La latencia sigue excluyendo espera previa al envío.
4. Criterio propuesto por nosotros, previo a correr: conservar 50.000 confirmadas y
   persistidas sin errores en todas las corridas; mediana de throughput B al menos 10%
   mayor y mediana de p99 no más de 5% peor que A, con mejora de tasa en al menos dos
   de tres parejas. Si hay dispersión que impide decidir, repetir antes de concluir.
   Estos umbrales no son exigencias numéricas del profesor.
5. Registrar resultados y decisión en archivos nuevos; conservar hipótesis y evidencia.
   Si B no mejora, reportarlo y mantener A. No combinar este ensayo con el cambio M01
   de concurrencia total ni con cambios de particionamiento, timeout o esquema.

El experimento cambia una estrategia del cliente y sus controles necesarios, no aísla
por separado el efecto de cada ajuste interno. No abarca API HTTP ni Data Mart.
Las pruebas offline se ejecutaron en Python 3.14 de Windows; la ejecución con Python
3.12 y el driver de la imagen de referencia sigue pendiente de la prueba conjunta.
