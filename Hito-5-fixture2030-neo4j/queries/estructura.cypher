
// RESTRICCIONES DE UNICIDAD


// Cada equipo se identifica mediante su código de 3 letras.
// Ejemplo: ARG, BRA, ESP...
CREATE CONSTRAINT equipo_codigo_unico IF NOT EXISTS
FOR (e:Equipo)
REQUIRE e.codigo IS UNIQUE;


// Cada jugador tendrá un identificador propio.
// Lo construiremos durante la carga a partir de sus datos.
CREATE CONSTRAINT jugador_id_unico IF NOT EXISTS
FOR (j:Jugador)
REQUIRE j.id IS UNIQUE;


// Cada partido tendrá un identificador único.
CREATE CONSTRAINT partido_id_unico IF NOT EXISTS
FOR (p:Partido)
REQUIRE p.id IS UNIQUE;


// Cada estadio tendrá un identificador único.
CREATE CONSTRAINT estadio_id_unico IF NOT EXISTS
FOR (e:Estadio)
REQUIRE e.id IS UNIQUE;


// Cada evento tendrá un identificador único.
CREATE CONSTRAINT evento_id_unico IF NOT EXISTS
FOR (e:Evento)
REQUIRE e.id IS UNIQUE;


// Cada usuario tiene un identificador propio dentro del módulo social.
CREATE CONSTRAINT usuario_id_unico IF NOT EXISTS
FOR (u:Usuario)
REQUIRE u.idUsuario IS UNIQUE;


// Cada grupo tiene un identificador propio.
CREATE CONSTRAINT grupo_id_unico IF NOT EXISTS
FOR (g:Grupo)
REQUIRE g.idGrupo IS UNIQUE;


// Cada predicción tiene un identificador propio.
CREATE CONSTRAINT prediccion_id_unico IF NOT EXISTS
FOR (pr:Prediccion)
REQUIRE pr.idPrediccion IS UNIQUE;
