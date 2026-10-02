
// 1. CREATE - Crear un nodo de prueba

    CREATE (p:PruebaCRUD {
        id: "CRUD-001",
        nombre: "Prueba CRUD",
        estado: "creado"
    })
    RETURN p;



// 2. READ - Recuperar el nodo creado

MATCH (p:PruebaCRUD {id: "CRUD-001"})
RETURN p;



// 3. UPDATE - Actualizar una propiedad

MATCH (p:PruebaCRUD {id: "CRUD-001"})
SET p.estado = "actualizado"
RETURN p;



// 4. CREATE RELATIONSHIP - Crear una relación de prueba

MATCH (a:Equipo {codigo: "ARG"})
MATCH (b:Equipo {codigo: "BRA"})
CREATE (a)-[r:RELACION_PRUEBA {motivo: "Demostración CRUD"}]->(b)
RETURN a, r, b;


// 5. DELETE RELATIONSHIP - Eliminar la relación de prueba

MATCH (a:Equipo {codigo: "ARG"})-[r:RELACION_PRUEBA]->(b:Equipo {codigo: "BRA"})
DELETE r
RETURN a, b;



// 6. DELETE NODE - Eliminar el nodo de prueba

MATCH (p:PruebaCRUD {id: "CRUD-001"})
DELETE p
RETURN "Nodo de prueba eliminado" AS resultado;



// 7. VERIFICACIÓN FINAL

MATCH (p:PruebaCRUD {id: "CRUD-001"})
RETURN count(p) AS nodos_prueba_restantes;



// 8. CREATE - Crear nodos de prueba del modelo de usuarios y predicciones.
// Los identificadores 9001 se reservan para esta demostración y se eliminan al final.
MATCH (p:Partido {id: "P001"})
CREATE (u:Usuario {
    idUsuario: 9001,
    nombre: "Usuario CRUD",
    origen: "Argentina",
    email: "usuario.crud@fixture2030.test",
    fechaRegistro: date("2030-06-13"),
    activo: true
})
CREATE (g:Grupo {
    idGrupo: 9001,
    nombreGrupo: "Grupo CRUD",
    fechaCreacion: date("2030-06-13")
})
CREATE (pr:Prediccion {
    idPrediccion: 9001,
    paisGanador: "Argentina",
    paisPerdedor: "Brasil",
    golesPG: 2,
    golesPP: 1
})
RETURN u, g, pr, p;


// 9. READ - Recuperar los nodos de prueba creados.
MATCH (u:Usuario {idUsuario: 9001})
MATCH (g:Grupo {idGrupo: 9001})
MATCH (pr:Prediccion {idPrediccion: 9001})
RETURN u, g, pr;


// 10. UPDATE - Actualizar propiedades del usuario y de su predicción de prueba.
MATCH (u:Usuario {idUsuario: 9001})
MATCH (pr:Prediccion {idPrediccion: 9001})
SET u.activo = false,
    u.origen = "Argentina (actualizado)",
    pr.golesPG = 3,
    pr.golesPP = 1
RETURN u, pr;


// 11. CREATE / MERGE RELATIONSHIPS - Vincular los nodos de prueba sin duplicar relaciones.
MATCH (u:Usuario {idUsuario: 9001})
MATCH (g:Grupo {idGrupo: 9001})
MATCH (pr:Prediccion {idPrediccion: 9001})
MATCH (p:Partido {id: "P001"})
MERGE (u)-[pertenece:PERTENECE_A]->(g)
ON CREATE SET pertenece.fechaIngreso = date("2030-06-13")
ON MATCH SET pertenece.fechaIngreso = coalesce(pertenece.fechaIngreso, date("2030-06-13"))
MERGE (u)-[realiza:REALIZA]->(pr)
ON CREATE SET realiza.fechaPrediccion = datetime("2030-06-13T09:00:00-03:00")
ON MATCH SET realiza.fechaPrediccion = coalesce(realiza.fechaPrediccion, datetime("2030-06-13T09:00:00-03:00"))
MERGE (pr)-[:SOBRE]->(p)
RETURN u, pertenece, g, realiza, pr, p;


// 12. DELETE RELATIONSHIP - Eliminar la pertenencia de prueba al grupo.
MATCH (u:Usuario {idUsuario: 9001})-[r:PERTENECE_A]->(g:Grupo {idGrupo: 9001})
DELETE r
RETURN u, g;


// 13. DELETE RELATIONSHIPS - Limpiar las restantes relaciones de prueba.
MATCH (u:Usuario {idUsuario: 9001})-[r:REALIZA]->(pr:Prediccion {idPrediccion: 9001})
DELETE r;

MATCH (pr:Prediccion {idPrediccion: 9001})-[r:SOBRE]->(p:Partido {id: "P001"})
DELETE r
RETURN pr, p;


// 14. DELETE NODE - Eliminar sólo los nodos de prueba del modelo nuevo.
MATCH (u:Usuario {idUsuario: 9001})
MATCH (g:Grupo {idGrupo: 9001})
MATCH (pr:Prediccion {idPrediccion: 9001})
DELETE u, g, pr
RETURN "Nodos de prueba del modelo nuevo eliminados" AS resultado;


// 15. VERIFICACIÓN FINAL DEL CRUD NUEVO.
OPTIONAL MATCH (u:Usuario {idUsuario: 9001})
WITH count(DISTINCT u) AS usuarios_prueba_restantes
OPTIONAL MATCH (g:Grupo {idGrupo: 9001})
WITH usuarios_prueba_restantes, count(DISTINCT g) AS grupos_prueba_restantes
OPTIONAL MATCH (pr:Prediccion {idPrediccion: 9001})
RETURN usuarios_prueba_restantes,
       grupos_prueba_restantes,
       count(DISTINCT pr) AS predicciones_prueba_restantes;
