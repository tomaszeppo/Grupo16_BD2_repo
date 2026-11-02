# Decisiones de arquitectura

Defendemos el sistema que está construido en el repositorio: la API del Hito 10 con seis bases, cada una con el módulo que pidió su hito. Para cada base, este documento dice qué guarda, por qué esa base, cómo está armada, cómo escalaría, qué consistencia necesita, qué pasa si se cae y qué evidencia lo respalda. Lo que es diseño para producción y no corre en el laboratorio está marcado como **propuesta**.

## El diseño del Hito 3 frente a lo construido

En el Hito 3 propusimos un reparto por necesidad de datos. Después, cada hito pidió un módulo concreto con una base concreta, y el sistema terminó así:

| Base | Hito 3 (diseño) | Construido (Hitos 4 a 10) |
|---|---|---|
| MongoDB | Partidos finalizados y datos estáticos | Equipos y jugadores (Hito 4) |
| Neo4j | Predicciones de usuarios | Partidos, equipos, estadios y eventos (Hito 5, con la corrección de dejar usuarios y predicciones para más adelante) |
| Cassandra | Logs de partidos | Comentarios masivos por partido y país (Hito 6) |
| Redis | Estado de partidos en vivo | Sesiones y caché de usuarios (Hito 7) |
| InfluxDB | Métricas y estadísticas históricas | Estadísticas de partido por ventana (Hito 8) |
| IRIS | Grupos y puntajes | Partido como entidad compleja con su máquina de estados (Hito 9) |

El criterio de fondo es el mismo: elegir la base por el patrón de acceso. Lo que cambió es el dato concreto de cada una. Las decisiones de distribución y consistencia del Hito 3 se reinterpretan abajo para el dato que cada base guarda hoy.

## Por qué no una sola base

Cada módulo tiene un patrón de acceso distinto, y forzarlos a una sola estructura vuelve caro justo lo que más se usa:

- Los comentarios son muchas escrituras pequeñas, concentradas después de un gol, que se leen por partido, país y ventana: una tabla ancha particionada (Cassandra) escribe sin coordinar entre nodos.
- La sesión de un usuario se lee en cada pedido y vence sola: clave-valor en memoria con TTL (Redis).
- Recorrer partido → equipos → estadio → eventos son relaciones: en un grafo es seguir aristas; en tablas, varios joins.
- Las estadísticas son mediciones con fecha que se consultan por ventana y se agregan: una base de series temporales (InfluxDB).
- La ficha de un equipo con su plantel es un documento que se lee entero (MongoDB).
- El partido como objeto con reglas de transición se modela mejor con clases y métodos (IRIS).

**El costo:** seis productos para operar, seis formas de respaldo, seis lenguajes de consulta y más superficie de monitoreo. En este hito se nota: solo dos tienen exportador funcionando. La API es lo que las une. Cada endpoint consulta una sola base, salvo crear comentario (Neo4j + Cassandra), y ningún pedido de usuario consulta las seis en serie.

## MongoDB: equipos y jugadores

| Punto | Respuesta |
|---|---|
| Qué dato guarda | Fichas de selecciones (`equipos`) y planteles (`jugadores`) |
| Qué acceso motivó la elección | Leer la ficha de un equipo y su plantel filtrado por posición, muchas veces y casi sin cambios durante el torneo |
| Modelo | Documental |
| Estructura implementada | Colecciones `equipos{nombre, codigo}` y `jugadores{nombre, apellido, dorsal, equipo, posicion}`, con validación `$jsonSchema`. Índice único en `equipos.codigo`; índices en `jugadores.equipo`, `apellido` y `posicion` |
| Carga y recuperación | Carga con `upsert` por equipo y dorsal, repetible. Lectura por `GET /equipos/{codigo}` y `/equipos/{codigo}/jugadores` (paginado) |
| Escala y distribución | Laboratorio: un nodo. **Propuesta:** réplica de 3 nodos y lecturas desde secundarios, porque es dato casi estático; el sharding no hace falta con unos 1.250 jugadores |
| Consistencia necesaria | Baja: una ficha desactualizada unos segundos no rompe nada |
| Si se cae | `/equipos` responde 503. El resto de la API sigue funcionando |
| Costo que introduce | Un producto más. La validación del esquema hay que mantenerla a mano |
| Evidencia | Exportador con operaciones y conexiones en el panel; p95 desde la API de 9,4 ms como máximo en la ventana de la demo ([series](../evidencia/dashboards/demo_20261030_223042_todo/series_prometheus.json)) |

## Neo4j: partidos, equipos, estadios y eventos

