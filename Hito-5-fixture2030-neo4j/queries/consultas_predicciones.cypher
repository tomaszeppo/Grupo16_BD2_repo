// CONSULTAS DEL SUBGRAFO DE USUARIOS, GRUPOS Y PREDICCIONES
// Ejecutar después de carga_usuarios_predicciones.cypher.


// CONSULTA 1 - Usuarios de un grupo.
MATCH (u:Usuario)-[r:PERTENECE_A]->(g:Grupo {idGrupo: 101})
RETURN g.nombreGrupo AS grupo,
       u.idUsuario AS id_usuario,
       u.nombre AS usuario,
       u.origen AS origen,
       r.fechaIngreso AS fecha_ingreso
ORDER BY u.nombre;


// CONSULTA 2 - Predicciones realizadas por una persona.
MATCH (u:Usuario {idUsuario: 1})-[r:REALIZA]->(pr:Prediccion)-[:SOBRE]->(p:Partido)
RETURN u.nombre AS usuario,
       pr.idPrediccion AS prediccion,
       p.id AS partido,
       pr.paisGanador AS pais_ganador,
       pr.paisPerdedor AS pais_perdedor,
       pr.golesPG AS goles_ganador,
       pr.golesPP AS goles_perdedor,
       p.equipoGanador AS resultado_equipo_ganador,
       p.golesGanador AS resultado_goles_ganador,
       p.golesPerdedor AS resultado_goles_perdedor,
       p.equipoPerdedor AS resultado_equipo_perdedor,
       p.origenResultado AS origen_resultado,
       r.fechaPrediccion AS fecha_prediccion
ORDER BY r.fechaPrediccion;


// CONSULTA 3 - Predicciones de todos los miembros de un grupo.
MATCH (u:Usuario)-[:PERTENECE_A]->(g:Grupo {idGrupo: 101})
MATCH (u)-[r:REALIZA]->(pr:Prediccion)-[:SOBRE]->(p:Partido)
RETURN g.nombreGrupo AS grupo,
       u.nombre AS usuario,
       p.id AS partido,
       pr.paisGanador AS pais_ganador,
       pr.golesPG AS goles_ganador,
       pr.golesPP AS goles_perdedor,
       r.fechaPrediccion AS fecha_prediccion
ORDER BY p.fecha, u.nombre, r.fechaPrediccion;


// CONSULTA 4 - Todas las predicciones sobre un partido.
MATCH (u:Usuario)-[r:REALIZA]->(pr:Prediccion)-[:SOBRE]->(p:Partido {id: "P001"})
RETURN p.id AS partido,
       p.fecha AS fecha,
       u.nombre AS usuario,
       pr.paisGanador AS pais_ganador,
       pr.paisPerdedor AS pais_perdedor,
       pr.golesPG AS goles_ganador,
       pr.golesPP AS goles_perdedor,
       p.equipoGanador AS resultado_equipo_ganador,
       p.golesGanador AS resultado_goles_ganador,
       p.golesPerdedor AS resultado_goles_perdedor,
       p.equipoPerdedor AS resultado_equipo_perdedor,
       p.origenResultado AS origen_resultado,
       r.fechaPrediccion AS fecha_prediccion
ORDER BY r.fechaPrediccion;


// CONSULTA 5 - Usuarios que pronosticaron a Argentina como ganadora.
MATCH (u:Usuario)-[:REALIZA]->(pr:Prediccion {paisGanador: "Argentina"})-[:SOBRE]->(p:Partido)
RETURN DISTINCT u.idUsuario AS id_usuario,
       u.nombre AS usuario,
       p.id AS partido,
       pr.golesPG AS goles_argentina,
       pr.golesPP AS goles_rival
ORDER BY usuario, partido;


// CONSULTA 6 - Recorrido integrado: Grupo <- Usuario -> Predicción -> Partido <- Equipo.
MATCH (g:Grupo {idGrupo: 101})<-[:PERTENECE_A]-(u:Usuario)
      -[:REALIZA]->(pr:Prediccion)-[:SOBRE]->(p:Partido)
      <-[:PARTICIPA_EN]-(e:Equipo)
