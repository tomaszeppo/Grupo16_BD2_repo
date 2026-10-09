// crud.cypher
// Ejemplos de creacion, lectura, actualizacion y eliminacion sobre el modelo
// ya cargado. Cada operacion de escritura va precedida y seguida de una
// lectura de verificacion, y las eliminaciones usan un patron acotado a un
// solo codigo, como advierte la consigna, para no arrastrar mas de lo pensado.
// Se puede correr entero mas de una vez: termina dejando la base sin el evento
// de prueba P-01-EV3.

// ---------------------------------------------------------------- CREATE
// Antes: el partido P-01 no tiene el evento P-01-EV3 (se espera 0).
MATCH (ev:Evento {codigo: 'P-01-EV3'}) RETURN count(ev) AS evento_ev3_antes;

// Registrar un cambio (sustitucion) en el partido P-01.
MATCH (p:Partido {codigo: 'P-01'})-[:DISPUTA {rol:'local'}]->(local:Equipo)
MATCH (saleCancha:Jugador {dorsal: 9})-[:PERTENECE_A]->(local)
MERGE (evCambio:Evento {codigo: p.codigo + '-EV3'})
ON CREATE SET evCambio.tipo = 'Cambio', evCambio.minuto = 65
MERGE (evCambio)-[:OCURRE_EN]->(p)
MERGE (saleCancha)-[:PROTAGONISTA_DE]->(evCambio);

// Despues: el evento existe, con su partido y su protagonista (se espera 1 fila).
MATCH (j:Jugador)-[:PROTAGONISTA_DE]->(ev:Evento {codigo: 'P-01-EV3'})-[:OCURRE_EN]->(p:Partido)
RETURN j.codigo AS jugador, ev.codigo AS evento, ev.tipo AS tipo, ev.minuto AS minuto, p.codigo AS partido;

// ---------------------------------------------------------------- READ
// Un jugador y el equipo al que pertenece.
MATCH (j:Jugador {codigo: 'ARG-20'})-[:PERTENECE_A]->(e:Equipo)
RETURN j.codigo, j.posicion, e.codigo AS equipo;

// Todos los eventos de un partido, ordenados por minuto.
MATCH (ev:Evento)-[:OCURRE_EN]->(p:Partido {codigo: 'P-01'})
RETURN ev.codigo, ev.tipo, ev.minuto
ORDER BY ev.minuto;

// ---------------------------------------------------------------- UPDATE
// Corregir el minuto de un evento. Antes:
MATCH (ev:Evento {codigo: 'P-01-EV1'}) RETURN ev.codigo AS evento, ev.minuto AS minuto_antes;

MATCH (ev:Evento {codigo: 'P-01-EV1'})
SET ev.minuto = 25
RETURN ev.codigo AS evento, ev.minuto AS minuto_despues;

// El partido pasa de fase. Antes:
MATCH (p:Partido {codigo: 'P-01'}) RETURN p.codigo AS partido, p.fase AS fase_antes;

MATCH (p:Partido {codigo: 'P-01'})
SET p.fase = 'Octavos de final'
RETURN p.codigo AS partido, p.fase AS fase_despues;

// ---------------------------------------------------------------- DELETE
// Borrar puntualmente una relacion (deshacer el protagonismo del cambio).
// Antes (se espera 1):
MATCH (:Jugador)-[r:PROTAGONISTA_DE]->(:Evento {codigo: 'P-01-EV3'}) RETURN count(r) AS relaciones_antes;

MATCH (:Jugador)-[r:PROTAGONISTA_DE]->(:Evento {codigo: 'P-01-EV3'})
DELETE r;

// Despues (se espera 0):
MATCH (:Jugador)-[r:PROTAGONISTA_DE]->(:Evento {codigo: 'P-01-EV3'}) RETURN count(r) AS relaciones_despues;

// Borrar el nodo evento completo (DETACH DELETE, con patron acotado a un solo codigo).
MATCH (ev:Evento {codigo: 'P-01-EV3'})
DETACH DELETE ev;

// Despues (se espera 0):
MATCH (ev:Evento {codigo: 'P-01-EV3'}) RETURN count(ev) AS evento_ev3_despues;
