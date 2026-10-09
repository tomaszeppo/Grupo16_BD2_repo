// carga.cypher
// Carga de datos de prueba: 64 equipos, 1536 jugadores, 10 sedes y los
// 32 partidos con eventos en los primeros 5. Todo con MERGE, para que se
// pueda volver a correr sin duplicar nada (idempotente, ver RNF4).
// Los datos de referencia (equipos, jugadores, sedes) se reescriben con SET.
// La fase y la fecha de cada partido y el tipo y minuto de cada evento van con
// ON CREATE SET: solo se escriben cuando el nodo se crea, asi recargar no pisa
// lo que se haya cambiado despues con crud.cypher.
// Correr despues de estructura.cypher, en el orden en que aparece este archivo.

// --- 1) Equipos ---
UNWIND [
  {codigo:'ARG', confederacion:'CONMEBOL', ranking:1},
  {codigo:'URU', confederacion:'CONMEBOL', ranking:2},
  {codigo:'PAR', confederacion:'CONMEBOL', ranking:3},
  {codigo:'BRA', confederacion:'CONMEBOL', ranking:4},
  {codigo:'COL', confederacion:'CONMEBOL', ranking:5},
  {codigo:'CHI', confederacion:'CONMEBOL', ranking:6},
  {codigo:'ECU', confederacion:'CONMEBOL', ranking:7},
  {codigo:'PER', confederacion:'CONMEBOL', ranking:8},
  {codigo:'ESP', confederacion:'UEFA', ranking:9},
  {codigo:'POR', confederacion:'UEFA', ranking:10},
  {codigo:'MAR', confederacion:'CAF', ranking:11},
  {codigo:'FRA', confederacion:'UEFA', ranking:12},
  {codigo:'GER', confederacion:'UEFA', ranking:13},
  {codigo:'ENG', confederacion:'UEFA', ranking:14},
  {codigo:'ITA', confederacion:'UEFA', ranking:15},
  {codigo:'NED', confederacion:'UEFA', ranking:16},
  {codigo:'BEL', confederacion:'UEFA', ranking:17},
  {codigo:'CRO', confederacion:'UEFA', ranking:18},
  {codigo:'SUI', confederacion:'UEFA', ranking:19},
  {codigo:'DEN', confederacion:'UEFA', ranking:20},
  {codigo:'POL', confederacion:'UEFA', ranking:21},
  {codigo:'SRB', confederacion:'UEFA', ranking:22},
  {codigo:'AUT', confederacion:'UEFA', ranking:23},
  {codigo:'UKR', confederacion:'UEFA', ranking:24},
  {codigo:'WAL', confederacion:'UEFA', ranking:25},
  {codigo:'SCO', confederacion:'UEFA', ranking:26},
  {codigo:'TUR', confederacion:'UEFA', ranking:27},
  {codigo:'SWE', confederacion:'UEFA', ranking:28},
  {codigo:'CZE', confederacion:'UEFA', ranking:29},
  {codigo:'NOR', confederacion:'UEFA', ranking:30},
  {codigo:'HUN', confederacion:'UEFA', ranking:31},
  {codigo:'GRE', confederacion:'UEFA', ranking:32},
  {codigo:'JPN', confederacion:'AFC', ranking:33},
  {codigo:'KOR', confederacion:'AFC', ranking:34},
  {codigo:'IRN', confederacion:'AFC', ranking:35},
  {codigo:'KSA', confederacion:'AFC', ranking:36},
  {codigo:'AUS', confederacion:'AFC', ranking:37},
  {codigo:'QAT', confederacion:'AFC', ranking:38},
  {codigo:'IRQ', confederacion:'AFC', ranking:39},
  {codigo:'CHN', confederacion:'AFC', ranking:40},
  {codigo:'ISL', confederacion:'AFC', ranking:41},
  {codigo:'UAE', confederacion:'AFC', ranking:42},
  {codigo:'SEN', confederacion:'CAF', ranking:43},
  {codigo:'NGA', confederacion:'CAF', ranking:44},
  {codigo:'EGY', confederacion:'CAF', ranking:45},
  {codigo:'ALG', confederacion:'CAF', ranking:46},
  {codigo:'TUN', confederacion:'CAF', ranking:47},
  {codigo:'CMR', confederacion:'CAF', ranking:48},
  {codigo:'GHA', confederacion:'CAF', ranking:49},
  {codigo:'CIV', confederacion:'CAF', ranking:50},
  {codigo:'RSA', confederacion:'CAF', ranking:51},
  {codigo:'COD', confederacion:'CAF', ranking:52},
  {codigo:'MEX', confederacion:'CONCACAF', ranking:53},
  {codigo:'USA', confederacion:'CONCACAF', ranking:54},
  {codigo:'CAN', confederacion:'CONCACAF', ranking:55},
  {codigo:'CRC', confederacion:'CONCACAF', ranking:56},
  {codigo:'JAM', confederacion:'CONCACAF', ranking:57},
  {codigo:'PAN', confederacion:'CONCACAF', ranking:58},
  {codigo:'HON', confederacion:'CONCACAF', ranking:59},
  {codigo:'NZL', confederacion:'OFC', ranking:60},
  {codigo:'VEN', confederacion:'CONMEBOL', ranking:61},
  {codigo:'ROU', confederacion:'CONMEBOL', ranking:62},
  {codigo:'IRL', confederacion:'UEFA', ranking:63},
  {codigo:'RUS', confederacion:'UEFA', ranking:64}
] AS fila
MERGE (e:Equipo {codigo: fila.codigo})
SET e.confederacion = fila.confederacion, e.ranking = fila.ranking;


