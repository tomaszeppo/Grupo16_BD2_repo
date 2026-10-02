

// 10 estadios de prueba.
UNWIND [
  {id: "EST001", nombre: "Estadio Monumental", ciudad: "Buenos Aires"},
  {id: "EST002", nombre: "Maracaná", ciudad: "Río de Janeiro"},
  {id: "EST003", nombre: "Camp Nou", ciudad: "Barcelona"},
  {id: "EST004", nombre: "Wembley", ciudad: "Londres"},
  {id: "EST005", nombre: "Stade de France", ciudad: "París"},
  {id: "EST006", nombre: "Allianz Arena", ciudad: "Múnich"},
  {id: "EST007", nombre: "Azteca", ciudad: "Ciudad de México"},
  {id: "EST008", nombre: "Lusail Stadium", ciudad: "Lusail"},
  {id: "EST009", nombre: "Saitama Stadium", ciudad: "Saitama"},
  {id: "EST010", nombre: "BC Place", ciudad: "Vancouver"}
] AS row
MERGE (e:Estadio {id: row.id})
SET e.nombre = row.nombre, e.ciudad = row.ciudad;

// 32 partidos de prueba. Se utilizan exclusivamente equipos del Hito 4.
UNWIND [
  {id: "P001", equipoLocal: "ARG", equipoVisitante: "BRA", estadio: "EST001", fecha: "2030-06-15", fase: "Fase de grupos"},
  {id: "P002", equipoLocal: "ESP", equipoVisitante: "FRA", estadio: "EST002", fecha: "2030-06-15", fase: "Fase de grupos"},
  {id: "P003", equipoLocal: "GER", equipoVisitante: "ENG", estadio: "EST003", fecha: "2030-06-15", fase: "Fase de grupos"},
  {id: "P004", equipoLocal: "ITA", equipoVisitante: "POR", estadio: "EST004", fecha: "2030-06-15", fase: "Fase de grupos"},
  {id: "P005", equipoLocal: "NED", equipoVisitante: "BEL", estadio: "EST005", fecha: "2030-06-16", fase: "Fase de grupos"},
  {id: "P006", equipoLocal: "CRO", equipoVisitante: "URU", estadio: "EST006", fecha: "2030-06-16", fase: "Fase de grupos"},
  {id: "P007", equipoLocal: "MEX", equipoVisitante: "USA", estadio: "EST007", fecha: "2030-06-16", fase: "Fase de grupos"},
  {id: "P008", equipoLocal: "CAN", equipoVisitante: "JPN", estadio: "EST008", fecha: "2030-06-16", fase: "Fase de grupos"},
  {id: "P009", equipoLocal: "KOR", equipoVisitante: "AUS", estadio: "EST009", fecha: "2030-06-17", fase: "Fase de grupos"},
  {id: "P010", equipoLocal: "MAR", equipoVisitante: "SEN", estadio: "EST010", fecha: "2030-06-17", fase: "Fase de grupos"},
  {id: "P011", equipoLocal: "GHA", equipoVisitante: "NGA", estadio: "EST001", fecha: "2030-06-17", fase: "Fase de grupos"},
  {id: "P012", equipoLocal: "CMR", equipoVisitante: "TUN", estadio: "EST002", fecha: "2030-06-17", fase: "Fase de grupos"},
  {id: "P013", equipoLocal: "EGY", equipoVisitante: "ALG", estadio: "EST003", fecha: "2030-06-18", fase: "Fase de grupos"},
  {id: "P014", equipoLocal: "COL", equipoVisitante: "CHI", estadio: "EST004", fecha: "2030-06-18", fase: "Fase de grupos"},
  {id: "P015", equipoLocal: "PER", equipoVisitante: "ECU", estadio: "EST005", fecha: "2030-06-18", fase: "Fase de grupos"},
  {id: "P016", equipoLocal: "PAR", equipoVisitante: "VEN", estadio: "EST006", fecha: "2030-06-18", fase: "Fase de grupos"},
  {id: "P017", equipoLocal: "SUI", equipoVisitante: "AUT", estadio: "EST007", fecha: "2030-06-19", fase: "Fase de grupos"},
  {id: "P018", equipoLocal: "POL", equipoVisitante: "SWE", estadio: "EST008", fecha: "2030-06-19", fase: "Fase de grupos"},
  {id: "P019", equipoLocal: "DEN", equipoVisitante: "NOR", estadio: "EST009", fecha: "2030-06-19", fase: "Fase de grupos"},
  {id: "P020", equipoLocal: "SRB", equipoVisitante: "WAL", estadio: "EST010", fecha: "2030-06-19", fase: "Fase de grupos"},
  {id: "P021", equipoLocal: "SCO", equipoVisitante: "IRL", estadio: "EST001", fecha: "2030-06-20", fase: "Fase de grupos"},
  {id: "P022", equipoLocal: "UKR", equipoVisitante: "RUS", estadio: "EST002", fecha: "2030-06-20", fase: "Fase de grupos"},
  {id: "P023", equipoLocal: "TUR", equipoVisitante: "GRE", estadio: "EST003", fecha: "2030-06-20", fase: "Fase de grupos"},
  {id: "P024", equipoLocal: "ROU", equipoVisitante: "CZE", estadio: "EST004", fecha: "2030-06-20", fase: "Fase de grupos"},
  {id: "P025", equipoLocal: "HUN", equipoVisitante: "ISL", estadio: "EST005", fecha: "2030-06-21", fase: "Fase de grupos"},
  {id: "P026", equipoLocal: "CRC", equipoVisitante: "PAN", estadio: "EST006", fecha: "2030-06-21", fase: "Fase de grupos"},
  {id: "P027", equipoLocal: "JAM", equipoVisitante: "HON", estadio: "EST007", fecha: "2030-06-21", fase: "Fase de grupos"},
  {id: "P028", equipoLocal: "KSA", equipoVisitante: "IRN", estadio: "EST008", fecha: "2030-06-21", fase: "Fase de grupos"},
  {id: "P029", equipoLocal: "QAT", equipoVisitante: "UAE", estadio: "EST009", fecha: "2030-06-22", fase: "Fase de grupos"},
  {id: "P030", equipoLocal: "IRQ", equipoVisitante: "CHN", estadio: "EST010", fecha: "2030-06-22", fase: "Fase de grupos"},
  {id: "P031", equipoLocal: "NZL", equipoVisitante: "RSA", estadio: "EST001", fecha: "2030-06-22", fase: "Fase de grupos"},
  {id: "P032", equipoLocal: "CIV", equipoVisitante: "COD", estadio: "EST002", fecha: "2030-06-22", fase: "Fase de grupos"}
] AS row
MERGE (p:Partido {id: row.id})
SET p.fecha = row.fecha, p.fase = row.fase
WITH p, row
MATCH (local:Equipo {codigo: row.equipoLocal})
MATCH (visitante:Equipo {codigo: row.equipoVisitante})
MATCH (estadio:Estadio {id: row.estadio})
MERGE (local)-[:PARTICIPA_EN]->(p)
MERGE (visitante)-[:PARTICIPA_EN]->(p)
MERGE (p)-[:SE_JUEGA_EN]->(estadio);

