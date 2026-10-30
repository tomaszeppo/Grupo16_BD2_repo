-- BORRADOR NO EJECUTADO. Crear solo en un archivo SQLite nuevo y revisado.
PRAGMA foreign_keys = ON;
CREATE TABLE partidos (
  partido_clave TEXT PRIMARY KEY,
  codigo_neo4j TEXT NOT NULL UNIQUE,
  codigo_cassandra TEXT NOT NULL UNIQUE,
  equipo_local TEXT NOT NULL,
  equipo_visitante TEXT NOT NULL,
  fecha TEXT NOT NULL,
  fuente_commit TEXT NOT NULL,
  verificado_en TEXT NOT NULL
);
CREATE TABLE lotes (
  lote_id TEXT PRIMARY KEY,
  inicio_utc TEXT NOT NULL,
  fin_utc TEXT NOT NULL,
  fuente_commit TEXT NOT NULL,
  dataset_sha256 TEXT NOT NULL
);
CREATE TABLE comentarios_resumen (
  partido_clave TEXT NOT NULL REFERENCES partidos(partido_clave),
  pais TEXT NOT NULL CHECK(length(pais)=3),
  inicio_ventana_utc TEXT NOT NULL,
  cantidad_comentarios INTEGER NOT NULL CHECK(cantidad_comentarios>=0),
  actualizado_en TEXT NOT NULL,
  lote_id TEXT NOT NULL REFERENCES lotes(lote_id),
  PRIMARY KEY(partido_clave,pais,inicio_ventana_utc)
);
CREATE TABLE checkpoints (
  flujo TEXT PRIMARY KEY,
  hasta_ventana_utc TEXT NOT NULL,
  lote_id TEXT NOT NULL REFERENCES lotes(lote_id)
);

