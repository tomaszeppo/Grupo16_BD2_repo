// verificar_carga.cypher
// Conteos de nodos y relaciones. Valores esperados despues de carga.cypher
// (y antes de crud.cypher, que agrega y quita un evento):
//   nodos:      Equipo 64 | Jugador 1536 | Sede 10 | Partido 32 | Evento 10
//   relaciones: PERTENECE_A 1536 | DISPUTA 64 | SE_JUEGA_EN 32 | OCURRE_EN 10 | PROTAGONISTA_DE 10

MATCH (e:Equipo) WITH count(e) AS equipos
MATCH (j:Jugador) WITH equipos, count(j) AS jugadores
MATCH (s:Sede) WITH equipos, jugadores, count(s) AS sedes
MATCH (p:Partido) WITH equipos, jugadores, sedes, count(p) AS partidos
MATCH (ev:Evento) WITH equipos, jugadores, sedes, partidos, count(ev) AS eventos
RETURN equipos, jugadores, sedes, partidos, eventos;

MATCH ()-[r:PERTENECE_A]->() WITH count(r) AS pertenece_a
MATCH ()-[r:DISPUTA]->() WITH pertenece_a, count(r) AS disputa
MATCH ()-[r:SE_JUEGA_EN]->() WITH pertenece_a, disputa, count(r) AS se_juega_en
MATCH ()-[r:OCURRE_EN]->() WITH pertenece_a, disputa, se_juega_en, count(r) AS ocurre_en
MATCH ()-[r:PROTAGONISTA_DE]->() WITH pertenece_a, disputa, se_juega_en, ocurre_en, count(r) AS protagonista_de
RETURN pertenece_a, disputa, se_juega_en, ocurre_en, protagonista_de;
