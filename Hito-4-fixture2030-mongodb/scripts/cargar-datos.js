// cargar-datos.js
// Carga los 64 equipos y la plantilla de 24 jugadores de cada uno (1536 en total).
// Se puede correr todas las veces que haga falta: cada documento se inserta o se
// actualiza por su "codigo" (upsert), asi que una segunda corrida deja los mismos
// totales y no pisa lo que cambia durante el torneo.
//   - Datos de referencia (nombre, ranking, posicion, etc.): van con $set, se
//     corrigen si cambiaron en este script.
//   - Datos que se pueden modificar despues de la carga (convocado y el contador
//     cantidadJugadoresConvocados): van con $setOnInsert, solo se escriben si el
//     documento todavia no existia.
// Lo llama init-scripts/03-load-data.js en el primer arranque y tambien se puede
// correr a mano (ver README).

db = db.getSiblingDB("fixture2030");

print("Cargando equipos...");

const equipos = [
  { codigo: 'ARG', nombre: 'Argentina', confederacion: 'CONMEBOL', ranking: 1, sedeBase: 'Buenos Aires' },
  { codigo: 'URU', nombre: 'Uruguay', confederacion: 'CONMEBOL', ranking: 2, sedeBase: 'Montevideo' },
  { codigo: 'PAR', nombre: 'Paraguay', confederacion: 'CONMEBOL', ranking: 3, sedeBase: 'Asunción' },
  { codigo: 'BRA', nombre: 'Brasil', confederacion: 'CONMEBOL', ranking: 4, sedeBase: 'San Pablo' },
  { codigo: 'COL', nombre: 'Colombia', confederacion: 'CONMEBOL', ranking: 5, sedeBase: 'Bogotá' },
  { codigo: 'CHI', nombre: 'Chile', confederacion: 'CONMEBOL', ranking: 6, sedeBase: 'Santiago' },
  { codigo: 'ECU', nombre: 'Ecuador', confederacion: 'CONMEBOL', ranking: 7, sedeBase: 'Quito' },
  { codigo: 'PER', nombre: 'Perú', confederacion: 'CONMEBOL', ranking: 8, sedeBase: 'Lima' },
  { codigo: 'ESP', nombre: 'España', confederacion: 'UEFA', ranking: 9, sedeBase: 'Madrid' },
  { codigo: 'POR', nombre: 'Portugal', confederacion: 'UEFA', ranking: 10, sedeBase: 'Lisboa' },
  { codigo: 'MAR', nombre: 'Marruecos', confederacion: 'CAF', ranking: 11, sedeBase: 'Rabat' },
  { codigo: 'FRA', nombre: 'Francia', confederacion: 'UEFA', ranking: 12, sedeBase: 'París' },
  { codigo: 'GER', nombre: 'Alemania', confederacion: 'UEFA', ranking: 13, sedeBase: 'Berlín' },
  { codigo: 'ENG', nombre: 'Inglaterra', confederacion: 'UEFA', ranking: 14, sedeBase: 'Londres' },
  { codigo: 'ITA', nombre: 'Italia', confederacion: 'UEFA', ranking: 15, sedeBase: 'Roma' },
  { codigo: 'NED', nombre: 'Países Bajos', confederacion: 'UEFA', ranking: 16, sedeBase: 'Ámsterdam' },
  { codigo: 'BEL', nombre: 'Bélgica', confederacion: 'UEFA', ranking: 17, sedeBase: 'Bruselas' },
  { codigo: 'CRO', nombre: 'Croacia', confederacion: 'UEFA', ranking: 18, sedeBase: 'Zagreb' },
  { codigo: 'SUI', nombre: 'Suiza', confederacion: 'UEFA', ranking: 19, sedeBase: 'Berna' },
  { codigo: 'DEN', nombre: 'Dinamarca', confederacion: 'UEFA', ranking: 20, sedeBase: 'Copenhague' },
  { codigo: 'POL', nombre: 'Polonia', confederacion: 'UEFA', ranking: 21, sedeBase: 'Varsovia' },
  { codigo: 'SRB', nombre: 'Serbia', confederacion: 'UEFA', ranking: 22, sedeBase: 'Belgrado' },
  { codigo: 'AUT', nombre: 'Austria', confederacion: 'UEFA', ranking: 23, sedeBase: 'Viena' },
  { codigo: 'UKR', nombre: 'Ucrania', confederacion: 'UEFA', ranking: 24, sedeBase: 'Kiev' },
  { codigo: 'WAL', nombre: 'Gales', confederacion: 'UEFA', ranking: 25, sedeBase: 'Cardiff' },
  { codigo: 'SCO', nombre: 'Escocia', confederacion: 'UEFA', ranking: 26, sedeBase: 'Glasgow' },
  { codigo: 'TUR', nombre: 'Turquía', confederacion: 'UEFA', ranking: 27, sedeBase: 'Estambul' },
  { codigo: 'SWE', nombre: 'Suecia', confederacion: 'UEFA', ranking: 28, sedeBase: 'Estocolmo' },
  { codigo: 'CZE', nombre: 'República Checa', confederacion: 'UEFA', ranking: 29, sedeBase: 'Praga' },
  { codigo: 'NOR', nombre: 'Noruega', confederacion: 'UEFA', ranking: 30, sedeBase: 'Oslo' },
  { codigo: 'HUN', nombre: 'Hungría', confederacion: 'UEFA', ranking: 31, sedeBase: 'Budapest' },
  { codigo: 'GRE', nombre: 'Grecia', confederacion: 'UEFA', ranking: 32, sedeBase: 'Atenas' },
  { codigo: 'JPN', nombre: 'Japón', confederacion: 'AFC', ranking: 33, sedeBase: 'Tokio' },
  { codigo: 'KOR', nombre: 'Corea del Sur', confederacion: 'AFC', ranking: 34, sedeBase: 'Seúl' },
  { codigo: 'IRN', nombre: 'Irán', confederacion: 'AFC', ranking: 35, sedeBase: 'Teherán' },
  { codigo: 'KSA', nombre: 'Arabia Saudita', confederacion: 'AFC', ranking: 36, sedeBase: 'Riad' },
  { codigo: 'AUS', nombre: 'Australia', confederacion: 'AFC', ranking: 37, sedeBase: 'Sídney' },
  { codigo: 'QAT', nombre: 'Catar', confederacion: 'AFC', ranking: 38, sedeBase: 'Doha' },
  { codigo: 'IRQ', nombre: 'Irak', confederacion: 'AFC', ranking: 39, sedeBase: 'Bagdad' },
  { codigo: 'CHN', nombre: 'China', confederacion: 'AFC', ranking: 40, sedeBase: 'Pekín' },
  { codigo: 'ISL', nombre: 'Islandia', confederacion: 'UEFA', ranking: 41, sedeBase: 'Reikiavik' },
  { codigo: 'UAE', nombre: 'Emiratos Árabes Unidos', confederacion: 'AFC', ranking: 42, sedeBase: 'Abu Dabi' },
  { codigo: 'SEN', nombre: 'Senegal', confederacion: 'CAF', ranking: 43, sedeBase: 'Dakar' },
  { codigo: 'NGA', nombre: 'Nigeria', confederacion: 'CAF', ranking: 44, sedeBase: 'Abuya' },
  { codigo: 'EGY', nombre: 'Egipto', confederacion: 'CAF', ranking: 45, sedeBase: 'El Cairo' },
  { codigo: 'ALG', nombre: 'Argelia', confederacion: 'CAF', ranking: 46, sedeBase: 'Argel' },
  { codigo: 'TUN', nombre: 'Túnez', confederacion: 'CAF', ranking: 47, sedeBase: 'Túnez' },
  { codigo: 'CMR', nombre: 'Camerún', confederacion: 'CAF', ranking: 48, sedeBase: 'Yaundé' },
  { codigo: 'GHA', nombre: 'Ghana', confederacion: 'CAF', ranking: 49, sedeBase: 'Acra' },
  { codigo: 'CIV', nombre: 'Costa de Marfil', confederacion: 'CAF', ranking: 50, sedeBase: 'Abiyán' },
  { codigo: 'RSA', nombre: 'Sudáfrica', confederacion: 'CAF', ranking: 51, sedeBase: 'Johannesburgo' },
  { codigo: 'COD', nombre: 'República Democrática del Congo', confederacion: 'CAF', ranking: 52, sedeBase: 'Kinsasa' },
  { codigo: 'MEX', nombre: 'México', confederacion: 'CONCACAF', ranking: 53, sedeBase: 'Ciudad de México' },
  { codigo: 'USA', nombre: 'Estados Unidos', confederacion: 'CONCACAF', ranking: 54, sedeBase: 'Nueva York' },
  { codigo: 'CAN', nombre: 'Canadá', confederacion: 'CONCACAF', ranking: 55, sedeBase: 'Toronto' },
  { codigo: 'CRC', nombre: 'Costa Rica', confederacion: 'CONCACAF', ranking: 56, sedeBase: 'San José' },
  { codigo: 'JAM', nombre: 'Jamaica', confederacion: 'CONCACAF', ranking: 57, sedeBase: 'Kingston' },
  { codigo: 'PAN', nombre: 'Panamá', confederacion: 'CONCACAF', ranking: 58, sedeBase: 'Panamá' },
  { codigo: 'HON', nombre: 'Honduras', confederacion: 'CONCACAF', ranking: 59, sedeBase: 'Tegucigalpa' },
  { codigo: 'NZL', nombre: 'Nueva Zelanda', confederacion: 'OFC', ranking: 60, sedeBase: 'Auckland' },
  { codigo: 'VEN', nombre: 'Venezuela', confederacion: 'CONMEBOL', ranking: 61, sedeBase: 'Caracas' },
  { codigo: 'ROU', nombre: 'Rumania', confederacion: 'UEFA', ranking: 62, sedeBase: 'Bucarest' },
  { codigo: 'IRL', nombre: 'Irlanda', confederacion: 'UEFA', ranking: 63, sedeBase: 'Dublín' },
  { codigo: 'RUS', nombre: 'Rusia', confederacion: 'UEFA', ranking: 64, sedeBase: 'Moscú' },
];

