# Decisiones de diseño — Módulo documental (Hito 4)

## De dónde viene esto

En el Hito 1 propusimos el modelo documental para selecciones, jugadores y estadios
por ser datos estables, de poco volumen y con estructura propia. El Hito 2 lo confirmó
con la matriz de decisión: MongoDB para los partidos finalizados y los datos estáticos.
Este hito lleva esa decisión a un módulo funcional que se limita a equipos y jugadores.

## Por qué MongoDB para este módulo

Equipos y jugadores se guardan como documentos independientes con una estructura
común y sencilla, pensados para consultarlos, filtrarlos, ordenarlos, actualizarlos
y agregarlos con los operadores propios de MongoDB. La estructura comparte campos
entre todos los jugadores pero puede crecer en iteraciones futuras sin rehacer el
modelo completo. La elección se apoya en los criterios del Hito 2: el volumen
de lecturas, la velocidad de acceso por código, la flexibilidad del esquema y la
posibilidad de escalar. No se descarta lo relacional por una cuestión de
garantías: ese tipo de garantías se resuelve acá con validación de esquema,
índices únicos y la carga con upsert que se describe más abajo.

## Alternativa descartada: plantilla embebida en el equipo

Se consideró guardar los jugadores como un arreglo dentro de cada documento de
equipo. Traería el equipo con su plantilla en una sola lectura, pero dificulta las
consultas globales sobre jugadores (por apellido, posición o dorsal) y agranda el
documento del equipo. Por eso quedaron en colecciones separadas, unidas por
`jugadores.equipoCodigo`, que es el `codigo` del equipo. El nombre y el resto de
los datos del equipo viven en un único lugar: si cambian, se modifican solo en
`equipos`.

## Validación e integridad

La validación con `$jsonSchema` controla estructura y tipos (códigos de tres
letras mayúsculas, dorsal entero, posición dentro de los valores permitidos),
pero no puede declarar una clave foránea. Por eso la integridad jugador–equipo se
comprueba además con un `$lookup` que busca jugadores cuyo `equipoCodigo` no
corresponde a ningún equipo (`queries/01-consultas-recuperacion.js`, resultado
esperado: lista vacía).

## Tabla de decisiones

| Decisión | Alternativas consideradas | Elección | Justificación | Impacto esperado |
| :--- | :--- | :--- | :--- | :--- |
| Relación equipo–jugador | Embeber la plantilla completa dentro del documento de equipo; o dos colecciones separadas conectadas por referencia | Dos colecciones separadas (`equipos` y `jugadores`), unidas por `jugadores.equipoCodigo` | Los jugadores se consultan y modifican por su cuenta (por apellido, posición, dorsal o convocatoria). Si estuvieran embebidos en un array dentro del equipo, cada cambio de un jugador obligaría a reescribir el documento del equipo, que además contiene todos los demás datos del equipo | Modificar un jugador nunca toca el documento del equipo. A cambio, traer un equipo con su plantilla completa exige dos consultas (o un `$lookup`) en vez de una sola lectura |
| Validación documental | Sin validación (esquema totalmente libre); validación estricta (`validationAction: "error"` + `validationLevel: "strict"`); validación moderada solo sobre campos críticos | `$jsonSchema` con `validationLevel: "moderate"` sobre los campos obligatorios de cada colección (ver `schemas/modelo-documental.md`) | Los campos obligatorios (código, nombre, confederación/posición, etc.) no pueden faltar sin romper el resto del sistema. `"moderate"` en vez de `"strict"` permite seguir actualizando documentos viejos que no cumplan una regla agregada después, sin bloquear la operación | Los documentos nuevos quedan garantizados sin campos críticos ausentes (RNF3); no se traba la carga si en el futuro se agrega una regla nueva |
| Estrategia de identificadores | UUID generado automáticamente; código legible propio del dominio (3 letras para equipo, equipo+dorsal para jugador) | Código propio: `codigo` de 3 letras para equipo (ej. `ARG`), `equipoCodigo-dorsal` para jugador (ej. `ARG-10`) | Un identificador legible permite reconocer la entidad a simple vista en consultas y logs, y permite que la relación equipo–jugador se vea en el propio dato (`ARG-10` pertenece a `ARG`) | Los índices únicos garantizan que no haya duplicados (RNF3) |
| Índices principales | Sin índices adicionales (solo `_id`); índice único en `codigo` de cada colección; índice compuesto agregado para filtros por posición y convocatoria | 6 índices: `codigo` único en cada colección, `confederacion + ranking` en equipos, y en jugadores `equipoCodigo`, `apellido` (el módulo ordena alfabéticamente) y el compuesto `equipoCodigo + posicion + convocado` | La consulta que más se repite en todo el módulo es "traer la plantilla de un equipo" (por `equipoCodigo`); sin ese índice, cada consulta recorrería los 1.536 jugadores en vez de los ~24 de un equipo | Las consultas por equipo pasan de recorrido completo (`COLLSCAN`) a acceso directo (`IXSCAN`), verificable con `explain()` en `queries/03-analisis-indices.js` |
| Carga y actualización | Borrar las colecciones e insertar de nuevo; insertar sin verificar si ya existe; insertar o actualizar cada documento por su `codigo` (upsert) | `scripts/cargar-datos.js`, con `bulkWrite` de `updateOne` + `upsert` por `codigo`. Los datos de referencia (nombre, ranking, posición, dorsal, fecha de nacimiento) van con `$set`; los que se pueden modificar después de la carga (`convocado` y el contador `cantidadJugadoresConvocados`) van con `$setOnInsert`. El `init-script` solo llama a ese archivo | Borrar e insertar de nuevo hubiera perdido las convocatorias y cualquier corrección hecha después de la carga. Además, la primera evidencia mostró a Argentina duplicada y hubo que borrarla a mano: la unicidad tiene que resolverla el propio script, con el índice único como respaldo. El mismo archivo se puede correr con el contenedor ya creado, cosa que los `init-scripts` no permiten porque solo corren en el primer arranque | Una segunda carga deja 64 equipos y 1.536 jugadores, sin correcciones manuales y sin pisar lo modificado después de la carga (RF8). Se comprueba con `queries/04-verificar-idempotencia.js`, que además prueba que un segundo `ARG` lo rechaza el índice (E11000). El costo es que cada recarga hace unas 1.600 escrituras aunque nada haya cambiado |

## Vínculo con hitos previos

- **Hito 1**: selecciones y jugadores son datos estables con estructura propia; por eso
  se propuso el modelo documental.
- **Hito 2**: la matriz de decisión asignó MongoDB a los partidos finalizados y los datos
  estáticos, donde entran equipos y jugadores.

## Limitaciones conocidas

- El contador `equipos.cantidadJugadoresConvocados` se actualiza a mano en
  el ejemplo de `queries/02-actualizaciones.js`; como la carga lo escribe con
  `$setOnInsert`, recargar no lo recalcula. Falta decidir si conviene
  automatizarlo o dejarlo como responsabilidad de la aplicación.
- No se probó el comportamiento del índice compuesto cuando el filtro no
  incluye `equipoCodigo` (por ejemplo, "todos los arqueros de todos los
  equipos"): ese patrón de acceso no está optimizado todavía.
- La integridad referencial entre `jugadores.equipoCodigo` y `equipos.codigo`
  no la garantiza MongoDB de forma automática (no hay foreign keys); depende
  de que la aplicación no inserte un jugador con un código de equipo
  inexistente.
