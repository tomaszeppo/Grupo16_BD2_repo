# Patrones de acceso

## P1 — Evolución de una estadística de un equipo en un partido

**Solicitante:** pantalla de partido / analítica operativa.  
**Entrada:** `partido_id`, `equipo_id`, rango temporal.  
**Respuesta:** puntos ordenados por `time`, con posesión, pases, tiros, recuperaciones y velocidad.  
**Frecuencia:** alta durante partidos.  
**Datos temporales:** observaciones deportivas.  
**Estructura:** tabla `estadisticas_partido` con `partido_id` y `equipo_id` como tags.

## P2 — Comparar equipos de un partido

**Solicitante:** pantalla de partido y módulo analítico.  
**Entrada:** `partido_id` + ventana temporal.  
**Respuesta:** promedio de posesión y velocidad, totales de pases/tiros/recuperaciones por `equipo_id`.  
**Frecuencia:** alta durante partidos.  
**Estructura:** agregación SQL sobre la misma tabla; el equipo es una dimensión indexable.

## P3 — Comparar fuentes de una observación

**Solicitante:** control de calidad / analítica.  
**Entrada:** `partido_id` + rango.  
**Respuesta:** agregaciones por `fuente`.  
**Frecuencia:** media.  
**Estructura:** `fuente` como tag de cardinalidad acotada.

## P4 — Pico de usuarios activos por región

**Solicitante:** plataforma / capacidad operativa.  
**Entrada:** `partido_id`, `region`, rango temporal.  
**Respuesta:** máximo o promedio de `usuarios_activos`.  
**Frecuencia:** media-alta.  
**Estructura:** tabla `usuarios_conectados` con `partido_id` y `region` como tags.

## P5 — Tendencia temporal por minuto

**Solicitante:** dashboard analítico.  
**Entrada:** partido, intervalo, equipo.  
**Respuesta:** una fila por minuto y equipo con promedios/totales.  
**Frecuencia:** periódica.  
**Estructura:** `DATE_BIN` de 1 minuto sobre la tabla raw.

## Respuesta ante ausencia o retraso

Si no hay puntos para el rango pedido, el consumidor recibe un conjunto vacío y debe distinguir “sin observaciones” de cero. Los datos tardíos se aceptan en el modelo como observaciones con timestamp de origen; las consultas deben declarar el rango y no depender de `now()` cuando se analizan datos sintéticos fechados en 2030.