// --- 2) Jugadores (24 por equipo = 1536 en total) ---
MATCH (e:Equipo)
UNWIND range(1, 24) AS dorsal
WITH e, dorsal,
     CASE WHEN dorsal <= 3 THEN 'Portero'
          WHEN dorsal <= 11 THEN 'Defensa'
          WHEN dorsal <= 19 THEN 'Centrocampista'
          ELSE 'Delantero' END AS posicion,
     CASE WHEN dorsal < 10 THEN '0' + toString(dorsal) ELSE toString(dorsal) END AS dorsalStr
MERGE (j:Jugador {codigo: e.codigo + '-' + dorsalStr})
SET j.posicion = posicion, j.dorsal = dorsal
MERGE (j)-[:PERTENECE_A]->(e);


// --- 3) Sedes (10 estadios) ---
UNWIND [
  {codigo:'EST001', nombre:'Estadio Monumental', ciudad:'Buenos Aires'},
  {codigo:'EST002', nombre:'Maracaná', ciudad:'Río de Janeiro'},
  {codigo:'EST003', nombre:'Camp Nou', ciudad:'Barcelona'},
  {codigo:'EST004', nombre:'Wembley', ciudad:'Londres'},
  {codigo:'EST005', nombre:'Stade de France', ciudad:'París'},
  {codigo:'EST006', nombre:'Allianz Arena', ciudad:'Múnich'},
  {codigo:'EST007', nombre:'Azteca', ciudad:'Ciudad de México'},
  {codigo:'EST008', nombre:'Lusail Stadium', ciudad:'Lusail'},
  {codigo:'EST009', nombre:'Saitama Stadium', ciudad:'Saitama'},
  {codigo:'EST010', nombre:'BC Place', ciudad:'Vancouver'}
] AS fila
MERGE (s:Sede {codigo: fila.codigo})
SET s.nombre = fila.nombre, s.ciudad = fila.ciudad;


