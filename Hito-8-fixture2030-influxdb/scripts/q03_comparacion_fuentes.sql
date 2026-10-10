SELECT
  fuente,
  AVG(posesion_pct) AS posesion_promedio,
  SUM(pases_completados) AS pases_totales,
  SUM(tiros) AS tiros_totales
FROM estadisticas_partido
WHERE partido_codigo = 'P-01'
  AND time >= '2030-06-15T18:30:00Z'
  AND time < '2030-06-15T18:40:00Z'
GROUP BY fuente
ORDER BY fuente;
