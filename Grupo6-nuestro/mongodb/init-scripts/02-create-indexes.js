// 02-create-indexes.js
// Crea los indices alineados con las consultas definidas en /queries (RF12).
// El criterio para elegir cada uno esta desarrollado en docs/decisiones-de-diseno.md.

db = db.getSiblingDB("fixture2030");

print("Creando indices en 'equipos'...");

// Busqueda directa por codigo (la consulta mas frecuente sobre un equipo puntual).
db.equipos.createIndex({ codigo: 1 }, { unique: true, name: "ix_equipos_codigo_unico" });

// Filtros habituales: equipos de una confederacion, ordenados por ranking.
db.equipos.createIndex({ confederacion: 1, ranking: 1 }, { name: "ix_equipos_confederacion_ranking" });

print("Creando indices en 'jugadores'...");

// Codigo unico de jugador.
db.jugadores.createIndex({ codigo: 1 }, { unique: true, name: "ix_jugadores_codigo_unico" });

// La consulta que mas se repite en todo el modulo: traer la plantilla de un equipo.
db.jugadores.createIndex({ equipoCodigo: 1 }, { name: "ix_jugadores_equipoCodigo" });

// El modulo ordena jugadores alfabeticamente por apellido.
db.jugadores.createIndex({ apellido: 1 }, { name: "ix_jugadores_apellido" });

// Variante habitual de esa misma consulta: plantilla filtrada por posicion y convocatoria.
db.jugadores.createIndex(
  { equipoCodigo: 1, posicion: 1, convocado: 1 },
  { name: "ix_jugadores_equipo_posicion_convocado" }
);

print("Indices creados.");