const opsEquipos = equipos.map((e) => ({
  updateOne: {
    filter: { codigo: e.codigo },
    update: {
      $set: {
        nombre: e.nombre,
        confederacion: e.confederacion,
        ranking: NumberInt(e.ranking),
        sedeBase: e.sedeBase
      },
      $setOnInsert: { cantidadJugadoresConvocados: NumberInt(24) }
    },
    upsert: true
  }
}));

const resEquipos = db.equipos.bulkWrite(opsEquipos, { ordered: false });
print("Equipos nuevos: " + resEquipos.upsertedCount + " | ya existentes: " + resEquipos.matchedCount);

// --- Generacion de la plantilla de cada equipo ---

const nombresPila = [
  "Lucas", "Mateo", "Santiago", "Diego", "Nicolas", "Bruno", "Iker", "Rodrigo",
  "Emiliano", "Julian", "Thiago", "Facundo", "Gonzalo", "Franco", "Agustin",
  "Ezequiel", "Ignacio", "Martin", "Tomas", "Federico", "Joaquin", "Maximiliano",
  "Leandro", "Ramiro", "Alejandro", "Cristian", "Gabriel", "Fernando", "Andres",
  "Pablo"
];

const apellidos = [
  "Gonzalez", "Rodriguez", "Fernandez", "Lopez", "Martinez", "Perez", "Sanchez",
  "Romero", "Diaz", "Torres", "Ramirez", "Flores", "Alvarez", "Ruiz", "Silva",
  "Castro", "Rojas", "Ortiz", "Molina", "Herrera", "Medina", "Aguirre", "Vega",
  "Cabrera", "Sosa", "Acosta", "Benitez", "Nunez", "Dominguez", "Vargas"
];

