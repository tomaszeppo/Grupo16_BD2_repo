
// CONSULTA 1 - Jugadores de un equipo
// Patrón + filtro + ordenamiento


// Pregunta: ¿Qué jugadores pertenecen a Argentina?
MATCH (j:Jugador)-[:PERTENECE_A]->(e:Equipo {codigo: "ARG"})
RETURN j.id AS id,
       j.nombre AS nombre,
       j.apellido AS apellido,
       j.dorsal AS dorsal,
       j.posicion AS posicion
ORDER BY j.apellido, j.nombre;



// CONSULTA 2 - Partidos y estadio de un equipo
// Recorrido de 2 relaciones consecutivas

// Pregunta: ¿En qué partidos y estadios juega Argentina?
MATCH (e:Equipo {codigo: "ARG"})
      -[:PARTICIPA_EN]->(p:Partido)
      -[:SE_JUEGA_EN]->(est:Estadio)
RETURN e.nombre AS equipo,
       p.id AS partido,
       p.fecha AS fecha,
       p.fase AS fase,
       p.equipoGanador + " " + toString(p.golesGanador) + "-" +
         toString(p.golesPerdedor) + " " + p.equipoPerdedor AS resultado_simulado,
       p.origenResultado AS origen_resultado,
       est.nombre AS estadio,
       est.ciudad AS ciudad
ORDER BY p.fecha;


// CONSULTA 3 - Eventos de los partidos de un equipo
// Recorrido de 2 relaciones consecutivas

// Pregunta: ¿Qué eventos están registrados en los partidos de Argentina?
MATCH (e:Equipo {codigo: "ARG"})
      -[:PARTICIPA_EN]->(p:Partido)
      <-[:OCURRE_EN]-(ev:Evento)
RETURN e.nombre AS equipo,
       p.id AS partido,
       ev.id AS evento,
       ev.tipo AS tipo,
       ev.minuto AS minuto
ORDER BY p.fecha, ev.minuto;


// CONSULTA 4 - Jugadores que llegan hasta un estadio
// Recorrido de 3 relaciones consecutivas

// Pregunta: ¿Qué jugadores están vinculados, a través de su equipo
// y un partido, con el Estadio Monumental?
MATCH (j:Jugador)-[:PERTENECE_A]->(e:Equipo)
      -[:PARTICIPA_EN]->(p:Partido)
      -[:SE_JUEGA_EN]->(est:Estadio {id: "EST001"})
RETURN j.nombre AS nombre,
       j.apellido AS apellido,
       e.nombre AS equipo,
       p.id AS partido,
       est.nombre AS estadio
ORDER BY e.nombre, j.apellido, j.nombre;



// CONSULTA 5 - Equipos relacionados con eventos de gol
// Recorrido de 3 relaciones consecutivas


// Pregunta: ¿Qué equipos tienen partidos en los que existe un evento de gol?
MATCH (e:Equipo)-[:PARTICIPA_EN]->(p:Partido)
      <-[:OCURRE_EN]-(ev:Evento {tipo: "Gol"})
RETURN e.codigo AS codigo,
       e.nombre AS equipo,
       count(DISTINCT p) AS partidos_con_gol
ORDER BY partidos_con_gol DESC, equipo;



// CONSULTA 6 - Camino más corto entre un jugador y un estadio
// Análisis relacional requerido por RF9


// Objetivo: mostrar cómo una entidad deportiva puede estar conectada
// con una sede mediante un recorrido del grafo.

// Usamos un jugador real del Hito 4 cargado en Neo4j.
MATCH (j:Jugador {id: "J-ARG-0020"}),
      (est:Estadio {id: "EST001"})
MATCH path = shortestPath((j)-[*..6]-(est))
RETURN j.id AS jugador,
       j.nombre + " " + j.apellido AS nombre_completo,
       est.nombre AS estadio,
       length(path) AS saltos,
       [n IN nodes(path) | labels(n)[0] + ":" + coalesce(n.nombre, n.id)] AS camino;



// CONSULTA 7 - Resumen de conectividad por equipo


// Pregunta: ¿Cuántos partidos y jugadores están conectados con cada equipo?
MATCH (e:Equipo)
OPTIONAL MATCH (j:Jugador)-[:PERTENECE_A]->(e)
WITH e, count(DISTINCT j) AS jugadores
OPTIONAL MATCH (e)-[:PARTICIPA_EN]->(p:Partido)
RETURN e.codigo AS codigo,
       e.nombre AS equipo,
       jugadores,
       count(DISTINCT p) AS partidos
ORDER BY partidos DESC, equipo;



// CONSULTA 8 - Resultados consolidados de los partidos de prueba.
// Los marcadores pertenecen al fixture simulado, no a una predicción de usuario.
MATCH (p:Partido)
RETURN p.id AS partido,
       p.fecha AS fecha,
       p.fase AS fase,
       p.equipoGanador AS equipo_ganador,
       p.golesGanador AS goles_ganador,
       p.golesPerdedor AS goles_perdedor,
       p.equipoPerdedor AS equipo_perdedor,
       p.origenResultado AS origen_resultado
ORDER BY p.fecha, p.id;
