-- Consulta sobre la proyeccion existente; no se extrae nuevamente de Cassandra.
-- Usuarios activos por minuto; no se suman como usuarios unicos del periodo.
SELECT partido_codigo, minuto_utc, comentarios, usuarios_activos,
       comentarios_visibles, comentarios_otro_estado, likes_total
FROM actividad_comentarios
ORDER BY comentarios DESC, partido_codigo, minuto_utc;

SELECT SUM(comentarios) AS comentarios_integrados,
       SUM(comentarios_visibles) AS visibles,
       SUM(comentarios_otro_estado) AS otros_estados
FROM actividad_comentarios;
