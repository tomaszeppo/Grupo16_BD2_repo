// RESULTADOS SIMULADOS DE LOS PARTIDOS
//
// Esta ampliación responde al modelo solicitado para Partido:
// equipoGanador, equipoPerdedor, golesGanador y golesPerdedor.
//
// El Fixture 2030 es un conjunto de prueba y no incluye resultados oficiales.
// Por eso todos los marcadores se identifican con origenResultado = "SIMULADO".
// No se derivan de las predicciones ni se usan para modificar Prediccion.
//
// Ejecutar después de carga_partidos.cypher. El bloque es idempotente: sólo
// actualiza partidos y valida que ganador y perdedor participen realmente.

UNWIND [
  {id: "P001", ganadorCodigo: "ARG", perdedorCodigo: "BRA", golesGanador: 1, golesPerdedor: 0},
  {id: "P002", ganadorCodigo: "ESP", perdedorCodigo: "FRA", golesGanador: 1, golesPerdedor: 0},
  {id: "P003", ganadorCodigo: "GER", perdedorCodigo: "ENG", golesGanador: 1, golesPerdedor: 0},
  {id: "P004", ganadorCodigo: "ITA", perdedorCodigo: "POR", golesGanador: 1, golesPerdedor: 0},
  {id: "P005", ganadorCodigo: "NED", perdedorCodigo: "BEL", golesGanador: 1, golesPerdedor: 0},
  {id: "P006", ganadorCodigo: "CRO", perdedorCodigo: "URU", golesGanador: 1, golesPerdedor: 0},
  {id: "P007", ganadorCodigo: "MEX", perdedorCodigo: "USA", golesGanador: 1, golesPerdedor: 0},
  {id: "P008", ganadorCodigo: "CAN", perdedorCodigo: "JPN", golesGanador: 1, golesPerdedor: 0},
  {id: "P009", ganadorCodigo: "KOR", perdedorCodigo: "AUS", golesGanador: 1, golesPerdedor: 0},
  {id: "P010", ganadorCodigo: "MAR", perdedorCodigo: "SEN", golesGanador: 1, golesPerdedor: 0},
  {id: "P011", ganadorCodigo: "GHA", perdedorCodigo: "NGA", golesGanador: 1, golesPerdedor: 0},
  {id: "P012", ganadorCodigo: "CMR", perdedorCodigo: "TUN", golesGanador: 1, golesPerdedor: 0},
  {id: "P013", ganadorCodigo: "EGY", perdedorCodigo: "ALG", golesGanador: 1, golesPerdedor: 0},
  {id: "P014", ganadorCodigo: "COL", perdedorCodigo: "CHI", golesGanador: 1, golesPerdedor: 0},
  {id: "P015", ganadorCodigo: "PER", perdedorCodigo: "ECU", golesGanador: 1, golesPerdedor: 0},
  {id: "P016", ganadorCodigo: "PAR", perdedorCodigo: "VEN", golesGanador: 1, golesPerdedor: 0},
  {id: "P017", ganadorCodigo: "SUI", perdedorCodigo: "AUT", golesGanador: 1, golesPerdedor: 0},
  {id: "P018", ganadorCodigo: "POL", perdedorCodigo: "SWE", golesGanador: 1, golesPerdedor: 0},
  {id: "P019", ganadorCodigo: "DEN", perdedorCodigo: "NOR", golesGanador: 1, golesPerdedor: 0},
  {id: "P020", ganadorCodigo: "SRB", perdedorCodigo: "WAL", golesGanador: 1, golesPerdedor: 0},
  {id: "P021", ganadorCodigo: "SCO", perdedorCodigo: "IRL", golesGanador: 1, golesPerdedor: 0},
  {id: "P022", ganadorCodigo: "UKR", perdedorCodigo: "RUS", golesGanador: 1, golesPerdedor: 0},
  {id: "P023", ganadorCodigo: "TUR", perdedorCodigo: "GRE", golesGanador: 1, golesPerdedor: 0},
  {id: "P024", ganadorCodigo: "ROU", perdedorCodigo: "CZE", golesGanador: 1, golesPerdedor: 0},
  {id: "P025", ganadorCodigo: "HUN", perdedorCodigo: "ISL", golesGanador: 1, golesPerdedor: 0},
  {id: "P026", ganadorCodigo: "CRC", perdedorCodigo: "PAN", golesGanador: 1, golesPerdedor: 0},
  {id: "P027", ganadorCodigo: "JAM", perdedorCodigo: "HON", golesGanador: 1, golesPerdedor: 0},
  {id: "P028", ganadorCodigo: "KSA", perdedorCodigo: "IRN", golesGanador: 1, golesPerdedor: 0},
  {id: "P029", ganadorCodigo: "QAT", perdedorCodigo: "UAE", golesGanador: 1, golesPerdedor: 0},
  {id: "P030", ganadorCodigo: "IRQ", perdedorCodigo: "CHN", golesGanador: 1, golesPerdedor: 0},
  {id: "P031", ganadorCodigo: "NZL", perdedorCodigo: "RSA", golesGanador: 1, golesPerdedor: 0},
  {id: "P032", ganadorCodigo: "CIV", perdedorCodigo: "COD", golesGanador: 1, golesPerdedor: 0}
] AS row
MATCH (p:Partido {id: row.id})
MATCH (ganador:Equipo {codigo: row.ganadorCodigo})-[:PARTICIPA_EN]->(p)
MATCH (perdedor:Equipo {codigo: row.perdedorCodigo})-[:PARTICIPA_EN]->(p)
WHERE ganador <> perdedor
  AND row.golesGanador > row.golesPerdedor
  AND row.golesPerdedor >= 0
SET p.equipoGanador = ganador.nombre,
    p.equipoPerdedor = perdedor.nombre,
    p.golesGanador = row.golesGanador,
    p.golesPerdedor = row.golesPerdedor,
    p.origenResultado = "SIMULADO"
RETURN count(DISTINCT p) AS partidos_actualizados;


// Control de integridad. Debe devolver cero filas.
MATCH (p:Partido)
WHERE p.equipoGanador IS NULL
   OR p.equipoPerdedor IS NULL
   OR p.golesGanador IS NULL
   OR p.golesPerdedor IS NULL
   OR p.golesGanador <= p.golesPerdedor
   OR coalesce(p.origenResultado, "") <> "SIMULADO"
RETURN p.id AS partido_incompleto,
       p.equipoGanador AS equipo_ganador,
       p.equipoPerdedor AS equipo_perdedor,
       p.golesGanador AS goles_ganador,
       p.golesPerdedor AS goles_perdedor,
       p.origenResultado AS origen_resultado
ORDER BY partido_incompleto;
