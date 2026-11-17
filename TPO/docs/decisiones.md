# Decisiones sobre las bases

Esta parte del proyecto final usa dos bases: **MongoDB** para todo lo del prode y **Neo4j** para el fixture y lo que pasa en cada partido. Redis, Cassandra e InfluxDB se suman sobre esta base ([cómo](como_sumar_una_base.md)). IRIS quedó afuera ([por qué](por_que_no_iris.md)).

Para cada base respondemos los diez puntos que pide la consigna del Hito 13. Donde decimos que algo está medido, el número y el archivo están en [rendimiento.md](rendimiento.md).

## Qué base manda sobre cada dato

| Dato | Manda | Copias |
|---|---|---|
| Usuarios, prodes privados, pronósticos | MongoDB | — |
| Resultado de un partido, a efectos del prode | MongoDB (`resultados`) | Neo4j guarda el marcador en el partido, para mostrarlo; lo escribe la misma operación de cierre |
| Puntajes y versiones históricas del ranking | MongoDB | El ranking en vivo irá a Redis y se reconstruye desde `puntajes` |
| Calendario, equipos de cada partido, estado, jugadas | Neo4j | Cada proceso de la API guarda una copia del calendario en memoria, de hasta 30 segundos |
| Catálogo de equipos y planteles | Se cargan en las dos desde el mismo archivo, con los mismos identificadores | MongoDB lo sirve como ficha; Neo4j lo usa para relacionar |

Los identificadores son los mismos en todas partes (`P-07`, `ARG`, `J-ARG-09`, `U0000001`). Nadie traduce identificadores entre bases; es la corrección que nos hicieron en el Hito 10.

El catálogo duplicado es la única copia de datos entre las dos bases. La aceptamos porque no cambia durante el torneo y porque cada base lo usa para algo distinto. No hay sincronización que mantener: si hubiera que corregir un plantel, se corrige el archivo de datos y se vuelve a correr la carga, que no duplica.

---

## MongoDB

**1. Qué guarda.** Usuarios, prodes privados con sus integrantes, un pronóstico por usuario y partido, el resultado de cada partido cerrado con el estado de su puntuación, el puntaje acumulado de cada usuario, una foto del ranking tras cada partido y el catálogo de equipos y jugadores.

**2. Qué accesos motivaron elegirla.** Casi todo lo del prode se lee y se escribe por clave o por un atributo simple: mi pronóstico de este partido, mis pronósticos, mis prodes, los pronósticos de un partido para puntuarlos, los primeros del ranking. No hay recorridos de relaciones. Además cada cosa tiene forma propia (un prode lleva una lista de integrantes; un resultado lleva adentro el avance de su puntuación), y un documento la guarda entera.

**3. Modelo.** Documental. Un documento por usuario, por prode, por pronóstico, por resultado y por puntaje.

**4. Estructura concreta.** Está detallada en [modelo_de_datos.md](modelo_de_datos.md). Lo que decidimos y por qué:

- *El pronóstico tiene como clave el usuario y el partido* (`U0000001:P-07`). Así no puede haber dos pronósticos del mismo usuario para el mismo partido, y cargar o corregir es una sola escritura. Lo probamos con 20 pedidos simultáneos del mismo usuario: queda un documento ([prueba](../tests/integration/test_prode_real.py)).
- *El prode general no guarda integrantes.* Son todos los usuarios; una lista de millones de identificadores no entra en un documento (el tope es 16 MB) y nadie la pediría entera.
- *Los prodes privados sí llevan a sus integrantes adentro*, porque están acotados a 100 y siempre se leen juntos. El tope se controla en la misma operación que agrega al integrante: con 99 adentro y 10 uniéndose a la vez, entra uno solo ([prueba](../tests/integration/test_prode_real.py)).
- *No hay un ranking guardado por prode privado.* Su tabla se arma al pedirla con los puntajes de sus integrantes. Así cerrar un partido cuesta una escritura por usuario, no una por cada prode de cada usuario.
- *Validación de esquema* en usuarios, prodes y pronósticos: la base rechaza, por ejemplo, un pronóstico con goles negativos aunque llegue por fuera de la API.

