SELECT
  time,
  partido_id,
  equipo_id,
  fuente,
  posesion_pct,
  pases_completados,
  tiros,
  recuperaciones,
  velocidad_kmh
FROM estadisticas_partido
WHERE partido_id = 'M001'
  AND equipo_id = 'ARG'
  AND time >= '2030-06-15T18:30:00Z'
  AND time < '2030-06-15T18:40:00Z'
ORDER BY time, fuente
LIMIT 40;
