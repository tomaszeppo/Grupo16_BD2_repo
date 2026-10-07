SELECT
  region,
  MAX(usuarios_activos) AS pico_usuarios_activos
FROM usuarios_conectados
WHERE partido_id = 'M001'
  AND time >= '2030-06-15T18:30:00Z'
  AND time < '2030-06-15T18:42:00Z'
GROUP BY region
ORDER BY pico_usuarios_activos DESC;
