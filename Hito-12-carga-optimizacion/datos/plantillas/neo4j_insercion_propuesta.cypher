// MATERIAL PARA REVISION. NO EJECUTADO. Requiere elegir destino y confirmar colisiones.
// Parametro $partidos: lista de neo4j_parametros.json. Los equipos/estadios deben existir.
// Primero verificar que cada ID existente coincida en equipos, fecha y sede.
// No ejecutar contra el laboratorio H10 con IDs P-NN como solucion de integracion final.
UNWIND $partidos AS row
MATCH (local:Equipo {codigo:row.equipoLocal})
MATCH (visitante:Equipo {codigo:row.equipoVisitante})
MATCH (estadio:Estadio {id:row.estadio})
MERGE (p:Partido {id:row.id})
ON CREATE SET p.fecha=row.fecha,p.fase=row.fase
MERGE (local)-[:PARTICIPA_EN]->(p)
MERGE (visitante)-[:PARTICIPA_EN]->(p)
MERGE (p)-[:SE_JUEGA_EN]->(estadio);

