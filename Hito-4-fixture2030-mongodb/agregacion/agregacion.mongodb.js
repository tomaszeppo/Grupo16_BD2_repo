use("fixture2030");



// cantidad de jugadores por equipo

db.equipos.aggregate([
  {
    $lookup: {
      from: "jugadores",
      localField: "codigo",
      foreignField: "equipo",
      as: "jugadores"
    }
  },
  {
    $project: {
      _id: 0,
      equipo: "$nombre",
      codigo: 1,
      cantidadJugadores: { $size: "$jugadores" }
    }
  },
  {
    $sort: {
      cantidadJugadores: -1
    }
  }
]);

// jugadores por posicion

db.jugadores.aggregate([
  {
    $group: {
      _id: "$posicion",
      cantidadJugadores: { $sum: 1 }
    }
  },
  {
    $sort: {
      cantidadJugadores: -1
    }
  },
  {
    $project: {
      _id: 0,
      posicion: "$_id",
      cantidadJugadores: 1
    }
  }
]);