// --- 4) Partidos: los 32 del fixture de la fase de grupos, con su sede ---
// La fase y la fecha van con ON CREATE SET. El resultado es simulado: el
// fixture de prueba no tiene resultados oficiales, y por eso se marca con
// origenResultado = 'SIMULADO'.
UNWIND [
  {numero:1, local:'ARG', visitante:'BRA', sede:'EST001', fecha:'2030-06-15', fase:'Fase de grupos', ganador:'ARG', perdedor:'BRA', golesGanador:1, golesPerdedor:0},
  {numero:2, local:'ESP', visitante:'FRA', sede:'EST002', fecha:'2030-06-15', fase:'Fase de grupos', ganador:'ESP', perdedor:'FRA', golesGanador:1, golesPerdedor:0},
  {numero:3, local:'GER', visitante:'ENG', sede:'EST003', fecha:'2030-06-15', fase:'Fase de grupos', ganador:'GER', perdedor:'ENG', golesGanador:1, golesPerdedor:0},
  {numero:4, local:'ITA', visitante:'POR', sede:'EST004', fecha:'2030-06-15', fase:'Fase de grupos', ganador:'ITA', perdedor:'POR', golesGanador:1, golesPerdedor:0},
  {numero:5, local:'NED', visitante:'BEL', sede:'EST005', fecha:'2030-06-16', fase:'Fase de grupos', ganador:'NED', perdedor:'BEL', golesGanador:1, golesPerdedor:0},
  {numero:6, local:'CRO', visitante:'URU', sede:'EST006', fecha:'2030-06-16', fase:'Fase de grupos', ganador:'CRO', perdedor:'URU', golesGanador:1, golesPerdedor:0},
  {numero:7, local:'MEX', visitante:'USA', sede:'EST007', fecha:'2030-06-16', fase:'Fase de grupos', ganador:'MEX', perdedor:'USA', golesGanador:1, golesPerdedor:0},
  {numero:8, local:'CAN', visitante:'JPN', sede:'EST008', fecha:'2030-06-16', fase:'Fase de grupos', ganador:'CAN', perdedor:'JPN', golesGanador:1, golesPerdedor:0},
  {numero:9, local:'KOR', visitante:'AUS', sede:'EST009', fecha:'2030-06-17', fase:'Fase de grupos', ganador:'KOR', perdedor:'AUS', golesGanador:1, golesPerdedor:0},
  {numero:10, local:'MAR', visitante:'SEN', sede:'EST010', fecha:'2030-06-17', fase:'Fase de grupos', ganador:'MAR', perdedor:'SEN', golesGanador:1, golesPerdedor:0},
  {numero:11, local:'GHA', visitante:'NGA', sede:'EST001', fecha:'2030-06-17', fase:'Fase de grupos', ganador:'GHA', perdedor:'NGA', golesGanador:1, golesPerdedor:0},
  {numero:12, local:'CMR', visitante:'TUN', sede:'EST002', fecha:'2030-06-17', fase:'Fase de grupos', ganador:'CMR', perdedor:'TUN', golesGanador:1, golesPerdedor:0},
  {numero:13, local:'EGY', visitante:'ALG', sede:'EST003', fecha:'2030-06-18', fase:'Fase de grupos', ganador:'EGY', perdedor:'ALG', golesGanador:1, golesPerdedor:0},
  {numero:14, local:'COL', visitante:'CHI', sede:'EST004', fecha:'2030-06-18', fase:'Fase de grupos', ganador:'COL', perdedor:'CHI', golesGanador:1, golesPerdedor:0},
  {numero:15, local:'PER', visitante:'ECU', sede:'EST005', fecha:'2030-06-18', fase:'Fase de grupos', ganador:'PER', perdedor:'ECU', golesGanador:1, golesPerdedor:0},
  {numero:16, local:'PAR', visitante:'VEN', sede:'EST006', fecha:'2030-06-18', fase:'Fase de grupos', ganador:'PAR', perdedor:'VEN', golesGanador:1, golesPerdedor:0},
  {numero:17, local:'SUI', visitante:'AUT', sede:'EST007', fecha:'2030-06-19', fase:'Fase de grupos', ganador:'SUI', perdedor:'AUT', golesGanador:1, golesPerdedor:0},
  {numero:18, local:'POL', visitante:'SWE', sede:'EST008', fecha:'2030-06-19', fase:'Fase de grupos', ganador:'POL', perdedor:'SWE', golesGanador:1, golesPerdedor:0},
  {numero:19, local:'DEN', visitante:'NOR', sede:'EST009', fecha:'2030-06-19', fase:'Fase de grupos', ganador:'DEN', perdedor:'NOR', golesGanador:1, golesPerdedor:0},
  {numero:20, local:'SRB', visitante:'WAL', sede:'EST010', fecha:'2030-06-19', fase:'Fase de grupos', ganador:'SRB', perdedor:'WAL', golesGanador:1, golesPerdedor:0},
  {numero:21, local:'SCO', visitante:'IRL', sede:'EST001', fecha:'2030-06-20', fase:'Fase de grupos', ganador:'SCO', perdedor:'IRL', golesGanador:1, golesPerdedor:0},
  {numero:22, local:'UKR', visitante:'RUS', sede:'EST002', fecha:'2030-06-20', fase:'Fase de grupos', ganador:'UKR', perdedor:'RUS', golesGanador:1, golesPerdedor:0},
  {numero:23, local:'TUR', visitante:'GRE', sede:'EST003', fecha:'2030-06-20', fase:'Fase de grupos', ganador:'TUR', perdedor:'GRE', golesGanador:1, golesPerdedor:0},
  {numero:24, local:'ROU', visitante:'CZE', sede:'EST004', fecha:'2030-06-20', fase:'Fase de grupos', ganador:'ROU', perdedor:'CZE', golesGanador:1, golesPerdedor:0},
  {numero:25, local:'HUN', visitante:'ISL', sede:'EST005', fecha:'2030-06-21', fase:'Fase de grupos', ganador:'HUN', perdedor:'ISL', golesGanador:1, golesPerdedor:0},
  {numero:26, local:'CRC', visitante:'PAN', sede:'EST006', fecha:'2030-06-21', fase:'Fase de grupos', ganador:'CRC', perdedor:'PAN', golesGanador:1, golesPerdedor:0},
  {numero:27, local:'JAM', visitante:'HON', sede:'EST007', fecha:'2030-06-21', fase:'Fase de grupos', ganador:'JAM', perdedor:'HON', golesGanador:1, golesPerdedor:0},
  {numero:28, local:'KSA', visitante:'IRN', sede:'EST008', fecha:'2030-06-21', fase:'Fase de grupos', ganador:'KSA', perdedor:'IRN', golesGanador:1, golesPerdedor:0},
  {numero:29, local:'QAT', visitante:'UAE', sede:'EST009', fecha:'2030-06-22', fase:'Fase de grupos', ganador:'QAT', perdedor:'UAE', golesGanador:1, golesPerdedor:0},
  {numero:30, local:'IRQ', visitante:'CHN', sede:'EST010', fecha:'2030-06-22', fase:'Fase de grupos', ganador:'IRQ', perdedor:'CHN', golesGanador:1, golesPerdedor:0},
  {numero:31, local:'NZL', visitante:'RSA', sede:'EST001', fecha:'2030-06-22', fase:'Fase de grupos', ganador:'NZL', perdedor:'RSA', golesGanador:1, golesPerdedor:0},
  {numero:32, local:'CIV', visitante:'COD', sede:'EST002', fecha:'2030-06-22', fase:'Fase de grupos', ganador:'CIV', perdedor:'COD', golesGanador:1, golesPerdedor:0}
] AS fila
MATCH (local:Equipo {codigo: fila.local})
MATCH (visitante:Equipo {codigo: fila.visitante})
MATCH (s:Sede {codigo: fila.sede})
WITH fila, local, visitante, s,
     CASE WHEN fila.numero < 10 THEN '0' + toString(fila.numero) ELSE toString(fila.numero) END AS numeroStr
