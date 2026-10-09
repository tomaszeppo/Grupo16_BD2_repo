// 03-analisis-indices.js
// Analisis de rendimiento: explain() con y sin indice (RF12).
// Los indices ya se crean en init-scripts/02-create-indexes.js, asi que para
// comparar hay que sacar el indice, correr la consulta y volver a crearlo.
//   mongosh ... fixture2030 --file /queries/03-analisis-indices.js

db = db.getSiblingDB("fixture2030");

function resumen(titulo) {
  const e = db.jugadores.find({ equipoCodigo: "ARG" }).explain("executionStats");
  const s = e.executionStats;
  // La etapa de entrada puede estar anidada (FETCH -> IXSCAN); se baja hasta la hoja.
  let etapa = e.queryPlanner.winningPlan;
  while (etapa.inputStage) etapa = etapa.inputStage;
  print(titulo);
  print("  etapa: " + etapa.stage + (etapa.indexName ? " (" + etapa.indexName + ")" : ""));
  print("  nReturned: " + s.nReturned + " | totalKeysExamined: " + s.totalKeysExamined +
        " | totalDocsExamined: " + s.totalDocsExamined +
        " | executionTimeMillis: " + s.executionTimeMillis);
}

// 1) Con el indice ix_jugadores_equipoCodigo (y el compuesto, que tambien empieza por equipoCodigo).
//    Se fuerza el simple con hint para que la comparacion sea clara.
function resumenConHint(titulo) {
  const e = db.jugadores.find({ equipoCodigo: "ARG" }).hint("ix_jugadores_equipoCodigo").explain("executionStats");
  const s = e.executionStats;
  let etapa = e.queryPlanner.winningPlan;
  while (etapa.inputStage) etapa = etapa.inputStage;
  print(titulo);
  print("  etapa: " + etapa.stage + " (" + etapa.indexName + ")");
  print("  nReturned: " + s.nReturned + " | totalKeysExamined: " + s.totalKeysExamined +
        " | totalDocsExamined: " + s.totalDocsExamined +
        " | executionTimeMillis: " + s.executionTimeMillis);
}

// 2) Sin los dos indices que empiezan por equipoCodigo la consulta recorre toda la coleccion.
resumenConHint("CON indice ix_jugadores_equipoCodigo:");

db.jugadores.dropIndex("ix_jugadores_equipoCodigo");
db.jugadores.dropIndex("ix_jugadores_equipo_posicion_convocado");
resumen("SIN indices por equipoCodigo (esperado COLLSCAN y 1536 documentos examinados):");

// 3) Se vuelven a crear para dejar el ambiente como estaba.
db.jugadores.createIndex({ equipoCodigo: 1 }, { name: "ix_jugadores_equipoCodigo" });
db.jugadores.createIndex(
  { equipoCodigo: 1, posicion: 1, convocado: 1 },
  { name: "ix_jugadores_equipo_posicion_convocado" }
);
resumen("De nuevo CON indices (plan elegido por el optimizador):");

// 4) Indices existentes.
printjson(db.jugadores.getIndexes().map((i) => i.name));