// Distribucion de posiciones para una plantilla de 24: 3 arqueros, 8 defensores,
// 8 mediocampistas, 5 delanteros.
const distribucionPosiciones = [
  ...Array(3).fill("Portero"),
  ...Array(8).fill("Defensa"),
  ...Array(8).fill("Centrocampista"),
  ...Array(5).fill("Delantero"),
];

function nombreDeterministico(semilla) {
  return nombresPila[semilla % nombresPila.length];
}

function apellidoDeterministico(semilla) {
  return apellidos[(semilla * 7 + 3) % apellidos.length];
}

function fechaNacimientoDeterministica(semilla) {
  // Jugadores de entre 18 y 36 anios a la fecha del torneo (2030-06-01).
  // Date.UTC para que la fecha no dependa de la zona horaria de quien corra el script.
  const edadAnios = 18 + (semilla % 19);
  const mes = (semilla % 12);
  const dia = 1 + (semilla % 27);
  return new Date(Date.UTC(2030 - edadAnios, mes, dia));
}

print("Cargando jugadores...");

let semillaGlobal = 1;
let jugadoresNuevos = 0;
let jugadoresExistentes = 0;

equipos.forEach((equipo) => {
  const ops = distribucionPosiciones.map((posicion, idx) => {
    const dorsal = idx + 1;
    const semilla = semillaGlobal + idx;
    return {
      updateOne: {
        filter: { codigo: equipo.codigo + "-" + String(dorsal).padStart(2, "0") },
        update: {
          $set: {
            equipoCodigo: equipo.codigo,
            nombre: nombreDeterministico(semilla),
            apellido: apellidoDeterministico(semilla),
            posicion: posicion,
            dorsal: NumberInt(dorsal),
            fechaNacimiento: fechaNacimientoDeterministica(semilla)
          },
          $setOnInsert: { convocado: true }
        },
        upsert: true
      }
    };
  });
  semillaGlobal += distribucionPosiciones.length;
  const res = db.jugadores.bulkWrite(ops, { ordered: false });
  jugadoresNuevos += res.upsertedCount;
  jugadoresExistentes += res.matchedCount;
});

print("Jugadores nuevos: " + jugadoresNuevos + " | ya existentes: " + jugadoresExistentes);
print("Total en la base -> equipos: " + db.equipos.countDocuments() +
      ", jugadores: " + db.jugadores.countDocuments());
