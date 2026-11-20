-- Comentarios de los partidos. Una copia en cada región (datacenter): cada usuario escribe y lee en la suya.
-- Sin vencimiento: el Mundial dura más de un mes y los comentarios se guardan para el análisis posterior.
CREATE KEYSPACE IF NOT EXISTS fixture2030
  WITH replication = {'class': 'NetworkTopologyStrategy', 'america': 1, 'europa': 1};

-- Partición: partido, país y ventana de 30 minutos (acota el tamaño de cada partición en un partido largo).
-- origen: "usuario" o "simulacion", para separar en el análisis los comentarios automáticos del simulador.
CREATE TABLE IF NOT EXISTS fixture2030.comentarios_por_partido_pais (
  partido_id text, pais text, ventana timestamp, creado_en timestamp, comentario_id uuid,
  usuario_nombre text, contenido text, origen text,
  PRIMARY KEY ((partido_id, pais, ventana), creado_en, comentario_id)
) WITH CLUSTERING ORDER BY (creado_en DESC, comentario_id ASC);