| Punto | Respuesta |
|---|---|
| Qué dato guarda | El fixture como red: equipos que participan en partidos que se juegan en estadios, y eventos que ocurren en un partido |
| Qué acceso motivó la elección | Recorrer relaciones: un partido con sus equipos, su estadio y sus eventos en una sola consulta |
| Modelo | Grafo de propiedades |
| Estructura implementada | Nodos `Equipo`, `Partido`, `Estadio`, `Evento`; relaciones `PARTICIPA_EN`, `SE_JUEGA_EN`, `OCURRE_EN`. Restricciones de unicidad en los cuatro identificadores |
| Carga y recuperación | `MERGE` (repetible). `GET /partidos/{id}` y `/partidos/{id}/eventos`. Además, el alta de un comentario consulta acá si el partido existe |
| Escala y distribución | Laboratorio: un nodo Community. **Propuesta:** el grafo del fixture es chico (104 partidos); alcanza con una instancia y copias de solo lectura cerca de cada región. El clúster con réplicas es de la edición Enterprise: es un costo de licencia a decidir |
| Consistencia necesaria | Media: un partido recién cargado tiene que existir antes de aceptar comentarios sobre él |
| Si se cae | `/partidos` y **también crear comentarios** responden 503, porque el alta valida el partido en Neo4j. Es la dependencia más delicada del flujo de comentarios |
| Costo que introduce | Acoplamiento: el flujo de mayor volumen (comentarios) depende de una base que no está pensada para ese volumen. **Propuesta:** guardar en Redis, con vencimiento, la marca de "partido existe y está abierto a comentarios", y consultar Neo4j solo si falta |
| Evidencia | p95 desde la API de 44,1 ms como máximo durante el pico de comentarios ([series](../evidencia/dashboards/demo_20261030_223042_todo/series_prometheus.json)) |

## Cassandra: comentarios

| Punto | Respuesta |
|---|---|
| Qué dato guarda | Comentarios de los usuarios durante un partido, separados por país de la audiencia |
| Qué acceso motivó la elección | Muchas escrituras pequeñas con picos después de un gol, y lectura de "los comentarios de este partido, de este país, en esta media hora" |
| Modelo | Columnar de tabla ancha |
| Estructura implementada | `comentarios_por_partido_pais` con clave de partición `(partido_id, pais, ventana)` y clustering por `creado_en` descendente. `comentarios_por_likes_partido_pais` para ordenar por likes. `comentarios_idempotencia` (TTL 24 h) fija la ventana en el primer intento |
| Carga y recuperación | `INSERT ... IF NOT EXISTS` en las tres tablas: un reintento completa lo que faltó sin duplicar. Lectura paginada por partición con cursor |
| Escala y distribución | Laboratorio: un nodo, `SimpleStrategy` con factor 1. **Propuesta (Hito 3):** factor de replicación 3 entre regiones, lectura y escritura con un nodo (R=1, W=1), consistencia eventual. La partición por país y ventana reparte un partido popular en muchas particiones en lugar de una sola |
| Consistencia necesaria | Eventual para leer comentarios. La idempotencia sí exige que dos reintentos no creen dos filas, y por eso usamos transacciones livianas (`IF NOT EXISTS`) |
| Si se cae | No se puede comentar ni leer comentarios (503). Con 3 réplicas, la caída de un nodo no corta el servicio (**propuesta**, no probado en el laboratorio) |
| Costo que introduce | Las transacciones livianas cuestan varias idas y vueltas entre réplicas: son más lentas que un `INSERT` simple. Lo aceptamos para no duplicar comentarios |
| Evidencia | Hito 12: 50.000 escrituras verificadas por corrida. Hito 13: 3.000 comentarios por la API a 50/s, los 3.000 encontrados, sin faltantes ni duplicados ([resumen](../evidencia/resultados_sin_secretos/pico_comentarios_20261030_222612_resumen.json)); p95 desde la API de 85,3 ms como máximo |

## Redis: sesiones

| Punto | Respuesta |
|---|---|
| Qué dato guarda | La sesión de cada usuario conectado: estado de acceso, rol, último acceso, acciones |
| Qué acceso motivó la elección | Se lee en cada pedido del usuario y tiene que vencer sola por inactividad |
| Modelo | Clave-valor en memoria |
| Estructura implementada | Hash `f2030:sesion:{usuario}` con TTL de 1.800 s; `maxmemory 128mb` con política `volatile-lru`; persistencia `appendonly yes` |
| Carga y recuperación | `GET /sesiones/{usuario}` lee el hash; `DELETE` lo invalida. El TTL lo maneja Redis |
| Escala y distribución | Laboratorio: un nodo. **Propuesta (Hito 3):** activo con réplica de respaldo; para 3 millones de sesiones, partición por usuario (Redis Cluster). Estimamos entre 3 y 6 GB solo de datos con 1 a 2 KB por sesión (estimación, no medición) |
| Consistencia necesaria | Leer la propia escritura: si cierro sesión, no puede seguir válida. La réplica asíncrona puede perder la última escritura al cambiar de nodo; el costo es que algunos usuarios vuelvan a iniciar sesión |
| Si se cae | `/sesiones` responde 503; comentarios, partidos y estadísticas siguen funcionando. **Probado:** Redis detenido 91 s; la sesión de `U001` volvió a responder 200 al reiniciar, gracias a la persistencia en disco ([evidencia](../evidencia/prueba_de_falla_20261030_223027.json)) |
| Costo que introduce | Todo está en memoria: si se llena, expulsa sesiones con TTL. Por eso el panel muestra la memoria usada frente al límite |
| Evidencia | Prueba de falla y panel de memoria y comandos del exportador |