// 3 eventos por partido: inicio, gol y final.
UNWIND [
  {id: "EV-P001-INICIO", tipo: "Inicio", minuto: 0, partido: "P001"},
  {id: "EV-P001-GOL", tipo: "Gol", minuto: 32, partido: "P001"},
  {id: "EV-P001-FINAL", tipo: "Final", minuto: 90, partido: "P001"},
  {id: "EV-P002-INICIO", tipo: "Inicio", minuto: 0, partido: "P002"},
  {id: "EV-P002-GOL", tipo: "Gol", minuto: 32, partido: "P002"},
  {id: "EV-P002-FINAL", tipo: "Final", minuto: 90, partido: "P002"},
  {id: "EV-P003-INICIO", tipo: "Inicio", minuto: 0, partido: "P003"},
  {id: "EV-P003-GOL", tipo: "Gol", minuto: 32, partido: "P003"},
  {id: "EV-P003-FINAL", tipo: "Final", minuto: 90, partido: "P003"},
  {id: "EV-P004-INICIO", tipo: "Inicio", minuto: 0, partido: "P004"},
  {id: "EV-P004-GOL", tipo: "Gol", minuto: 32, partido: "P004"},
  {id: "EV-P004-FINAL", tipo: "Final", minuto: 90, partido: "P004"},
  {id: "EV-P005-INICIO", tipo: "Inicio", minuto: 0, partido: "P005"},
  {id: "EV-P005-GOL", tipo: "Gol", minuto: 32, partido: "P005"},
  {id: "EV-P005-FINAL", tipo: "Final", minuto: 90, partido: "P005"},
  {id: "EV-P006-INICIO", tipo: "Inicio", minuto: 0, partido: "P006"},
  {id: "EV-P006-GOL", tipo: "Gol", minuto: 32, partido: "P006"},
  {id: "EV-P006-FINAL", tipo: "Final", minuto: 90, partido: "P006"},
  {id: "EV-P007-INICIO", tipo: "Inicio", minuto: 0, partido: "P007"},
  {id: "EV-P007-GOL", tipo: "Gol", minuto: 32, partido: "P007"},
  {id: "EV-P007-FINAL", tipo: "Final", minuto: 90, partido: "P007"},
  {id: "EV-P008-INICIO", tipo: "Inicio", minuto: 0, partido: "P008"},
  {id: "EV-P008-GOL", tipo: "Gol", minuto: 32, partido: "P008"},
  {id: "EV-P008-FINAL", tipo: "Final", minuto: 90, partido: "P008"},
  {id: "EV-P009-INICIO", tipo: "Inicio", minuto: 0, partido: "P009"},
  {id: "EV-P009-GOL", tipo: "Gol", minuto: 32, partido: "P009"},
  {id: "EV-P009-FINAL", tipo: "Final", minuto: 90, partido: "P009"},
  {id: "EV-P010-INICIO", tipo: "Inicio", minuto: 0, partido: "P010"},
  {id: "EV-P010-GOL", tipo: "Gol", minuto: 32, partido: "P010"},
  {id: "EV-P010-FINAL", tipo: "Final", minuto: 90, partido: "P010"},
  {id: "EV-P011-INICIO", tipo: "Inicio", minuto: 0, partido: "P011"},
  {id: "EV-P011-GOL", tipo: "Gol", minuto: 32, partido: "P011"},
  {id: "EV-P011-FINAL", tipo: "Final", minuto: 90, partido: "P011"},
  {id: "EV-P012-INICIO", tipo: "Inicio", minuto: 0, partido: "P012"},
  {id: "EV-P012-GOL", tipo: "Gol", minuto: 32, partido: "P012"},
  {id: "EV-P012-FINAL", tipo: "Final", minuto: 90, partido: "P012"},
  {id: "EV-P013-INICIO", tipo: "Inicio", minuto: 0, partido: "P013"},
  {id: "EV-P013-GOL", tipo: "Gol", minuto: 32, partido: "P013"},
  {id: "EV-P013-FINAL", tipo: "Final", minuto: 90, partido: "P013"},
  {id: "EV-P014-INICIO", tipo: "Inicio", minuto: 0, partido: "P014"},
  {id: "EV-P014-GOL", tipo: "Gol", minuto: 32, partido: "P014"},
  {id: "EV-P014-FINAL", tipo: "Final", minuto: 90, partido: "P014"},
  {id: "EV-P015-INICIO", tipo: "Inicio", minuto: 0, partido: "P015"},
  {id: "EV-P015-GOL", tipo: "Gol", minuto: 32, partido: "P015"},
  {id: "EV-P015-FINAL", tipo: "Final", minuto: 90, partido: "P015"},
  {id: "EV-P016-INICIO", tipo: "Inicio", minuto: 0, partido: "P016"},
  {id: "EV-P016-GOL", tipo: "Gol", minuto: 32, partido: "P016"},
  {id: "EV-P016-FINAL", tipo: "Final", minuto: 90, partido: "P016"},
  {id: "EV-P017-INICIO", tipo: "Inicio", minuto: 0, partido: "P017"},
  {id: "EV-P017-GOL", tipo: "Gol", minuto: 32, partido: "P017"},
  {id: "EV-P017-FINAL", tipo: "Final", minuto: 90, partido: "P017"},
  {id: "EV-P018-INICIO", tipo: "Inicio", minuto: 0, partido: "P018"},
  {id: "EV-P018-GOL", tipo: "Gol", minuto: 32, partido: "P018"},
  {id: "EV-P018-FINAL", tipo: "Final", minuto: 90, partido: "P018"},
  {id: "EV-P019-INICIO", tipo: "Inicio", minuto: 0, partido: "P019"},
  {id: "EV-P019-GOL", tipo: "Gol", minuto: 32, partido: "P019"},
  {id: "EV-P019-FINAL", tipo: "Final", minuto: 90, partido: "P019"},
  {id: "EV-P020-INICIO", tipo: "Inicio", minuto: 0, partido: "P020"},
  {id: "EV-P020-GOL", tipo: "Gol", minuto: 32, partido: "P020"},
  {id: "EV-P020-FINAL", tipo: "Final", minuto: 90, partido: "P020"},
  {id: "EV-P021-INICIO", tipo: "Inicio", minuto: 0, partido: "P021"},
  {id: "EV-P021-GOL", tipo: "Gol", minuto: 32, partido: "P021"},
  {id: "EV-P021-FINAL", tipo: "Final", minuto: 90, partido: "P021"},
  {id: "EV-P022-INICIO", tipo: "Inicio", minuto: 0, partido: "P022"},
  {id: "EV-P022-GOL", tipo: "Gol", minuto: 32, partido: "P022"},
  {id: "EV-P022-FINAL", tipo: "Final", minuto: 90, partido: "P022"},
  {id: "EV-P023-INICIO", tipo: "Inicio", minuto: 0, partido: "P023"},
  {id: "EV-P023-GOL", tipo: "Gol", minuto: 32, partido: "P023"},
  {id: "EV-P023-FINAL", tipo: "Final", minuto: 90, partido: "P023"},
  {id: "EV-P024-INICIO", tipo: "Inicio", minuto: 0, partido: "P024"},
  {id: "EV-P024-GOL", tipo: "Gol", minuto: 32, partido: "P024"},
  {id: "EV-P024-FINAL", tipo: "Final", minuto: 90, partido: "P024"},
  {id: "EV-P025-INICIO", tipo: "Inicio", minuto: 0, partido: "P025"},
  {id: "EV-P025-GOL", tipo: "Gol", minuto: 32, partido: "P025"},
  {id: "EV-P025-FINAL", tipo: "Final", minuto: 90, partido: "P025"},
  {id: "EV-P026-INICIO", tipo: "Inicio", minuto: 0, partido: "P026"},
  {id: "EV-P026-GOL", tipo: "Gol", minuto: 32, partido: "P026"},
  {id: "EV-P026-FINAL", tipo: "Final", minuto: 90, partido: "P026"},
  {id: "EV-P027-INICIO", tipo: "Inicio", minuto: 0, partido: "P027"},
  {id: "EV-P027-GOL", tipo: "Gol", minuto: 32, partido: "P027"},
  {id: "EV-P027-FINAL", tipo: "Final", minuto: 90, partido: "P027"},
  {id: "EV-P028-INICIO", tipo: "Inicio", minuto: 0, partido: "P028"},
  {id: "EV-P028-GOL", tipo: "Gol", minuto: 32, partido: "P028"},
  {id: "EV-P028-FINAL", tipo: "Final", minuto: 90, partido: "P028"},
  {id: "EV-P029-INICIO", tipo: "Inicio", minuto: 0, partido: "P029"},
  {id: "EV-P029-GOL", tipo: "Gol", minuto: 32, partido: "P029"},
  {id: "EV-P029-FINAL", tipo: "Final", minuto: 90, partido: "P029"},
  {id: "EV-P030-INICIO", tipo: "Inicio", minuto: 0, partido: "P030"},
  {id: "EV-P030-GOL", tipo: "Gol", minuto: 32, partido: "P030"},
  {id: "EV-P030-FINAL", tipo: "Final", minuto: 90, partido: "P030"},
  {id: "EV-P031-INICIO", tipo: "Inicio", minuto: 0, partido: "P031"},
  {id: "EV-P031-GOL", tipo: "Gol", minuto: 32, partido: "P031"},
  {id: "EV-P031-FINAL", tipo: "Final", minuto: 90, partido: "P031"},
  {id: "EV-P032-INICIO", tipo: "Inicio", minuto: 0, partido: "P032"},
  {id: "EV-P032-GOL", tipo: "Gol", minuto: 32, partido: "P032"},
  {id: "EV-P032-FINAL", tipo: "Final", minuto: 90, partido: "P032"}
] AS row
MERGE (e:Evento {id: row.id})
SET e.tipo = row.tipo, e.minuto = row.minuto
WITH e, row
MATCH (p:Partido {id: row.partido})
MERGE (e)-[:OCURRE_EN]->(p);

// Comprobación final.
MATCH (p:Partido)
WITH count(p) AS partidos
MATCH (e:Estadio)
WITH partidos, count(e) AS estadios
MATCH (ev:Evento)
RETURN partidos, estadios, count(ev) AS eventos;
