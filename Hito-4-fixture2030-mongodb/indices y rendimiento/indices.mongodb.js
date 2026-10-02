use("fixture2030");



// eliminar indices anteriores

db.equipos.dropIndexes();
db.jugadores.dropIndexes();


// rendimiento antes de los indices


db.jugadores
  .find({ equipo: "ARG" })
  .explain("executionStats");


print("\n--- Ordenar jugadores por apellido ---");

db.jugadores
  .find()
  .sort({ apellido: 1 })
  .explain("executionStats");


print("\n--- Buscar jugadores por posición ---");

db.jugadores
  .find({ posicion: "Portero" })
  .explain("executionStats");


// crear indices

db.equipos.createIndex(
  { codigo: 1 },
  { unique: true }
);

db.jugadores.createIndex(
  { equipo: 1 }
);

db.jugadores.createIndex(
  { apellido: 1 }
);

db.jugadores.createIndex(
  { posicion: 1 }
);


// mostrar indices creados

print("\nÍndices de equipos:");
printjson(db.equipos.getIndexes());

print("\nÍndices de jugadores:");
printjson(db.jugadores.getIndexes());


// rendimiento después de los indices
print("RENDIMIENTO DESPUÉS DE LOS ÍNDICES");


db.jugadores
  .find({ equipo: "ARG" })
  .explain("executionStats");


print("\n--- Ordenar jugadores por apellido ---");

db.jugadores
  .find()
  .sort({ apellido: 1 })
  .explain("executionStats");


print("\n--- Buscar jugadores por posición ---");

db.jugadores
  .find({ posicion: "Portero" })
  .explain("executionStats");