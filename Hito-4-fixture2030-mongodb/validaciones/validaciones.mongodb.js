use("fixture2030");


// validacion de equipos

db.runCommand({
    collMod: "equipos",
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["nombre", "codigo"],
            properties: {
                nombre: {
                    bsonType: "string",
                    description: "El nombre del equipo es obligatorio y debe ser texto"
                },
                codigo: {
                    bsonType: "string",
                    pattern: "^[A-Z]{3}$",
                    description: "El código del equipo debe tener exactamente 3 letras mayúsculas"
                }
            }
        }
    },
    validationLevel: "strict",
    validationAction: "error"
});


// validacion de jugadores

db.runCommand({
    collMod: "jugadores",
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: [
                "nombre",
                "apellido",
                "dorsal",
                "equipo",
                "posicion"
            ],
            properties: {

                nombre: {
                    bsonType: "string",
                    minLength: 1,
                    description: "El nombre es obligatorio y debe ser texto"
                },

                apellido: {
                    bsonType: "string",
                    minLength: 1,
                    description: "El apellido es obligatorio y debe ser texto"
                },

                dorsal: {
                    bsonType: "int",
                    minimum: 1,
                    maximum: 99,
                    description: "El dorsal debe ser un entero entre 1 y 99"
                },

                equipo: {
                    bsonType: "string",
                    pattern: "^[A-Z]{3}$",
                    description: "El código del equipo debe tener exactamente 3 letras mayúsculas"
                },

                posicion: {
                    enum: [
                        "Portero",
                        "Defensa",
                        "Centrocampista",
                        "Delantero"
                    ],
                    description: "La posición debe ser una de las posiciones permitidas"
                }
            }
        }
    },
    validationLevel: "strict",
    validationAction: "error"
});

print("Validaciones configuradas correctamente.");