## InfluxDB: estadísticas de partido

| Punto | Respuesta |
|---|---|
| Qué dato guarda | Mediciones con fecha: posesión, pases, tiros, recuperaciones y velocidad, por partido, equipo y fuente |
| Qué acceso motivó la elección | Consultar una ventana de tiempo acotada y agregarla (promedio, máximo) |
| Modelo | Series temporales |
| Estructura implementada | Base `fixture2030_metrics` (retención 90 días), tabla `estadisticas_partido` con tags `partido_id, equipo_id, sede, fuente, fase` y cinco campos numéricos |
| Carga y recuperación | Escritura en line protocol (reescribir el mismo instante no duplica). `GET /partidos/{id}/estadisticas` con ventana y agregación |
| Escala y distribución | Laboratorio: un nodo. **Propuesta (Hito 3):** réplica asíncrona entre nodos regionales; partición por partido y período |
| Consistencia necesaria | Eventual: un retraso breve en una estadística es aceptable si la ingesta no se frena |
| Si se cae | `/estadisticas` responde 503. Las mediciones que lleguen durante la caída se pierden si nadie las retiene: hace falta una cola delante (**propuesta**) |
| Costo que introduce | Un producto con su propio lenguaje de consulta; cada combinación de tags crea series, así que hay que cuidar no agregar tags de mucha variedad |
| Evidencia | 4.800 puntos sembrados; p95 desde la API de 9,1 ms como máximo en la ventana de la demo |

## IRIS: el partido como objeto

| Punto | Respuesta |
|---|---|
| Qué dato guarda | El partido como entidad compleja con sus eventos hijos y su estado |
| Qué acceso motivó la elección | Encapsular reglas: un partido no puede pasar de "Programado" a "Finalizado" sin jugarse, ni recibir eventos una vez terminado |
| Modelo | Objetos (multimodelo) |
| Estructura implementada | Clases del Hito 9 (`Fixture.Partido`, `Fixture.Evento`, etc.) con `CambiarEstado()` y `AgregarEvento()` |
| Carga y recuperación | `GET /partidos/{id}/detalle` y `POST /partidos/{id}/estado` |
| Escala y distribución | Laboratorio: un nodo. **Propuesta (Hito 3):** activo con réplicas sincronizadas (mirroring), porque el estado oficial del partido no admite dos versiones |
| Consistencia necesaria | Fuerte: todos tienen que ver el mismo estado del partido |
| Si se cae | No se puede consultar el detalle ni cambiar el estado (503). Ante una partición de red, preferimos rechazar el cambio antes que tener dos estados distintos |
| Costo que introduce | Producto comercial (la edición Community tiene límites); en el laboratorio el usuario de la API tiene más permisos de los necesarios (`%All`) |
| Evidencia | `P-05`: `Programado → En juego` (200), `→ Finalizado` (200), volver a `En juego` rechazado con 409 ([evidencia](../evidencia/estado_partido_20261030_222740.json)) |

## Preguntas transversales

**¿Qué datos son operacionales y cuáles podrían ir a una vista analítica?** Los seis módulos son operacionales: atienden pedidos de usuarios. La actividad de comentarios por partido y minuto ya la proyectamos en el Data Mart del Hito 12, fuera del camino de la API. Las métricas de Prometheus también son analíticas, pero sobre la plataforma, no sobre el torneo.

**¿Dónde hay caché y cómo vence?** En Redis: las sesiones vencen por TTL (30 minutos de inactividad). La API no tiene otra caché hoy. La marca de "partido abierto a comentarios" es una propuesta.

**¿Cómo se evita que una consulta de alto volumen bloquee todo?**
- Cada endpoint toca una sola base, así que un problema en una base no frena a las otras. Lo vimos en la prueba de falla: con Redis caído, los comentarios siguieron devolviendo 201.
- La API tiene un tiempo máximo por pedido (504) y paginación con límite de 100 en las lecturas.
- El punto débil que encontramos es que los pedidos a una base caída esperan su timeout completo (ver [mejora transversal](limitaciones_y_evidencia.md#mejora-transversal-propuesta)).

**¿Qué haríamos si una base queda indisponible?** Seguir atendiendo lo que no depende de ella (la API ya lo hace), avisar con la alerta `BaseNoDisponible` y recuperar la base. Si es Neo4j, también se cortan los comentarios, y por eso proponemos desacoplar esa validación.

**¿Qué costo operativo agrega mantener seis productos?** Seis configuraciones, seis estrategias de respaldo, seis lenguajes de consulta, más superficie de seguridad, y monitoreo desparejo: solo Redis y MongoDB tienen exportador acá. Lo compensamos con la API como punto único de entrada y con métricas medidas desde la API, que tratan a las seis bases con la misma vara.

**¿Qué parte de la escalabilidad está medida y qué parte es proyección?** Ver [limitaciones y evidencia](limitaciones_y_evidencia.md#medido-frente-a-proyectado).
