SHOW TABLES;

SHOW COLUMNS IN estadisticas_partido;
SHOW COLUMNS IN usuarios_conectados;

SELECT COUNT(*) AS puntos_estadisticas FROM estadisticas_partido;
SELECT COUNT(*) AS puntos_usuarios FROM usuarios_conectados;

SELECT partido_id, COUNT(*) AS puntos
FROM estadisticas_partido
GROUP BY partido_id
ORDER BY partido_id
LIMIT 15;

SELECT equipo_id, COUNT(*) AS puntos
FROM estadisticas_partido
WHERE partido_id = 'M001'
GROUP BY equipo_id
ORDER BY equipo_id;

SELECT fuente, COUNT(*) AS puntos
FROM estadisticas_partido
WHERE partido_id = 'M001'
GROUP BY fuente
ORDER BY fuente;
