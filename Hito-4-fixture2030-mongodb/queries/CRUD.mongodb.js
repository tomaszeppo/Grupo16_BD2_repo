/* global use, db */
// MongoDB Playground
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.

// The current database to use.
use("fixture2030");


// operaciones de actualización, eliminación e inserción RF9

db.equipos.updateOne(
    { nombre: "República Democrática del Congo", codigo: "COD" },
    { $set: { nombre: "República Democrática de Congo", codigo: "COD" } }
);

db.equipos.deleteOne({
    nombre: "República Democrática del Congo",
    codigo: "COD"
});

db.equipos.insertOne({
    nombre: "República Democrática del Congo",
    codigo: "COD"
});
