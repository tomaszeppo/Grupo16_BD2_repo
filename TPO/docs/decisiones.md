# Decisiones sobre las bases

El proyecto final usa cinco bases: **MongoDB** para todo lo del prode, **Neo4j** para el fixture y lo que pasa en cada partido, **Redis** para las sesiones, el partido en vivo y el ranking, **Cassandra** para los comentarios e **InfluxDB** para las series de cada partido (estadísticas y audiencia). IRIS quedó afuera ([por qué](por_que_no_iris.md)). Cómo se reparten entre regiones está en [arquitectura por regiones](arquitectura_regiones.md).

Para cada base respondemos los diez puntos que pide la consigna del Hito 13. Donde decimos que algo está medido, el número y el archivo están en [rendimiento.md](rendimiento.md).

## Qué base manda sobre cada dato

| Dato | Manda | Copias |
|---|---|---|
| Usuarios, prodes privados, pronósticos | MongoDB | — |
| Resultado de un partido, a efectos del prode | MongoDB (`resultados`) | Neo4j guarda el marcador en el partido, para mostrarlo; lo escribe la misma operación de cierre |
| Puntajes y versiones históricas del ranking | MongoDB | Redis tiene el ranking en vivo (un conjunto ordenado). Al cerrar un partido se actualiza primero y los puntajes llegan a MongoDB segundos después; si Redis se pierde, se reconstruye desde `puntajes` |
| Sesiones | Redis | — |
| Quién está mirando cada partido ahora | Redis | El conteo por minuto queda en InfluxDB |
| Comentarios | Cassandra | Una copia por región; Redis los reparte en vivo sin guardarlos |
| Estadísticas de la simulación, audiencia y comentarios por minuto | InfluxDB | Al terminar el partido, las estadísticas se archivan en Neo4j; la audiencia queda solo en InfluxDB |
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

**7. Consistencia.** Los pronósticos y los resultados necesitan no perderse: por eso la confirmación de la mayoría. Medido, cuesta entre un cuarto y un tercio de las escrituras (según la corrida) frente a confirmar con un solo nodo sin esperar al diario. El ranking tolera atraso: mientras se suman los puntos de un partido, quien consulte puede ver a unos usuarios con el partido aplicado y a otros todavía no, sobre todo leyendo de un secundario. Lo aceptamos porque dura lo que tarda la suma y no deja nada mal al terminar.

