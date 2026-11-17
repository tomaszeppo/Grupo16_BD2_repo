# Por qué IRIS no entra en el proyecto final

Durante la cursada usamos seis bases, una por hito. En el proyecto final usamos cinco: dejamos afuera IRIS. No es un olvido; lo evaluamos y esta es la razón.

## Qué hacía IRIS en los hitos

- **Hito 9.** Modelamos el partido como un objeto con sus eventos adentro, con herencia entre tipos de evento, y lo guardamos entero con una sola operación. También lo consultamos con SQL.
- **Hito 10.** La API leía de IRIS el detalle del partido como objeto y le pedía los cambios de estado, que IRIS validaba.
- **Hito 13.** Uno de los momentos de la demostración era ese cambio de estado.

Lo que IRIS aportaba era guardar un árbol de objetos de una vez y validar las transiciones del partido en la propia base.

## Por qué no hace falta en el prode

**El partido ya tiene dueño.** En el proyecto final el partido, su estado y sus jugadas están en Neo4j, porque lo que queremos preguntar sobre un partido son recorridos (qué jugadas llevaron a un gol, qué le queda a un equipo hasta la final). Sumar IRIS era tener el mismo partido en dos bases y volver a discutir cuál manda, que es justo lo que nos marcaron en los Hitos 7 y 10.

**Lo que se guarda "de una vez" en el prode cabe en un documento.** El resultado de un partido con el avance de su puntuación, o un prode con sus integrantes, son un solo documento de MongoDB, que se escribe completo o no se escribe. No tenemos ningún árbol de objetos que guardar.

**Las reglas de estado son pocas.** Un partido pasa de programado a en juego y de en juego a finalizado. Lo resuelve una condición en la consulta de Neo4j, y repetir el cambio no tiene efecto. No justifica un motor de objetos.

**Cada base tiene un costo.** La consigna del Hito 13 pregunta qué costo operativo agrega mantener seis productos. IRIS es además el más pesado de levantar en nuestro laboratorio. Mantenerlo sin un dato que solo él resuelva bien era pagar ese costo por nada.

## Qué base tomó cada cosa

| En los hitos, en IRIS | En el proyecto final |
|---|---|
| El partido como objeto | Nodo `Partido` en Neo4j |
| Los eventos como hijos del partido | Nodos `Evento` relacionados con el partido y entre sí |
| Cambio de estado validado | Condición en la escritura de Neo4j; el cierre lo ordena la API |
| Guardado del árbol de una vez | No hay árbol; lo que va junto es un documento de MongoDB |

## Qué perdemos

Perdemos la herencia entre tipos de evento (acá el tipo es un atributo) y la posibilidad de consultar el partido con SQL. Para lo que hace el prode no las necesitamos. Si el sistema creciera hacia algo con reglas de negocio pesadas sobre objetos complejos, por ejemplo la planilla oficial del árbitro con sus validaciones, IRIS volvería a ser un candidato.

Los Hitos 9, 10 y 13 quedan como se entregaron, con IRIS funcionando.
