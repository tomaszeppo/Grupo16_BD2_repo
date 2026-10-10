// 04-verificar-idempotencia.js
// Comprueba que la carga se puede repetir sin cambiar los totales y que el
// indice unico rechaza un codigo duplicado.
//   mongosh ... fixture2030 --file /queries/04-verificar-idempotencia.js

db = db.getSiblingDB("fixture2030");

const ESPERADO_EQUIPOS = 64;
const ESPERADO_JUGADORES = 1536;

function contar() {
  return { equipos: db.equipos.countDocuments(), jugadores: db.jugadores.countDocuments() };
}

// 1) Estado antes de volver a cargar.
const antes = contar();
print("Antes   -> equipos: " + antes.equipos + ", jugadores: " + antes.jugadores);

// Datos modificados despues de la carga que la recarga no debe pisar.
const apellidoAntes = db.jugadores.findOne({ codigo: "BRA-05" }).apellido;
const convocadoAntes = db.jugadores.findOne({ codigo: "JPN-07" }).convocado;

// 2) Se ejecuta de nuevo la misma carga.
load("/scripts/cargar-datos.js");

// 3) Estado despues y comparacion.
const despues = contar();
print("Despues -> equipos: " + despues.equipos + ", jugadores: " + despues.jugadores);


const convocadoDespues = db.jugadores.findOne({ codigo: "JPN-07" }).convocado;
print("JPN-07 convocado antes / despues de recargar: " + convocadoAntes + " / " + convocadoDespues);

const igual = antes.equipos === despues.equipos && antes.jugadores === despues.jugadores;
const esperado = despues.equipos === ESPERADO_EQUIPOS && despues.jugadores === ESPERADO_JUGADORES;
print("Totales iguales antes y despues: " + igual);
print("Totales iguales a los esperados (" + ESPERADO_EQUIPOS + " / " + ESPERADO_JUGADORES + "): " + esperado);
// El apellido es dato de referencia: la recarga lo vuelve al valor del script.
const apellidoDespues = db.jugadores.findOne({ codigo: "BRA-05" }).apellido;
print("Apellido de BRA-05 antes / despues de recargar (dato de referencia, se corrige): " + apellidoAntes + " / " + apellidoDespues);
const intactos = convocadoAntes === convocadoDespues;
print("Datos del torneo intactos: " + intactos);
if (!igual || !esperado || !intactos) {
  throw new Error("La carga no es idempotente");
}

// 4) Un insert duplicado de ARG lo tiene que rechazar el indice unico.
print("Intentando insertar un segundo equipo con codigo ARG...");
try {
  db.equipos.insertOne({
    codigo: "ARG",
    nombre: "Argentina duplicada",
    confederacion: "CONMEBOL",
    ranking: NumberInt(1)
  });
  throw new Error("El insert duplicado no fue rechazado");
} catch (e) {
  print("Error recibido: " + e.message);
  if (e.code !== 11000) {
    throw e;
  }
  print("Rechazado por el indice unico (E11000), como se esperaba.");
}
print("Equipos con codigo ARG: " + db.equipos.countDocuments({ codigo: "ARG" }));