**8. Qué pasa si falla.** Con un nodo caído el conjunto sigue. Medido dos veces, con resultados distintos: el 17/11, apagar el primario con orden no dio errores y cortarlo de golpe dejó unos 10 segundos sin poder escribir (503); el 20/11, cortarlo de golpe no dio errores y apagarlo con orden tampoco al caer, pero sí 60 errores (503) en unos segundos después de que el nodo volvió. En todos los casos lo ya confirmado no se perdió ([rendimiento.md](rendimiento.md#28-fallas-controladas-durante-la-carga)). Si MongoDB entero no responde, no hay prode: la API devuelve 503 y el fixture se sigue viendo.

**9. Costo.** Tres nodos para una sola base. La consistencia entre documentos queda a cargo nuestro: no usamos transacciones de varios documentos, así que cada paso del cierre de un partido está escrito para poder repetirse sin efecto. Y MongoDB resuelve mal "en qué puesto estoy": tiene que contar cuántos están mejor. Por eso el ranking en vivo se lee de Redis.

**10. Evidencia.** Carga repetida, unicidad y validación: [test_carga.py](../tests/integration/test_carga.py). Puntuación comparada documento por documento contra las reglas, cierres simultáneos y reinicio de una puntuación a medias: [test_puntuacion_real.py](../tests/integration/test_puntuacion_real.py). Rendimiento, costo de la mayoría, cierre de partido, puesto en el ranking y caídas: [rendimiento.md](rendimiento.md).

### El cierre de un partido

Es la operación más delicada del prode y la única que escribe en las dos bases.

1. Se guarda el resultado en MongoDB. Si ya había uno con el mismo marcador, se sigue; con otro marcador, se rechaza.
2. Se marca el partido como finalizado en Neo4j.
3. Se puntúan los pronósticos del partido y se actualiza el ranking en Redis, por lotes. Cada usuario se aplica con una operación atómica que anota que ese partido ya se le sumó.
4. Pasada una espera (15 segundos por defecto), los puntos se vuelcan a MongoDB: cada pronóstico con su puntaje y cada usuario con su acumulado, salvo que ya tenga sumado ese partido (cada puntaje lleva la lista de partidos aplicados).
5. Se guarda la foto del ranking.

El ranking se ve actualizado apenas termina el paso 3; MongoDB lo alcanza en el paso 4. Con `REDIS_ENABLED=false` los pasos 3 y 4 corren enteros dentro de MongoDB (una actualización que puntúa y otra que suma), que es como funcionaba antes de sumar Redis; los dos caminos están medidos en [rendimiento.md](rendimiento.md).

Si algo se corta en el medio, se repite el mismo pedido: el paso 1 encuentra el resultado, el 3 no vuelve a aplicar a quien ya lo tiene y el 4 no suma dos veces. Si llegan varios cierres a la vez, uno solo toma la puntuación (probado con 8 simultáneos). No hace falta repetirlo a mano: cada proceso de la API busca cada 30 segundos las puntuaciones que quedaron pendientes, fallidas o tomadas por un proceso que dejó de dar señales (120 segundos sin terminar un paso) y las retoma, hasta cinco intentos por partido. Las reglas de puntos y desempate están en [`app/dominio/puntuacion.py`](../app/dominio/puntuacion.py), y una prueba verifica que lo que calcula MongoDB coincide con esa función en cada pronóstico.

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

**8. Qué pasa si falla.** No se puede ver el detalle de un partido, sus jugadas ni operar partidos: la API devuelve 503. **Se puede seguir pronosticando y viendo el fixture**, con la copia del calendario. Medido: 19.499 pronósticos sin un error en una corrida en la que Neo4j estuvo caído 30 segundos.

**9. Costo.** Un producto más para operar, con un único punto de falla en esta edición. La primera vez que ve una consulta tarda en armar el plan, y en el laboratorio eso superaba el tiempo de espera de un pedido: por eso la API hace que Neo4j planifique todas sus consultas al arrancar.

**10. Evidencia.** Carga repetida y unicidad: [test_carga.py](../tests/integration/test_carga.py). Recorridos (cadena de un gol, participación en goles, camino por el cuadro): [test_fixture_real.py](../tests/integration/test_fixture_real.py). Lecturas bajo carga y caída: [rendimiento.md](rendimiento.md).

### Por qué no guardar las jugadas en MongoDB

Se podría: cada partido con su lista de jugadas adentro. Leer el partido entero sería más simple. Lo que se complica es justo lo que queremos preguntar: "qué llevó a este gol" obliga a seguir referencias entre jugadas dentro de la lista, y "quiénes participaron en más goles de todo el torneo" obliga a hacerlo para todos los partidos. En el grafo las dos son un recorrido de `INFLUYE_EN`.

---

## Redis

**1. Qué guarda.** Las sesiones, el ranking en vivo, quién está mirando cada partido en este momento, los espectadores únicos de cada partido y los contadores de comentarios del minuto en curso. También reparte cada comentario entre los procesos de la API (publicación y suscripción) y lleva las marcas del modo lento y de los comentarios repetidos.

**2. Qué accesos motivaron elegirlo.** Todo es lectura o escritura de una clave en el camino de cada pedido, o datos que viven segundos: validar una sesión en cada pedido; renovar la presencia de miles de conexiones cada pocos segundos; contar cuántos dieron señal en los últimos 15 segundos; avisar a todos los procesos que llegó un comentario. Necesita vencimiento automático y que todos los procesos de la API vean lo mismo.

**3. Modelo.** Clave-valor con estructuras: texto, conjuntos ordenados, conjuntos, HyperLogLog y canales.

**4. Estructura concreta.** Las claves están en [modelo_de_datos.md](modelo_de_datos.md#redis). Lo que decidimos y por qué:

- *La presencia es un conjunto ordenado con la hora de la última señal como puntaje.* Contar los activos es borrar los vencidos y contar lo que queda. Si un proceso de la API muere sin avisar, sus espectadores dejan de contar solos a los 15 segundos: no quedan espectadores fantasma.
- *Un espectador es una sesión*: varias pestañas con la misma sesión cuentan una vez. Los únicos se cuentan por usuario con un HyperLogLog, que ocupa lo mismo con cien o con un millón de usuarios.
- *Una sola suscripción por proceso*, compartida por todas sus conexiones: un proceso con mil espectadores no abre mil suscripciones.
- *No se guarda el token en la presencia*, sino un resumen de él.
- *El ranking es un conjunto ordenado* cuyo puntaje junta en un solo número los puntos, los exactos y el tiempo acumulado, en ese orden de importancia. El puesto de un usuario es una sola consulta (`ZREVRANK`), sin contar a nadie. El miembro es el número de usuario invertido, para que a igualdad total quede primero el identificador más bajo, igual que en MongoDB.

**5. Cómo se carga y se lee.** Lo escribe la API al vuelo. Las sesiones para las pruebas de carga se crean por lotes ([`carga/sesiones.py`](../carga/sesiones.py)).

**6. Distribución.** Un primario y una réplica de solo lectura, que representa "la otra región". En el laboratorio la API lee y escribe todo en el primario: la réplica está para medir cuánto tarda en llegarle un cambio, no la consulta ningún pedido. En producción, un Redis por región para sesiones, presencia y chat, y réplicas del primario central para leer el ranking ([arquitectura por regiones](arquitectura_regiones.md)).

**7. Consistencia.** La réplica copia sin que el primario la espere: lo que se lee ahí puede llegar con atraso; medido en [rendimiento.md](rendimiento.md#29-partido-en-vivo). La presencia tolera unos segundos de error a propósito: es un conteo para el análisis, no un dato que se cobre.

**8. Qué pasa si falla.** Sin Redis no hay sesiones: toda ruta que necesita saber quién pide responde 503 (no se vuelve a confiar en lo que mande el cliente). La conexión en vivo se cierra con un aviso y el navegador reintenta solo. La simulación no se corta: los minutos sin Redis quedan sin audiencia y se marcan (`audiencia_incompleta`). Las sesiones sobreviven a un reinicio porque Redis guarda en disco cada segundo (AOF).

**9. Costo.** Una pieza más que, si se cae, deja a todos sin sesión. Por eso tiene réplica, y en producción tendría conmutación automática. La memoria crece con las sesiones abiertas, las conexiones en vivo y la cantidad de usuarios con puntaje, no con el historial. Sesiones, partido en vivo y ranking comparten una sola instancia con un tope de memoria sin desalojo: si se llena, Redis rechaza escrituras (no se abren sesiones ni se puntúa) en vez de borrar datos. En producción irían separados, como dice la arquitectura por regiones.

**10. Evidencia.** Sesiones, vencimiento y Redis caído: [test_sesiones.py](../tests/unit/test_sesiones.py). Presencia, tribunas y conexiones cortadas: [test_vivo.py](../tests/unit/test_vivo.py). Contra Redis real: [test_redis_real.py](../tests/integration/test_redis_real.py). Atraso de la réplica y carga del partido en vivo: [rendimiento.md](rendimiento.md#29-partido-en-vivo).

---

## Cassandra

**1. Qué guarda.** Los comentarios de cada partido, por país.

**2. Qué accesos motivaron elegirla.** Muchas escrituras pequeñas a la vez (un gol hace comentar a todos juntos) y una sola forma de leer: los últimos comentarios de una tribuna. Nunca se busca un comentario suelto ni se cruzan datos. Además, los comentarios priorizan seguir funcionando antes que estar al día en todas partes, y Cassandra replica entre regiones sin un nodo principal.

**3. Modelo.** Columnas anchas, con la tabla pensada para la consulta.

**4. Estructura concreta.** En [modelo_de_datos.md](modelo_de_datos.md#cassandra--keyspace-fixture2030). La partición es partido, país y media hora: es exactamente lo que lee una tribuna, y acota el tamaño de cada partición en un partido largo. Dentro de la partición, del más nuevo al más viejo.

**5. Cómo se carga y se lee.** Escribe la API, en la región del país del usuario. Un reintento del mismo comentario no se duplica: la clave lleva la hora del servidor, así que la tabla sola no lo evitaría; lo frena una marca en Redis (`visto:`) de 10 minutos. Reintentar después de 10 minutos sí duplicaría; lo aceptamos.

**6. Distribución.** Un datacenter por región (`america` y `europa`), cada uno con una copia completa. En el laboratorio, un nodo por región; en producción, tres por región con replicación 3.

**7. Consistencia.** `LOCAL_ONE`: cada escritura confirma en su región sin esperar a la otra, que recibe la copia por detrás. Un hincha de Europa puede ver un comentario de América con un instante de atraso; nunca se pierde.

**8. Qué pasa si falla.** Si se cae la región de un usuario, la API escribe y lee en la otra, lo informa (`region_atendida`) y lo cuenta en una métrica. Al volver, la región caída recibe lo que se escribió en el corte. Medido en [rendimiento.md](rendimiento.md#29-partido-en-vivo). Si se caen las dos, comentar responde 503 y el partido sigue.

**9. Costo.** Dos nodos de unos 750 MB cada uno en el laboratorio, el mayor consumo de memoria del proyecto. Una tabla por consulta: si mañana se quisiera leer "los comentarios de un usuario", haría falta otra tabla.

**10. Evidencia.** Cambio de región y comentarios repetidos: [test_cassandra_adaptador.py](../tests/unit/test_cassandra_adaptador.py), [test_comentarios.py](../tests/unit/test_comentarios.py). Escribir en una región y leer en la otra: [test_cassandra_real.py](../tests/integration/test_cassandra_real.py). Caída de una región durante un partido: [rendimiento.md](rendimiento.md#29-partido-en-vivo).

---

## InfluxDB

**1. Qué guarda.** Las series de cada partido simulado: estadísticas por jugador y minuto, jugadas, audiencia por país y minuto, comentarios por minuto y los espectadores únicos.

**2. Qué accesos motivaron elegirla.** Todo es "por minuto": cuántos miraban en el minuto 23, cuánto tuvo la pelota cada equipo entre el 30 y el 45, en qué minuto de un partido hay más audiencia en promedio. Son agregaciones por tiempo sobre muchas filas que se escriben una vez y no se modifican.

**3. Modelo.** Series de tiempo, con consultas en SQL.

**4. Estructura concreta.** En [modelo_de_datos.md](modelo_de_datos.md#influxdb--tres-bases). Solo son etiquetas las dimensiones por las que se filtra o agrupa (partido, país, origen, corrida, tipo); el minuto y los valores son campos. Es la corrección del Hito 8 sobre la cardinalidad.

**5. Cómo se carga y se lee.** Escribe el simulador una vez por minuto simulado. Las escrituras no esperan el volcado a disco de InfluxDB: esperándolo, cada una tardaba cerca de un segundo y el partido, que simula un minuto por segundo, se atrasaba al doble. A cambio, una caída de InfluxDB puede perder el último segundo de muestras, que el archivo del partido detecta como faltantes.

**6. Distribución.** Una instancia. En producción, una por región con un proceso que consolida en la central ([arquitectura por regiones](arquitectura_regiones.md)).

**7. Consistencia.** No hace falta más que la de una sola instancia: cada fila se escribe una vez y no se corrige.

**8. Qué pasa si falla.** La simulación sigue; los minutos sin escribir se marcan como incompletos y el archivo del partido queda pendiente hasta reintentarlo. El análisis de audiencia no responde (503) mientras no vuelva.

**9. Costo.** Los datos crudos de cada simulación vencen a los 7 días (antes se archivan en Neo4j); los resúmenes, la audiencia y los comentarios por minuto no vencen y crecen con cada partido: 91 filas de audiencia y 182 de comentarios por país y partido. Para un torneo de 104 partidos es poco; en producción, con muchos países, convendría resumir los partidos terminados.

**10. Evidencia.** Formato de las filas y escrituras sin espera: [test_influx_simulacion.py](../tests/unit/test_influx_simulacion.py). Cierre de cada minuto: [test_audiencia.py](../tests/unit/test_audiencia.py). Análisis de audiencia y tramos: [test_analisis_audiencia.py](../tests/unit/test_analisis_audiencia.py).

---

## La copia del calendario

Para aceptar un pronóstico hay que saber si el partido existe, si tiene equipos y si no empezó. Esos datos los gobierna Neo4j, pero consultarlo en cada pronóstico lo ponía en el camino del pico. Cada proceso de la API guarda entonces una copia de los 104 partidos y la renueva cada 30 segundos.

Qué ganamos, medido: casi el doble de pronósticos por segundo (227,7 contra 115,7 con 50 usuarios), y que la caída de Neo4j no impida pronosticar.

Qué cuesta: cuando se pone un partido en juego antes de su horario, el proceso que atendió ese pedido cierra los pronósticos en el acto, pero los otros procesos pueden tardar hasta 30 segundos en enterarse y aceptar alguno más. Para que eso no cuente, Neo4j guarda el momento real de inicio y la puntuación **anula** todo pronóstico cargado en ese momento o después: queda guardado, pero vale cero y se marca como anulado. El cierre por horario no tiene este problema, porque el horario ya está en la copia.

La renovación de la copia nunca frena a los demás pedidos; ese detalle lo encontró la prueba de caída y está contado en [rendimiento.md](rendimiento.md#28-fallas-controladas-durante-la-carga).

Esta copia podría pasar a Redis: sería una sola para todos los procesos y el atraso desaparecería. No lo hicimos porque pondría a Redis en el camino de cada pronóstico más de lo que ya está (hoy solo valida la sesión).

## Simplificaciones de laboratorio

- **Sin contraseñas.** Hay sesiones de verdad en Redis, pero abrir una es elegir un usuario: no se pide contraseña.
- **Administración con una clave fija** en un encabezado, para poder operar partidos en la demostración.
- **El calendario se ubica desde la fecha de carga**, para que haya partidos abiertos. La regla de habilitar los pronósticos 3 días antes del Mundial no se aplica.
- **Se puede pronosticar pasado el horario programado, hasta que el partido se pone en juego** (`PRONOSTICOS_HASTA_INICIO_REAL=true`, el valor con el que levanta Compose). Sirve para la demostración, donde los partidos se inician a mano y no a su hora. La validación sigue saliendo de la copia del calendario, no de Neo4j: lo único que cambia es que no se compara contra el horario. Un pronóstico que entra después del inicio real se anula al puntuar, igual que en el caso anterior. Con `false` rige el cierre por horario.
- **Los equipos de las eliminatorias se asignan a mano.** No calculamos las tablas de los grupos.
- **Datos sintéticos.** Los equipos llevan nombres de países para que el fixture se lea fácil; todo lo demás es inventado.
- **"Mirar" un partido es tener abierta su página.** No hay video; la conexión en vivo de la página es la señal de que alguien mira.
- **Dos regiones en una máquina.** La separación de datos y la caída de una región son reales; la distancia entre regiones no.
