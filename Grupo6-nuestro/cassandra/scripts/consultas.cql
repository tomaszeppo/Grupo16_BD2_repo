-- consultas.cql
-- Consultas de lectura del modulo, cada una ligada a un patron concreto de
-- docs/patrones_de_acceso.md. Ninguna usa ALLOW FILTERING como solucion
-- principal (la consigna lo prohibe para consultas frecuentes).

USE fixture2030;

-- 1) Feed en vivo: ultimos comentarios de un partido, en un bucket puntual.
--    Es la consulta mas frecuente del modulo (patron prioritario 1).
--    El orden DESC ya viene dado por el CLUSTERING ORDER de la tabla.
SELECT comentario_id, usuario_id, contenido, creado_en, likes
FROM comentarios_por_partido
WHERE partido_codigo = 'P-01' AND bucket = 1
LIMIT 20;

-- 2) Ventana temporal mas amplia: comentarios de dos buckets consecutivos
--    de un partido (por ejemplo, para "repasar el primer tiempo").
--    IN sobre la parte de la particion sigue resolviendose sin
--    ALLOW FILTERING porque bucket es parte de la clave de particion.
SELECT comentario_id, usuario_id, contenido, creado_en, estado_moderacion
FROM comentarios_por_partido
WHERE partido_codigo = 'P-01' AND bucket IN (0, 1);

-- 3) Historial de un usuario (patron prioritario 6, resuelto por la tabla
--    secundaria en vez de filtrar la tabla principal).
SELECT comentario_id, partido_codigo, contenido, creado_en, estado_moderacion
FROM comentarios_por_usuario
WHERE usuario_id = 'user-00001'
LIMIT 50;

-- 4) Paginacion: misma consulta que la 1, pidiendo la pagina siguiente.
--    En cqlsh esto se ve como un LIMIT mas la salida "---MORE---"; con un
--    driver de aplicacion se usa el paging_state que devuelve la respuesta
--    anterior en vez de repetir el LIMIT a mano.
SELECT comentario_id, usuario_id, contenido, creado_en, likes
FROM comentarios_por_partido
WHERE partido_codigo = 'P-01' AND bucket = 0
LIMIT 20;
