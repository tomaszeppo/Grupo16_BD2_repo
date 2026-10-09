// consultas_grafo.cypher
// Consultas con patrones de grafo (RF8) y consulta de analisis (RF9).

// --- RF8: recorridos de dos o mas relaciones consecutivas ---

// Recorrido de 3 saltos: Equipo -> Jugador -> Evento -> Partido.
// Responde: "todos los goles convertidos, quien lo hizo y en que partido".
MATCH (e:Equipo)<-[:PERTENECE_A]-(j:Jugador)-[:PROTAGONISTA_DE]->(ev:Evento {tipo:'Gol'})-[:OCURRE_EN]->(p:Partido)
RETURN e.codigo AS equipo, j.codigo AS jugador, p.codigo AS partido, ev.minuto AS minuto
ORDER BY p.codigo;

// Recorrido de 2 saltos: rivales de un equipo a traves de los partidos compartidos.
MATCH (equipo:Equipo {codigo:'ARG'})<-[:DISPUTA]-(p:Partido)-[:DISPUTA]->(rival:Equipo)
WHERE rival.codigo <> 'ARG'
RETURN p.codigo AS partido, rival.codigo AS rival, p.fecha AS fecha
ORDER BY fecha;

// Bonus: equipos que jugaron en una sede determinada (2 saltos).
MATCH (s:Sede {codigo:'EST001'})<-[:SE_JUEGA_EN]-(p:Partido)-[:DISPUTA]->(e:Equipo)
RETURN s.codigo AS sede, p.codigo AS partido, e.codigo AS equipo
ORDER BY p.codigo;


// --- RF9: consulta de camino / conectividad ---
// Usa el patron de camino de la Clase 5 (relacion variable -[*1..N]-),
// no algoritmos de GDS (esos requieren un plugin que la clase no instala).
//
// Objetivo: ver si dos equipos que NO se enfrentan en la muestra estan
// igualmente conectados por otra via (compartir estadio en otro partido).
// Interpretacion: dos selecciones sin partido entre si pueden terminar
// compartiendo estadio y ventana de fechas — algo que no se ve mirando
// un documento aislado de cada partido por separado.
MATCH camino = (a:Equipo {codigo:'ARG'})-[*1..4]-(b:Equipo {codigo:'SCO'})
RETURN camino, length(camino) AS saltos
ORDER BY saltos ASC
LIMIT 1;
