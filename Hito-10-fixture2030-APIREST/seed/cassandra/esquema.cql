-- Esquema de comentarios (Hito 6, tomado del PDF de documentación) + tabla auxiliar de idempotencia de la API.
CREATE KEYSPACE IF NOT EXISTS fixture2030
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS fixture2030.comentarios_por_partido_pais (
    partido_id text, pais text, ventana timestamp, creado_en timestamp, comentario_id uuid,
    usuario_id text, usuario_nombre text, contenido text, likes int, estado_moderacion text,
    PRIMARY KEY ((partido_id, pais, ventana), creado_en, comentario_id)
) WITH CLUSTERING ORDER BY (creado_en DESC, comentario_id ASC);

CREATE TABLE IF NOT EXISTS fixture2030.comentarios_por_likes_partido_pais (
    partido_id text, pais text, ventana timestamp, likes int, creado_en timestamp, comentario_id uuid,
    usuario_nombre text, contenido text,
    PRIMARY KEY ((partido_id, pais, ventana), likes, creado_en, comentario_id)
) WITH CLUSTERING ORDER BY (likes DESC, creado_en DESC, comentario_id ASC);

-- Tabla auxiliar de la API (no está en main): fija ventana y creado_en del primer intento de cada Idempotency-Key.
CREATE TABLE IF NOT EXISTS fixture2030.comentarios_idempotencia (
    clave text PRIMARY KEY, partido_id text, pais text, ventana timestamp, creado_en timestamp, comentario_id uuid
) WITH default_time_to_live = 86400;
