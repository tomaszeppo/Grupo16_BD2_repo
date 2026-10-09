-- esquema.cql
-- Keyspace y tablas del modulo de comentarios masivos del Fixture 2030.
-- Correr una sola vez, antes de cualquier carga.

-- Ambiente de laboratorio: un solo nodo, por eso SimpleStrategy con RF=1.
-- En un despliegue real multi-region se usaria NetworkTopologyStrategy con
-- un factor de replica por datacenter (ver docs/decisiones_de_particionamiento.md).
CREATE KEYSPACE IF NOT EXISTS fixture2030
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE fixture2030;

-- Tabla principal: comentarios de un partido.
-- Particion = partido_codigo + bucket (ventana de 10 minutos desde el inicio
-- del partido). El bucket evita que un partido muy popular concentre todo
-- en una sola particion (ver decisiones_de_particionamiento.md).
-- Clustering = comentario_id (timeuuid) DESC, para leer lo mas reciente
-- primero sin ordenar en la aplicacion.
-- Resuelve las consultas prioritarias 1, 2, 3, 4 y 5 de patrones_de_acceso.md.
CREATE TABLE IF NOT EXISTS comentarios_por_partido (
    partido_codigo text,
    bucket int,
    comentario_id timeuuid,
    usuario_id text,
    contenido text,
    creado_en timestamp,
    estado_moderacion text,
    likes int,
    PRIMARY KEY ((partido_codigo, bucket), comentario_id)
) WITH CLUSTERING ORDER BY (comentario_id DESC);

-- Tabla secundaria: historial de comentarios por usuario.
-- La tabla principal no permite responder "todos los comentarios de este
-- usuario" sin recorrer todas las particiones (ALLOW FILTERING, prohibido
-- por la consigna como solucion principal). Se duplica el comentario acá,
-- con otra clave, para resolver esa consulta de forma directa.
-- Resuelve la consulta prioritaria 6 de patrones_de_acceso.md.
CREATE TABLE IF NOT EXISTS comentarios_por_usuario (
    usuario_id text,
    creado_en timestamp,
    comentario_id timeuuid,
    partido_codigo text,
    contenido text,
    estado_moderacion text,
    PRIMARY KEY (usuario_id, creado_en, comentario_id)
) WITH CLUSTERING ORDER BY (creado_en DESC, comentario_id DESC);

-- Tabla de referencia (no es una tabla de comentarios): fecha y hora de
-- inicio de cada partido, para poder calcular a que bucket corresponde un
-- comentario nuevo. Usa los mismos codigos de partido que el modulo de
-- grafos del Hito 5 (P-01 a P-32).
CREATE TABLE IF NOT EXISTS partidos_referencia (
    partido_codigo text PRIMARY KEY,
    fecha_inicio timestamp
);
