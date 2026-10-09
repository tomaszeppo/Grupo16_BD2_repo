// estructura.cypher
// Restricciones de unicidad e indices. Correr antes que cualquier carga de datos.

// --- Restricciones de unicidad (tambien crean un indice automaticamente) ---
CREATE CONSTRAINT equipo_codigo_unico IF NOT EXISTS FOR (e:Equipo) REQUIRE e.codigo IS UNIQUE;
CREATE CONSTRAINT jugador_codigo_unico IF NOT EXISTS FOR (j:Jugador) REQUIRE j.codigo IS UNIQUE;
CREATE CONSTRAINT partido_codigo_unico IF NOT EXISTS FOR (p:Partido) REQUIRE p.codigo IS UNIQUE;
CREATE CONSTRAINT sede_codigo_unico IF NOT EXISTS FOR (s:Sede) REQUIRE s.codigo IS UNIQUE;
CREATE CONSTRAINT evento_codigo_unico IF NOT EXISTS FOR (ev:Evento) REQUIRE ev.codigo IS UNIQUE;

// --- Indices sobre patrones de recuperacion frecuentes ---
// Filtrar eventos por tipo (por ejemplo, "todos los goles").
CREATE INDEX evento_tipo_idx IF NOT EXISTS FOR (ev:Evento) ON (ev.tipo);
// Ordenar o filtrar partidos por fecha (la "programacion" que pide el hito).
CREATE INDEX partido_fecha_idx IF NOT EXISTS FOR (p:Partido) ON (p.fecha);

// Verificar lo creado:
SHOW CONSTRAINTS;
SHOW INDEXES;
