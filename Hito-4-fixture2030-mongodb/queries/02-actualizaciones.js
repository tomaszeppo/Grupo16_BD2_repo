// 02-actualizaciones.js
// Insercion y actualizacion (RF9). Todas incluyen un filtro especifico.
// Cada update imprime matchedCount y el script corta con error si no encontro
// exactamente el documento esperado (un update que no encuentra nada no da error
// por si solo, por eso se comprueba a mano).
// Para correrlo (ver README):
//   mongosh ... fixture2030 --file /queries/02-actualizaciones.js

db = db.getSiblingDB("fixture2030");

function comprobar(descripcion, resultado, esperado) {
  print(descripcion + " -> matchedCount: " + resultado.matchedCount +
        ", modifiedCount: " + resultado.modifiedCount);
  if (resultado.matchedCount !== esperado) {
    throw new Error("No coincide la cantidad esperada (" + esperado + ") en: " + descripcion);
  }
}

// --- Insercion ---

// Agregar un nuevo equipo (validado por el $jsonSchema de 01-create-collections.js).
db.equipos.insertOne({
  codigo: "TST",
  nombre: "Equipo de prueba",
  confederacion: "UEFA",
  ranking: NumberInt(65),
  sedeBase: "Ciudad de prueba",
  cantidadJugadoresConvocados: NumberInt(0)
});
print("Equipo TST insertado. Equipos en la base: " + db.equipos.countDocuments());

// Agregar un nuevo jugador para ese equipo.
db.jugadores.insertOne({
  codigo: "TST-01",
  equipoCodigo: "TST",
  nombre: "Jugador",
  apellido: "de prueba",
  posicion: "Delantero",
  dorsal: NumberInt(1),
  fechaNacimiento: new Date("2005-01-01"),
  convocado: true
});
print("Jugador TST-01 insertado. Jugadores en la base: " + db.jugadores.countDocuments());

// --- Sobre equipos ---

// Actualizar el ranking de un equipo (por ejemplo, tras una actualizacion oficial).
comprobar("ranking de MAR", db.equipos.updateOne(
  { codigo: "MAR" },
  { $set: { ranking: NumberInt(10) } }
), 1);

// --- Sobre jugadores ---

// Marcar un jugador como no convocado (por lesion, por ejemplo).
comprobar("JPN-07 no convocado", db.jugadores.updateOne(
  { codigo: "JPN-07" },
  { $set: { convocado: false } }
), 1);

// Corregir el nombre de un jugador (su codigo no cambia).
comprobar("nombre de ARG-10", db.jugadores.updateOne(
  { codigo: "ARG-10" },
  { $set: { nombre: "Lionel" } }
), 1);

// Actualizar varios jugadores que cumplan una condicion (por ejemplo, volver a
// convocar a los tres porteros de un equipo). Esperado: los 3 de ARG.
comprobar("porteros de ARG convocados", db.jugadores.updateMany(
  { equipoCodigo: "ARG", posicion: "Portero" },
  { $set: { convocado: true } }
), 3);

// Corregir el apellido de un jugador.
comprobar("apellido de BRA-05", db.jugadores.updateOne(
  { codigo: "BRA-05" },
  { $set: { apellido: "Da Silva" } }
), 1);

// Mantener el contador desnormalizado de "equipos.cantidadJugadoresConvocados"
// despues de un cambio de convocatoria.
comprobar("contador de convocados de JPN", db.equipos.updateOne(
  { codigo: "JPN" },
  {
    $set: {
      cantidadJugadoresConvocados: NumberInt(db.jugadores.countDocuments({
        equipoCodigo: "JPN",
        convocado: true
      }))
    }
  }
), 1);

printjson(db.equipos.findOne({ codigo: "JPN" }, { _id: 0, codigo: 1, cantidadJugadoresConvocados: 1 }));

// --- Limpieza de los documentos de prueba ---
const delJ = db.jugadores.deleteOne({ codigo: "TST-01" });
const delE = db.equipos.deleteOne({ codigo: "TST" });
print("Borrados de prueba -> jugador: " + delJ.deletedCount + ", equipo: " + delE.deletedCount);
print("Totales finales -> equipos: " + db.equipos.countDocuments() +
      ", jugadores: " + db.jugadores.countDocuments());