RETURN g.nombreGrupo AS grupo,
       u.nombre AS usuario,
       pr.idPrediccion AS prediccion,
       p.id AS partido,
       e.codigo AS codigo_equipo,
       e.nombre AS equipo
ORDER BY usuario, partido, equipo;


// CONSULTA 7 - Recorrido Usuario -> Predicción -> Partido -> Estadio.
MATCH (u:Usuario {idUsuario: 1})-[:REALIZA]->(pr:Prediccion)-[:SOBRE]->(p:Partido)
      -[:SE_JUEGA_EN]->(est:Estadio)
RETURN u.nombre AS usuario,
       p.id AS partido,
       est.nombre AS estadio,
       est.ciudad AS ciudad
ORDER BY p.fecha;


// CONSULTA 8 - Recorrido Usuario -> Predicción -> Partido <- Evento.
MATCH (u:Usuario {idUsuario: 1})-[:REALIZA]->(pr:Prediccion)-[:SOBRE]->(p:Partido)
      <-[:OCURRE_EN]-(ev:Evento)
RETURN u.nombre AS usuario,
       pr.idPrediccion AS prediccion,
       p.id AS partido,
       ev.tipo AS tipo_evento,
       ev.minuto AS minuto
ORDER BY p.fecha, ev.minuto;


// CONSULTA 9 - Integrantes por grupo sin almacenar un campo redundante.
MATCH (g:Grupo)
OPTIONAL MATCH (u:Usuario)-[:PERTENECE_A]->(g)
RETURN g.idGrupo AS id_grupo,
       g.nombreGrupo AS grupo,
       count(DISTINCT u) AS integrantes
ORDER BY integrantes DESC, grupo;


// CONSULTA 10 - Cantidad de predicciones recibidas por partido.
MATCH (p:Partido)
OPTIONAL MATCH (pr:Prediccion)-[:SOBRE]->(p)
RETURN p.id AS partido,
       p.fecha AS fecha,
       count(DISTINCT pr) AS predicciones
ORDER BY predicciones DESC, fecha, partido;


// CONSULTA 11 - Cantidad de predicciones realizadas por integrante de cada grupo.
MATCH (g:Grupo)<-[:PERTENECE_A]-(u:Usuario)
OPTIONAL MATCH (u)-[:REALIZA]->(pr:Prediccion)
RETURN g.nombreGrupo AS grupo,
       u.nombre AS usuario,
       count(DISTINCT pr) AS predicciones_realizadas
ORDER BY grupo, predicciones_realizadas DESC, usuario;



// CONSULTA 12 - Comparación calculada entre pronóstico y resultado simulado.
// No se persiste un campo "acierto" porque depende del criterio de evaluación.
MATCH (u:Usuario)-[r:REALIZA]->(pr:Prediccion)-[:SOBRE]->(p:Partido)
WHERE p.origenResultado = "SIMULADO"
RETURN u.nombre AS usuario,
       p.id AS partido,
       pr.paisGanador + " " + toString(pr.golesPG) + "-" +
         toString(pr.golesPP) + " " + pr.paisPerdedor AS pronostico,
       p.equipoGanador + " " + toString(p.golesGanador) + "-" +
         toString(p.golesPerdedor) + " " + p.equipoPerdedor AS resultado_simulado,
       CASE
         WHEN pr.paisGanador = p.equipoGanador
          AND pr.paisPerdedor = p.equipoPerdedor
          AND pr.golesPG = p.golesGanador
          AND pr.golesPP = p.golesPerdedor
           THEN "Marcador exacto"
         WHEN pr.paisGanador = p.equipoGanador
          AND pr.paisPerdedor = p.equipoPerdedor
           THEN "Ganador correcto"
         ELSE "No acertó"
       END AS evaluacion,
       r.fechaPrediccion AS fecha_prediccion
ORDER BY p.fecha, p.id, r.fechaPrediccion;