MERGE (p:Partido {codigo: 'P-' + numeroStr})
ON CREATE SET p.fase = fila.fase, p.fecha = date(fila.fecha),
              p.equipoGanador = fila.ganador, p.equipoPerdedor = fila.perdedor,
              p.golesGanador = fila.golesGanador, p.golesPerdedor = fila.golesPerdedor,
              p.origenResultado = 'SIMULADO'
MERGE (p)-[:DISPUTA {rol: 'local'}]->(local)
MERGE (p)-[:DISPUTA {rol: 'visitante'}]->(visitante)
MERGE (p)-[:SE_JUEGA_EN]->(s);


// --- 5) Eventos de muestra en los primeros 5 partidos ---
MATCH (p:Partido) WHERE p.codigo IN ['P-01','P-02','P-03','P-04','P-05']
MATCH (p)-[:DISPUTA {rol:'local'}]->(local:Equipo)
MATCH (p)-[:DISPUTA {rol:'visitante'}]->(visitante:Equipo)
MATCH (goleador:Jugador {dorsal: 20})-[:PERTENECE_A]->(local)
MATCH (amonestado:Jugador {dorsal: 5})-[:PERTENECE_A]->(visitante)
MERGE (evGol:Evento {codigo: p.codigo + '-EV1'})
ON CREATE SET evGol.tipo = 'Gol', evGol.minuto = 23
MERGE (evGol)-[:OCURRE_EN]->(p)
MERGE (goleador)-[:PROTAGONISTA_DE]->(evGol)
MERGE (evTarjeta:Evento {codigo: p.codigo + '-EV2'})
ON CREATE SET evTarjeta.tipo = 'TarjetaAmarilla', evTarjeta.minuto = 41
MERGE (evTarjeta)-[:OCURRE_EN]->(p)
MERGE (amonestado)-[:PROTAGONISTA_DE]->(evTarjeta);
