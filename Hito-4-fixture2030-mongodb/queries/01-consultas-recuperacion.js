// 01-consultas-recuperacion.js
// Consultas de recuperacion (RF10): identificacion directa, filtrado, proyeccion,
// ordenamiento y paginacion, mas las dos agregaciones (RF11). Se pueden pegar
// de a bloques en mongosh o correr el archivo entero (ver README); en ese caso
// cada resultado se imprime con printjson.

db = db.getSiblingDB("fixture2030");

// --- Equipos ---

// Identificacion directa por codigo (usa el indice unico ix_equipos_codigo_unico).
printjson(db.equipos.findOne({ codigo: "ARG" }));

// Filtrado: equipos de una confederacion.
printjson(db.equipos.find({ confederacion: "CONMEBOL" }).sort({ ranking: 1 }).toArray());

// Proyeccion: solo los campos necesarios para una grilla.
printjson(db.equipos.find(
  { confederacion: "CONMEBOL" },
  { _id: 0, codigo: 1, nombre: 1, ranking: 1 }
).sort({ ranking: 1 }).toArray());

// Ordenamiento y paginacion (por ejemplo, una grilla de 10 equipos por pagina).
printjson(db.equipos.find({}, { _id: 0, codigo: 1, ranking: 1 }).sort({ ranking: 1 }).skip(0).limit(10).toArray());   // pagina 1
printjson(db.equipos.find({}, { _id: 0, codigo: 1, ranking: 1 }).sort({ ranking: 1 }).skip(10).limit(10).toArray());  // pagina 2

// --- Jugadores ---

// Identificacion directa por codigo.
printjson(db.jugadores.findOne({ codigo: "ARG-10" }));

// Filtrado: plantilla completa de un equipo (usa ix_jugadores_equipoCodigo).
print("Plantilla de ARG: " + db.jugadores.find({ equipoCodigo: "ARG" }).sort({ dorsal: 1 }).toArray().length + " jugadores");

// Filtrado mas especifico: delanteros convocados de un equipo
// (usa el indice compuesto ix_jugadores_equipo_posicion_convocado).
printjson(db.jugadores.find({
  equipoCodigo: "ARG",
  posicion: "Delantero",
  convocado: true
}, { _id: 0, codigo: 1, nombre: 1 }).toArray());

// Proyeccion: solo nombre y posicion de la plantilla de un equipo.
printjson(db.jugadores.find(
  { equipoCodigo: "BRA" },
  { _id: 0, nombre: 1, posicion: 1, dorsal: 1 }
).sort({ dorsal: 1 }).limit(5).toArray());

// Filtrado por rango: dorsales del 1 al 5 de un equipo.
printjson(db.jugadores.find(
  { equipoCodigo: "ARG", dorsal: { $gte: 1, $lte: 5 } },
  { _id: 0, codigo: 1, apellido: 1, dorsal: 1 }
).sort({ dorsal: 1 }).toArray());

// Ordenamiento alfabetico por apellido con paginacion (usa ix_jugadores_apellido).
printjson(db.jugadores.find({}, { _id: 0, codigo: 1, apellido: 1, nombre: 1 })
  .sort({ apellido: 1, codigo: 1 }).skip(0).limit(5).toArray());

// --- Agregacion (RF11) ---

// 1) Cantidad de jugadores convocados y anio de nacimiento promedio por equipo.
printjson(db.jugadores.aggregate([
  { $match: { convocado: true } },
  {
    $group: {
      _id: "$equipoCodigo",
      cantidadJugadores: { $sum: 1 },
      anioNacimientoPromedio: { $avg: { $year: "$fechaNacimiento" } }
    }
  },
  { $sort: { cantidadJugadores: -1 } },
  { $limit: 10 }
]).toArray());

// 2) Cantidad de equipos y de jugadores por confederacion (cruza ambas
//    colecciones con $lookup, el equivalente a un JOIN en MongoDB).
printjson(db.equipos.aggregate([
  {
    $lookup: {
      from: "jugadores",
      localField: "codigo",
      foreignField: "equipoCodigo",
      as: "plantilla"
    }
  },
  {
    $group: {
      _id: "$confederacion",
      cantidadEquipos: { $sum: 1 },
      cantidadJugadores: { $sum: { $size: "$plantilla" } }
    }
  },
  { $sort: { cantidadEquipos: -1 } }
]).toArray());

// 3) Cantidad de jugadores por posicion.
printjson(db.jugadores.aggregate([
  { $group: { _id: "$posicion", cantidadJugadores: { $sum: 1 } } },
  { $sort: { cantidadJugadores: -1 } },
  { $project: { _id: 0, posicion: "$_id", cantidadJugadores: 1 } }
]).toArray());

// Integridad referencial (MongoDB no tiene claves foraneas): jugadores cuyo
// equipoCodigo no corresponde a ningun equipo. Esperado: lista vacia.
printjson(db.jugadores.aggregate([
  { $lookup: { from: "equipos", localField: "equipoCodigo", foreignField: "codigo", as: "equipo" } },
  { $match: { equipo: { $size: 0 } } },
  { $project: { _id: 0, codigo: 1, equipoCodigo: 1 } }
]).toArray());