**5. Cómo se carga y se lee.** La carga del catálogo usa `upsert`: repetirla deja los mismos totales (`python -m seed.run --verificar` lo comprueba y falla si cambian). Es la corrección del Hito 4. Las lecturas van por índice: `pronosticos` por usuario y por partido; `puntajes` por el mismo orden del ranking, así los primeros puestos salen de recorrer el índice sin ordenar nada.

**6. Distribución.** Un conjunto de réplicas de tres nodos. Las escrituras piden confirmación de la mayoría; el ranking se puede leer de un secundario. Fragmentar no está construido: la clave que usaríamos (por usuario) y qué consultas quedarían dirigidas a un solo fragmento están en la proyección de [rendimiento.md](rendimiento.md#4-proyección-al-mundial-no-medido).

**7. Consistencia.** Los pronósticos y los resultados necesitan no perderse: por eso la confirmación de la mayoría. Medido, cuesta alrededor de un tercio de las escrituras frente a confirmar con un solo nodo sin esperar al diario. El ranking tolera atraso: mientras se suman los puntos de un partido, quien consulte puede ver a unos usuarios con el partido aplicado y a otros todavía no, sobre todo leyendo de un secundario. Lo aceptamos porque dura lo que tarda la suma y no deja nada mal al terminar.

**8. Qué pasa si falla.** Con un nodo caído el conjunto sigue. Medido: si el primario se apaga con orden no hay ningún error; si se corta de golpe, unos 10 segundos sin poder escribir (la API responde 503) hasta que los otros dos eligen un nuevo primario, y lo ya confirmado no se pierde. Si MongoDB entero no responde, no hay prode: la API devuelve 503 y el fixture se sigue viendo.

**9. Costo.** Tres nodos para una sola base. La consistencia entre documentos queda a cargo nuestro: no usamos transacciones de varios documentos, así que cada paso del cierre de un partido está escrito para poder repetirse sin efecto. Y MongoDB resuelve mal "en qué puesto estoy": tiene que contar cuántos están mejor.

**10. Evidencia.** Carga repetida, unicidad y validación: [test_carga.py](../tests/integration/test_carga.py). Puntuación comparada documento por documento contra las reglas, cierres simultáneos y reinicio de una puntuación a medias: [test_puntuacion_real.py](../tests/integration/test_puntuacion_real.py). Rendimiento, costo de la mayoría, cierre de partido, puesto en el ranking y caídas: [rendimiento.md](rendimiento.md).

### El cierre de un partido

Es la operación más delicada del prode y la única que escribe en las dos bases.

1. Se guarda el resultado en MongoDB. Si ya había uno con el mismo marcador, se sigue; con otro marcador, se rechaza.
2. Se marca el partido como finalizado en Neo4j.
3. Se puntúan los pronósticos del partido con una sola actualización que corre dentro de MongoDB, sin traerlos a la API.
4. Se suma a cada usuario lo de ese partido, salvo que ya lo tenga sumado: cada puntaje lleva la lista de partidos aplicados.
5. Se guarda la foto del ranking.

Si algo se corta en el medio, se repite el mismo pedido: el paso 1 encuentra el resultado, el 3 vuelve a escribir los mismos valores y el 4 no suma dos veces. Si llegan varios cierres a la vez, uno solo toma la puntuación (probado con 8 simultáneos). Las reglas de puntos y desempate están en [`app/dominio/puntuacion.py`](../app/dominio/puntuacion.py), y una prueba verifica que lo que calcula MongoDB coincide con esa función en cada pronóstico.

Los goles en contra no se modelan: un gol cuenta para el equipo del jugador que lo hizo.

---

## Neo4j

**1. Qué guarda.** Equipos, jugadores, estadios, los 104 partidos con su estado y las jugadas de cada partido, con quién las protagonizó y cuál llevó a cuál. También el cuadro de eliminatorias: qué partido alimenta a cuál.

**2. Qué accesos motivaron elegirlo.** Preguntas que son recorridos: qué jugadas llevaron a este gol, qué jugadores participaron en más goles (contando a los que dieron el pase), qué le queda a un equipo hasta la final. En las tres hay que seguir relaciones un número de pasos que no se conoce de antemano.

**3. Modelo.** Grafo de propiedades.

**4. Estructura concreta.** Nodos `Equipo`, `Jugador`, `Estadio`, `Partido` y `Evento` (una jugada). Relaciones: `PERTENECE_A`, `PARTICIPA_EN` (con la condición de local o visitante), `SE_JUEGA_EN`, `OCURRE_EN`, `PROTAGONIZA`, `INFLUYE_EN` entre jugadas y `CLASIFICA_A` entre partidos. Mantuvimos los nombres de los Hitos 5 y 10. **No hay usuarios, grupos ni predicciones en el grafo**: es la corrección del Hito 5, y en el proyecto final esos datos viven en MongoDB.

**5. Cómo se carga y se lee.** Todo con `MERGE` y restricciones de unicidad: la carga se puede repetir. Una recarga no pisa el estado ni el marcador de un partido que ya empezó. Las consultas de la API son fijas y con parámetros; quien llama no aporta texto de consulta.

**6. Distribución.** Una sola instancia. La edición comunitaria no arma clúster, y lo decimos como límite, no como decisión.

**7. Consistencia.** Cada operación es una transacción. El estado de un partido cambia en un solo sentido (programado, en juego, finalizado) y repetir el cambio no tiene efecto: poner en juego dos veces no mueve el momento de inicio.

**8. Qué pasa si falla.** No se puede ver el detalle de un partido, sus jugadas ni operar partidos: la API devuelve 503. **Se puede seguir pronosticando y viendo el fixture**, con la copia del calendario. Medido: 9.301 pronósticos sin un error con Neo4j caído.

**9. Costo.** Un producto más para operar, con un único punto de falla en esta edición. La primera vez que ve una consulta tarda en armar el plan, y en el laboratorio eso superaba el tiempo de espera de un pedido: por eso la API hace que Neo4j planifique todas sus consultas al arrancar.

**10. Evidencia.** Carga repetida y unicidad: [test_carga.py](../tests/integration/test_carga.py). Recorridos (cadena de un gol, participación en goles, camino por el cuadro): [test_fixture_real.py](../tests/integration/test_fixture_real.py). Lecturas bajo carga y caída: [rendimiento.md](rendimiento.md).

### Por qué no guardar las jugadas en MongoDB

Se podría: cada partido con su lista de jugadas adentro. Leer el partido entero sería más simple. Lo que se complica es justo lo que queremos preguntar: "qué llevó a este gol" obliga a seguir referencias entre jugadas dentro de la lista, y "quiénes participaron en más goles de todo el torneo" obliga a hacerlo para todos los partidos. En el grafo las dos son un recorrido de `INFLUYE_EN`.

---

## La copia del calendario

Para aceptar un pronóstico hay que saber si el partido existe, si tiene equipos y si no empezó. Esos datos los gobierna Neo4j, pero consultarlo en cada pronóstico lo ponía en el camino del pico. Cada proceso de la API guarda entonces una copia de los 104 partidos y la renueva cada 30 segundos.

Qué ganamos, medido: más del doble de pronósticos por segundo, y que la caída de Neo4j no impida pronosticar.

Qué cuesta: cuando se pone un partido en juego antes de su horario, el proceso que atendió ese pedido cierra los pronósticos en el acto, pero los otros procesos pueden tardar hasta 30 segundos en enterarse y aceptar alguno más. Para que eso no cuente, Neo4j guarda el momento real de inicio y la puntuación **anula** todo pronóstico cargado en ese momento o después: queda guardado, pero vale cero y se marca como anulado. El cierre por horario no tiene este problema, porque el horario ya está en la copia.

La renovación de la copia nunca frena a los demás pedidos; ese detalle lo encontró la prueba de caída y está contado en [rendimiento.md](rendimiento.md#28-fallas-controladas-durante-la-carga).

Cuando esté Redis, esta copia puede pasar ahí: sería una sola para todos los procesos y el atraso desaparecería.

## Simplificaciones de laboratorio

- **Sin autenticación.** La API toma el usuario del encabezado `X-Usuario-Id` y solo verifica que exista. Las sesiones llegan con Redis; el punto de enganche ya está.
- **Administración con una clave fija** en un encabezado, para poder operar partidos en la demostración.
- **El calendario se ubica desde la fecha de carga**, para que haya partidos abiertos. La regla de habilitar los pronósticos 3 días antes del Mundial no se aplica.
- **Los equipos de las eliminatorias se asignan a mano.** No calculamos las tablas de los grupos.
- **Datos sintéticos.** Los equipos llevan nombres de países para que el fixture se lea fácil; todo lo demás es inventado.
