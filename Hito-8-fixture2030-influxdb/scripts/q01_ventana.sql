SELECT
  time,
  partido_codigo,
  equipo_codigo,
  fuente,
  posesion_pct,
  pases_completados,
  tiros,
  recuperaciones,
  velocidad_kmh
FROM estadisticas_partido
WHERE partido_codigo = 'P-01'
  AND equipo_codigo = 'ARG'
  AND time >= '2030-06-15T18:30:00Z'
  AND time < '2030-06-15T18:40:00Z'
ORDER BY time, fuente
LIMIT 40;
