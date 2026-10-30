# M01 - Mitigación candidata de presión del cliente (RF7, RF8 y 5.5)

Fecha de implementación: 30/10/2026. Estado: **implementada en una versión nueva,
sin ejecutar la carga comparativa ni demostrar todavía una mejora**.

La hipótesis se formuló antes del cambio en `docs/hipotesis_previa_optimizacion.md`
y `docs/RF7_analisis_y_prueba.md` de la raíz H12. La referencia histórica permanece en
`versiones/v2.0_base/` y sus datos en `resultados/base/base-20261030-002022/`.

| Campo solicitado | Registro de M01 |
|---|---|
| Problema / hipótesis | Un cliente de un proceso y hasta 100 operaciones en curso podría contribuir a la cola de latencias. Bajar a 50 podría reducir p99 sin pérdida importante de throughput ni integridad |
| Cambio implementado | Concurrencia predeterminada y perfil de ejecución de 100 a 50. Se mantiene un proceso y el mismo planificador asíncrono |
| Arreglos de control | Validación del perfil antes de conectar: 50.000 filas, concurrencia 50 y un proceso. Un comando heredado con 100 es rechazado. Se agregan identificación del experimento y hash del perfil al registro inicial |
| Archivos afectados | En esta versión: `carga/prueba_rendimiento.py` y `config/escenario_escritura_simple.json`. Documentación, pruebas aisladas y manifiesto nuevos. Ningún archivo histórico se modifica |
| Posible costo o riesgo | Menor throughput o mayor duración; el descenso de latencia podría no repetirse. Conservar resultados agrega datos y archivos. Las tareas compartidas, cachés y crecimiento de tabla pueden sesgar la comparación |
| Prueba ejecutada después | Seis verificaciones aisladas de perfil, rechazo temprano, igualdad de instrumentos, conservación de funciones y hashes históricos. Sin conexiones ni carga de Cassandra. La comparación A/B real sigue pendiente |
| Resultado medido | Referencia disponible: 50.000 confirmadas/persistidas, 6.261,365 escrituras/s y p99 172,385 ms. La candidata no tiene medición de rendimiento aún; no se calcula una mejora ficticia |
| Decisión final | Pendiente. La versión se prepara como candidata; no se aprueba como optimización efectiva hasta medir y contrastar con A |

## Por qué se implementa este cambio moderado

La línea base alcanzó 100 operaciones en curso. En tres de cuatro muestras útiles el
cliente superó el 90% de un núcleo, y p99 fue muy superior a p95. Eso justifica explorar
el nivel de concurrencia como variable, sin demostrar que el cliente sea la única causa.
El benchmark H6 de correcciones ya mencionaba posibles límites del generador.

El límite menor se aplica realmente al parámetro `concurrency` del planificador del driver.
La validación impide ejecutar la candidata con el antiguo argumento 100 por accidente.
Estos controles de perfil y trazabilidad ocurren antes de la fase medida.

## Qué permanece igual para poder comparar

- INSERT preparado, campos, payload, usuarios, semilla y timeuuid.
- Trece buckets, 50.000 filas y distribución esperada; solo cambia el ID exclusivo de cada corrida.
- Un proceso, ausencia de rampa y de calentamiento separado.
- Código de envío y cálculo de métricas: funciones `timeuuid`, `trabajo` y `ejecutar` sin cambios estructurales.
- Instrumento `metricas_operaciones.py`, verificador, monitor, esquema y dependencias idénticos byte por byte.
- Timeout, consistencia, retry policy y configuración del driver: sin cambios de optimización.

La versión **del experimento** es `v2.1_candidata_c50`. La versión **del medidor** sigue
siendo `2.0-instrumentado`; no se alteran sus definiciones de tiempo o percentiles.

## Prueba de mejora pendiente

Comparar A (histórica, concurrencia 100) y B (esta candidata, 50), con volumen, proceso,
instrumentación, datos y recursos equivalentes. El protocolo previo propone tres corridas
por condición y alternar el orden; no se ejecutaron automáticamente. Usar carpetas, IDs
y contenedores nuevos, con IDs de igual longitud. Conservar todos los resultados.

Observar p95/p99, throughput, errores, recursos y persistencia. Los umbrales propuestos
en RF7 (no impuestos por el profesor) se conservan sin modificarlos después de medir.
Si la mejora no se sostiene o pierde demasiado throughput, rechazarla o declararla no
concluyente. Incluso una mejora no identifica por sí sola el componente causal exacto.

Este registro satisface la descripción de la implementación candidata (RF8) y su vínculo
con RF7. La prueba y resultado posterior de 5.5 siguen pendientes de ejecución conjunta.
