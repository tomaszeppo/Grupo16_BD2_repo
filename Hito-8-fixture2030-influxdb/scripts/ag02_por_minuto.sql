SELECT
  DATE_BIN(INTERVAL '1 minute', time, '2030-06-15T18:30:00Z') AS minuto,
  equipo_id,
  AVG(posesion_pct) AS posesion_promedio,
  SUM(pases_completados) AS pases_totales,
  SUM(tiros) AS tiros_totales,
  AVG(velocidad_kmh) AS velocidad_promedio
FROM estadisticas_partido
WHERE partido_id = 'M001'
  AND time >= '2030-06-15T18:30:00Z'
  AND time < '2030-06-15T18:40:00Z'
GROUP BY 1, equipo_id
ORDER BY 1, equipo_id;
