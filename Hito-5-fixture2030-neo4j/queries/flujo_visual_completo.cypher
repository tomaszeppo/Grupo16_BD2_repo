// FLUJO VISUAL REPRESENTATIVO DEL MODELO COMPLETO
//
// No intenta mostrar los 1.281 nodos cargados simultáneamente: esa vista sería
// ilegible. En cambio, reúne las ocho etiquetas y todos los tipos de relación
// del modelo en un único flujo de P001. El nodo Partido incluye además su
// resultado simulado; el estilo fixture2030.grass lo muestra en el caption.
//
// Para que los nombres se vean como captions, importar antes
// docs/fixture2030.grass desde el comando :style de Neo4j Browser.

MATCH flujoSocial =
  (g:Grupo {idGrupo: 101})
  <-[:PERTENECE_A]-(u:Usuario {idUsuario: 1})
  -[:REALIZA]->(pr:Prediccion {idPrediccion: 1001})
  -[:SOBRE]->(p:Partido {id: "P001"})

MATCH flujoDeportivo =
  (j:Jugador {id: "J-ARG-0020"})
  -[:PERTENECE_A]->(arg:Equipo {codigo: "ARG"})
  -[:PARTICIPA_EN]->(p)
  -[:SE_JUEGA_EN]->(est:Estadio)

MATCH flujoRival = (bra:Equipo {codigo: "BRA"})-[:PARTICIPA_EN]->(p)
MATCH flujoEvento = (ev:Evento)-[:OCURRE_EN]->(p)

WITH flujoSocial, flujoDeportivo, flujoRival, flujoEvento, ev
ORDER BY ev.minuto
RETURN flujoSocial,
       flujoDeportivo,
       flujoRival,
       flujoEvento;
