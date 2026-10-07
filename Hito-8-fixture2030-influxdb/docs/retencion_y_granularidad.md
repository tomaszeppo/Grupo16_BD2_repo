# Retención y granularidad

## Retención aplicada

La base `fixture2030_metrics` se crea con **90 días** de retención.

Esta decisión mantiene suficiente margen para el trabajo operativo del torneo y evita asumir conservación infinita para puntos de alta frecuencia. En InfluxDB 3 Core el período de retención se fija al crear la base y es inmutable; cambiarlo implica otra base y eventual migración.

## Datos raw

Durante la ventana de retención se conserva la granularidad de segundos. Es la representación útil para revisar cambios finos de posesión, pases, tiros y velocidad.

## Resumen histórico propuesto

Para un histórico de más largo plazo, la propuesta es generar agregados de 5 minutos:

- promedio de `posesion_pct`;
- suma de `pases_completados`;
- suma de `tiros`;
- suma de `recuperaciones`;
- promedio y máximo de `velocidad_kmh`;
- máximo/promedio de `usuarios_activos` según pregunta.

La función correcta depende de la semántica del dato. No se suman medidas instantáneas como velocidad.

## Ciclo de vida

1. Ingreso: puntos raw por segundo.
2. Operación: consultas por rango corto.
3. Resumen: ventanas de 1–5 minutos cuando la consulta lo justifique.
4. Fin de retención: los puntos raw dejan de estar disponibles según la política de la base.

La entrega demuestra la retención aplicada y la agregación SQL; no presenta el downsampling automático como una funcionalidad ya ejecutada.
