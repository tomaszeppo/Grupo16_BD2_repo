/* global use, db */
// MongoDB Playground
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.

// The current database to use.
use("fixture2030");

// carga de equipos - hasta linea 76

db.equipos.deleteMany({}); //eliminamos todo antes de cargar para evitar duplicados
db.equipos.insertMany([
  { nombre: "Argentina", codigo: "ARG" },
  { nombre: "Brasil", codigo: "BRA" },
  { nombre: "España", codigo: "ESP" },
  { nombre: "Francia", codigo: "FRA" },
  { nombre: "Alemania", codigo: "GER" },
  { nombre: "Inglaterra", codigo: "ENG" },
  { nombre: "Italia", codigo: "ITA" },
  { nombre: "Portugal", codigo: "POR" },
  { nombre: "Países Bajos", codigo: "NED" },
  { nombre: "Bélgica", codigo: "BEL" },
  { nombre: "Croacia", codigo: "CRO" },
  { nombre: "Uruguay", codigo: "URU" },
  { nombre: "México", codigo: "MEX" },
  { nombre: "Estados Unidos", codigo: "USA" },
  { nombre: "Canadá", codigo: "CAN" },
  { nombre: "Japón", codigo: "JPN" },
  { nombre: "Corea del Sur", codigo: "KOR" },
  { nombre: "Australia", codigo: "AUS" },
  { nombre: "Marruecos", codigo: "MAR" },
  { nombre: "Senegal", codigo: "SEN" },
  { nombre: "Ghana", codigo: "GHA" },
  { nombre: "Nigeria", codigo: "NGA" },
  { nombre: "Camerún", codigo: "CMR" },
  { nombre: "Túnez", codigo: "TUN" },
  { nombre: "Egipto", codigo: "EGY" },
  { nombre: "Argelia", codigo: "ALG" },
  { nombre: "Colombia", codigo: "COL" },
  { nombre: "Chile", codigo: "CHI" },
  { nombre: "Perú", codigo: "PER" },
  { nombre: "Ecuador", codigo: "ECU" },
  { nombre: "Paraguay", codigo: "PAR" },
  { nombre: "Venezuela", codigo: "VEN" },
  { nombre: "Suiza", codigo: "SUI" },
  { nombre: "Austria", codigo: "AUT" },
  { nombre: "Polonia", codigo: "POL" },
  { nombre: "Suecia", codigo: "SWE" },
  { nombre: "Dinamarca", codigo: "DEN" },
  { nombre: "Noruega", codigo: "NOR" },
  { nombre: "Serbia", codigo: "SRB" },
  { nombre: "Gales", codigo: "WAL" },
  { nombre: "Escocia", codigo: "SCO" },
  { nombre: "Irlanda", codigo: "IRL" },
  { nombre: "Ucrania", codigo: "UKR" },
  { nombre: "Rusia", codigo: "RUS" },
  { nombre: "Turquía", codigo: "TUR" },
  { nombre: "Grecia", codigo: "GRE" },
  { nombre: "Rumania", codigo: "ROU" },
  { nombre: "República Checa", codigo: "CZE" },
  { nombre: "Hungría", codigo: "HUN" },
  { nombre: "Islandia", codigo: "ISL" },
  { nombre: "Costa Rica", codigo: "CRC" },
  { nombre: "Panamá", codigo: "PAN" },
  { nombre: "Jamaica", codigo: "JAM" },
  { nombre: "Honduras", codigo: "HON" },
  { nombre: "Arabia Saudita", codigo: "KSA" },
  { nombre: "Irán", codigo: "IRN" },
  { nombre: "Qatar", codigo: "QAT" },
  { nombre: "Emiratos Árabes Unidos", codigo: "UAE" },
  { nombre: "Irak", codigo: "IRQ" },
  { nombre: "China", codigo: "CHN" },
  { nombre: "Nueva Zelanda", codigo: "NZL" },
  { nombre: "Sudáfrica", codigo: "RSA" },
  { nombre: "Costa de Marfil", codigo: "CIV" },
  { nombre: "República Democrática del Congo", codigo: "COD" }
]);


