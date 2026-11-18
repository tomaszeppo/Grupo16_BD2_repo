CREATE KEYSPACE IF NOT EXISTS fixture2030 WITH replication = {'class':'SimpleStrategy','replication_factor':1};
CREATE TABLE IF NOT EXISTS fixture2030.comentarios_por_partido_pais (
 partido_id text, pais text, ventana timestamp, creado_en timestamp, comentario_id uuid,
 usuario_nombre text, contenido text,
 PRIMARY KEY ((partido_id, pais, ventana), creado_en, comentario_id)
) WITH CLUSTERING ORDER BY (creado_en DESC, comentario_id ASC);
