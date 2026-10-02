/* global use, db */
// MongoDB Playground
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.

// The current database to use.
use("fixture2030");


// operaciones de busqueda RF10
db.equipos.findOne({
    codigo: "ARG"
});

// operaciones de filtrado RF10
db.jugadores.find({
    equipo: "ARG"
});

db.jugadores.find({
    posicion: "Portero"
});

db.jugadores.find({
    dorsal: {
        $gte: 1,
        $lte: 5
    }
});

// ordenamiento

db.jugadores.find().sort({
    apellido: 1 // ordenar alfabeticamente por apellido, de la A a la Z
});

// paginacion - limitar maximo 20 docs
db.jugadores.find()
    .sort({ apellido: 1 })
    .skip(0)
    .limit(20);