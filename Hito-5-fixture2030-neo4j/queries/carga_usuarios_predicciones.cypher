// CARGA DEL SUBGRAFO DE USUARIOS, GRUPOS Y PREDICCIONES
// Ejecutar después de carga.cypher y carga_partidos.cypher.
// Los MERGE permiten ejecutar esta carga más de una vez sin duplicar datos.


// Usuarios de prueba reproducibles.
UNWIND [
  {idUsuario: 1, nombre: "Ana Torres", origen: "Argentina", email: "ana.torres@fixture2030.test", fechaRegistro: date("2030-05-01"), activo: true},
  {idUsuario: 2, nombre: "Bruno Silva", origen: "Brasil", email: "bruno.silva@fixture2030.test", fechaRegistro: date("2030-05-02"), activo: true},
  {idUsuario: 3, nombre: "Carla Méndez", origen: "México", email: "carla.mendez@fixture2030.test", fechaRegistro: date("2030-05-03"), activo: true},
  {idUsuario: 4, nombre: "Diego Fernández", origen: "España", email: "diego.fernandez@fixture2030.test", fechaRegistro: date("2030-05-04"), activo: true},
  {idUsuario: 5, nombre: "Elena García", origen: "Colombia", email: "elena.garcia@fixture2030.test", fechaRegistro: date("2030-05-05"), activo: true}
] AS row
MERGE (u:Usuario {idUsuario: row.idUsuario})
SET u.nombre = row.nombre,
    u.origen = row.origen,
    u.email = row.email,
    u.fechaRegistro = row.fechaRegistro,
    u.activo = row.activo;


// Grupos de prueba. La cantidad de miembros se calcula por recorrido.
UNWIND [
  {idGrupo: 101, nombreGrupo: "Amigos del Fixture", fechaCreacion: date("2030-05-01")},
  {idGrupo: 102, nombreGrupo: "Analistas del Mundial", fechaCreacion: date("2030-05-03")},
  {idGrupo: 103, nombreGrupo: "Hinchada Global", fechaCreacion: date("2030-05-05")}
] AS row
MERGE (g:Grupo {idGrupo: row.idGrupo})
SET g.nombreGrupo = row.nombreGrupo,
    g.fechaCreacion = row.fechaCreacion;


// Pertenencia de cada usuario a un grupo.
UNWIND [
  {idUsuario: 1, idGrupo: 101, fechaIngreso: date("2030-05-02")},
  {idUsuario: 2, idGrupo: 101, fechaIngreso: date("2030-05-03")},
  {idUsuario: 3, idGrupo: 102, fechaIngreso: date("2030-05-04")},
  {idUsuario: 4, idGrupo: 102, fechaIngreso: date("2030-05-05")},
  {idUsuario: 5, idGrupo: 103, fechaIngreso: date("2030-05-06")}
] AS row
MATCH (u:Usuario {idUsuario: row.idUsuario})
MATCH (g:Grupo {idGrupo: row.idGrupo})
MERGE (u)-[r:PERTENECE_A]->(g)
SET r.fechaIngreso = row.fechaIngreso;


// Predicciones enlazadas exclusivamente a partidos ya cargados.
// fechaPrediccion se guarda en la relación REALIZA para conservar la autoría
// y el instante en que se efectuó cada pronóstico.
UNWIND [
  {idPrediccion: 1001, idUsuario: 1, idPartido: "P001", paisGanador: "Argentina", paisPerdedor: "Brasil", golesPG: 2, golesPP: 1, fechaPrediccion: datetime("2030-06-14T09:30:00-03:00")},
  {idPrediccion: 1002, idUsuario: 2, idPartido: "P001", paisGanador: "Brasil", paisPerdedor: "Argentina", golesPG: 1, golesPP: 0, fechaPrediccion: datetime("2030-06-14T10:15:00-03:00")},
  {idPrediccion: 1003, idUsuario: 3, idPartido: "P002", paisGanador: "España", paisPerdedor: "Francia", golesPG: 2, golesPP: 0, fechaPrediccion: datetime("2030-06-14T11:00:00-03:00")},
  {idPrediccion: 1004, idUsuario: 4, idPartido: "P002", paisGanador: "Francia", paisPerdedor: "España", golesPG: 2, golesPP: 1, fechaPrediccion: datetime("2030-06-14T11:45:00-03:00")},
  {idPrediccion: 1005, idUsuario: 3, idPartido: "P003", paisGanador: "Alemania", paisPerdedor: "Inglaterra", golesPG: 3, golesPP: 2, fechaPrediccion: datetime("2030-06-14T12:30:00-03:00")},
  {idPrediccion: 1006, idUsuario: 5, idPartido: "P001", paisGanador: "Argentina", paisPerdedor: "Brasil", golesPG: 1, golesPP: 0, fechaPrediccion: datetime("2030-06-14T13:00:00-03:00")},
  {idPrediccion: 1007, idUsuario: 1, idPartido: "P003", paisGanador: "Inglaterra", paisPerdedor: "Alemania", golesPG: 2, golesPP: 1, fechaPrediccion: datetime("2030-06-14T13:30:00-03:00")}
] AS row
MATCH (u:Usuario {idUsuario: row.idUsuario})
MATCH (p:Partido {id: row.idPartido})
// Valida que ambos países pronosticados participen realmente en el partido.
MATCH (p)<-[:PARTICIPA_EN]-(ganador:Equipo {nombre: row.paisGanador})
MATCH (p)<-[:PARTICIPA_EN]-(perdedor:Equipo {nombre: row.paisPerdedor})
WHERE ganador <> perdedor
  AND row.golesPG > row.golesPP
MERGE (pr:Prediccion {idPrediccion: row.idPrediccion})
SET pr.paisGanador = row.paisGanador,
    pr.paisPerdedor = row.paisPerdedor,
    pr.golesPG = row.golesPG,
    pr.golesPP = row.golesPP
MERGE (u)-[realiza:REALIZA]->(pr)
SET realiza.fechaPrediccion = row.fechaPrediccion
MERGE (pr)-[:SOBRE]->(p);


// Comprobación de la carga integrada.
MATCH (u:Usuario)
WITH count(u) AS usuarios
MATCH (g:Grupo)
WITH usuarios, count(g) AS grupos
MATCH (pr:Prediccion)
WITH usuarios, grupos, count(pr) AS predicciones
MATCH (:Usuario)-[pertenencias:PERTENECE_A]->(:Grupo)
WITH usuarios, grupos, predicciones, count(pertenencias) AS pertenencias
MATCH (:Usuario)-[realizaciones:REALIZA]->(:Prediccion)
WITH usuarios, grupos, predicciones, pertenencias, count(realizaciones) AS realizaciones
MATCH (:Prediccion)-[sobre:SOBRE]->(:Partido)
RETURN usuarios, grupos, predicciones, pertenencias, realizaciones, count(sobre) AS predicciones_sobre_partidos;
