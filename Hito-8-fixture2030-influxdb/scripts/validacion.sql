SHOW TABLES;

SHOW COLUMNS IN estadisticas_partido;
SHOW COLUMNS IN usuarios_conectados;

SELECT COUNT(*) AS puntos_estadisticas FROM estadisticas_partido;
SELECT COUNT(*) AS puntos_usuarios FROM usuarios_conectados;

SELECT partido_codigo, COUNT(*) AS puntos
FROM estadisticas_partido
GROUP BY partido_codigo
ORDER BY partido_codigo
LIMIT 15;

SELECT equipo_codigo, COUNT(*) AS puntos
FROM estadisticas_partido
WHERE partido_codigo = 'P-01'
GROUP BY equipo_codigo
ORDER BY equipo_codigo;

SELECT fuente, COUNT(*) AS puntos
FROM estadisticas_partido
WHERE partido_codigo = 'P-01'
GROUP BY fuente
ORDER BY fuente;
