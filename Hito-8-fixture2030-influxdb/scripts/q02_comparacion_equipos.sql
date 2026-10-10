SELECT
  equipo_codigo,
  AVG(posesion_pct) AS posesion_promedio,
  SUM(pases_completados) AS pases_totales,
  SUM(tiros) AS tiros_totales,
  SUM(recuperaciones) AS recuperaciones_totales,
  AVG(velocidad_kmh) AS velocidad_promedio
FROM estadisticas_partido
WHERE partido_codigo = 'P-01'
  AND time >= '2030-06-15T18:30:00Z'
  AND time < '2030-06-15T18:40:00Z'
GROUP BY equipo_codigo
ORDER BY equipo_codigo;
