// 01-create-collections.js
// Crea las colecciones "equipos" y "jugadores" con reglas de validacion basicas (RF7).
// Se ejecuta automaticamente al levantar el contenedor por primera vez.

db = db.getSiblingDB("fixture2030");

print("Creando coleccion 'equipos' con validacion...");

db.createCollection("equipos", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["codigo", "nombre", "confederacion", "ranking"],
      properties: {
        codigo: {
          bsonType: "string",
          pattern: "^[A-Z]{3}$",
          description: "codigo de 3 letras mayusculas del equipo (estandar FIFA), obligatorio y unico"
        },
        nombre: {
          bsonType: "string",
          description: "nombre del equipo, obligatorio"
        },
        confederacion: {
          enum: ["CONMEBOL", "UEFA", "CAF", "AFC", "CONCACAF", "OFC"],
          description: "confederacion a la que pertenece, obligatoria"
        },
        ranking: {
          bsonType: "int",
          minimum: 1,
          description: "posicion en el ranking, obligatoria"
        },
        sedeBase: {
          bsonType: "string",
          description: "ciudad de concentracion del equipo"
        },
        cantidadJugadoresConvocados: {
          bsonType: "int",
          description: "contador desnormalizado, se actualiza junto con la plantilla"
        }
      }
    }
  },
  validationLevel: "moderate",
  validationAction: "error"
});

print("Creando coleccion 'jugadores' con validacion...");

db.createCollection("jugadores", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["codigo", "equipoCodigo", "nombre", "apellido", "posicion", "convocado"],
      properties: {
        codigo: {
          bsonType: "string",
          description: "codigo unico del jugador (ej: ARG-10), obligatorio"
        },
        equipoCodigo: {
          bsonType: "string",
          pattern: "^[A-Z]{3}$",
          description: "referencia al codigo del equipo en la coleccion 'equipos', obligatoria"
        },
        nombre: {
          bsonType: "string",
          minLength: 1,
          description: "nombre de pila del jugador, obligatorio"
        },
        apellido: {
          bsonType: "string",
          minLength: 1,
          description: "apellido del jugador, obligatorio"
        },
        posicion: {
          enum: ["Portero", "Defensa", "Centrocampista", "Delantero"],
          description: "posicion principal, obligatoria"
        },
        dorsal: {
          bsonType: "int",
          minimum: 1,
          maximum: 26,
          description: "numero de camiseta dentro de la plantilla"
        },
        fechaNacimiento: {
          bsonType: "date",
          description: "fecha de nacimiento"
        },
        convocado: {
          bsonType: "bool",
          description: "si integra la lista final de convocados, obligatorio"
        }
      }
    }
  },
  validationLevel: "moderate",
  validationAction: "error"
});

print("Colecciones creadas.");
