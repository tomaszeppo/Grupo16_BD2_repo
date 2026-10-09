-- crud.cql
-- Operaciones de creacion, recuperacion, actualizacion y eliminacion (RF8)
-- sobre las DOS tablas de comentarios, por fuera de la carga masiva. Se corre
-- de punta a punta sin editar nada:
--   docker exec fixture2030-cassandra cqlsh -f /scripts/crud.cql
-- Requiere esquema.cql. Cada operacion va precedida o seguida de un SELECT de
-- verificacion por clave completa (nunca se lee una particion entera, que en la
-- carga masiva tiene miles de filas). Termina dejando las tablas como estaban,
-- asi que se puede repetir y tampoco altera los conteos de la carga masiva.
--
-- El comentario_id es un timeuuid fijo y valido (version 1), el mismo para las
-- dos tablas; en una aplicacion real lo genera el cliente para poder usar el
-- mismo valor en las dos tablas (como en la carga masiva).

USE fixture2030;

-- ---------------------------------------------------------------- CREATE
-- Antes: el comentario no existe en ninguna de las dos tablas (0 filas).
SELECT comentario_id, contenido, estado_moderacion
FROM comentarios_por_partido
WHERE partido_codigo = 'P-01' AND bucket = 0 AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

SELECT comentario_id, contenido, estado_moderacion
FROM comentarios_por_usuario
WHERE usuario_id = 'user-00099' AND creado_en = '2030-06-08 18:05:00+0000' AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

-- Alta del comentario en las dos tablas (duplicacion controlada).
INSERT INTO comentarios_por_partido
    (partido_codigo, bucket, comentario_id, usuario_id, contenido, creado_en, estado_moderacion, likes)
VALUES
    ('P-01', 0, c4d8e1a0-6d3b-11ef-9b2a-0242ac120002, 'user-00099', 'Comentario de prueba para CRUD', '2030-06-08 18:05:00+0000', 'visible', 0);

INSERT INTO comentarios_por_usuario
    (usuario_id, creado_en, comentario_id, partido_codigo, contenido, estado_moderacion)
VALUES
    ('user-00099', '2030-06-08 18:05:00+0000', c4d8e1a0-6d3b-11ef-9b2a-0242ac120002, 'P-01', 'Comentario de prueba para CRUD', 'visible');

-- ---------------------------------------------------------------- READ
-- Despues del alta: el comentario aparece en las dos tablas (1 fila cada una).
SELECT * FROM comentarios_por_partido
WHERE partido_codigo = 'P-01' AND bucket = 0 AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

SELECT * FROM comentarios_por_usuario
WHERE usuario_id = 'user-00099' AND creado_en = '2030-06-08 18:05:00+0000' AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

-- Lectura por la clave de acceso de cada tabla: el historial del usuario
-- y los 5 comentarios mas recientes de la ventana del partido.
SELECT usuario_id, creado_en, partido_codigo, contenido FROM comentarios_por_usuario
WHERE usuario_id = 'user-00099' LIMIT 5;

SELECT comentario_id, usuario_id, contenido FROM comentarios_por_partido
WHERE partido_codigo = 'P-01' AND bucket = 0 LIMIT 5;

-- ---------------------------------------------------------------- UPDATE
-- Moderar un comentario puntual en las dos tablas. Hace falta la clave
-- completa (particion + clustering), nunca se modera filtrando por otro campo.
UPDATE comentarios_por_partido
SET estado_moderacion = 'oculto'
WHERE partido_codigo = 'P-01' AND bucket = 0 AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

UPDATE comentarios_por_usuario
SET estado_moderacion = 'oculto'
WHERE usuario_id = 'user-00099' AND creado_en = '2030-06-08 18:05:00+0000' AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

-- Despues: estado_moderacion pasa de 'visible' a 'oculto' en las dos tablas.
SELECT comentario_id, estado_moderacion FROM comentarios_por_partido
WHERE partido_codigo = 'P-01' AND bucket = 0 AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

SELECT comentario_id, estado_moderacion FROM comentarios_por_usuario
WHERE usuario_id = 'user-00099' AND creado_en = '2030-06-08 18:05:00+0000' AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

-- ---------------------------------------------------------------- DELETE
-- Eliminacion controlada de un comentario puntual, tambien por clave completa
-- (nunca un DELETE sin filtro o con filtro parcial), en las dos tablas.
DELETE FROM comentarios_por_partido
WHERE partido_codigo = 'P-01' AND bucket = 0 AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

DELETE FROM comentarios_por_usuario
WHERE usuario_id = 'user-00099' AND creado_en = '2030-06-08 18:05:00+0000' AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

-- Despues: ya no queda ninguna fila (0 filas en cada tabla).
SELECT comentario_id, estado_moderacion FROM comentarios_por_partido
WHERE partido_codigo = 'P-01' AND bucket = 0 AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;

SELECT comentario_id, estado_moderacion FROM comentarios_por_usuario
WHERE usuario_id = 'user-00099' AND creado_en = '2030-06-08 18:05:00+0000' AND comentario_id = c4d8e1a0-6d3b-11ef-9b2a-0242ac120002;
