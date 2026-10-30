-- Ejecutar contra el SQLite de una extraccion validada, no contra Cassandra.
-- El grano es partido y minuto UTC; usuarios activos no son aditivos entre minutos.
SELECT partido_codigo, minuto_utc, comentarios, usuarios_activos,
       comentarios_visibles, comentarios_otro_estado, likes_total
FROM actividad_comentarios
ORDER BY comentarios DESC, partido_codigo, minuto_utc;

SELECT SUM(comentarios) AS comentarios_integrados,
       SUM(comentarios_visibles) AS visibles,
       SUM(comentarios_otro_estado) AS otros_estados
FROM actividad_comentarios;
