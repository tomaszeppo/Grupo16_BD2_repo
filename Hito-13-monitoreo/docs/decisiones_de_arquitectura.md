# Decisiones de arquitectura

Defendemos la arquitectura vigente: la API del Hito 10 con cinco bases. MongoDB conserva documentos persistentes e historial; Redis resuelve estado efímero y cálculos en tiempo real; Neo4j representa la estructura del fixture; InfluxDB registra series temporales; Cassandra guarda comentarios en vivo. Las funciones de prode/ranking descritas como objetivo no están implementadas en los endpoints actuales.

## El diseño del Hito 3 frente a lo construido

En el Hito 3 propusimos un reparto por necesidad de datos. Después, cada hito pidió un módulo concreto con una base concreta, y el sistema terminó así:

| Base | Hito 3 (diseño) | Construido (Hitos 4 a 10) |
|---|---|---|
| MongoDB | Partidos finalizados y datos estáticos | Equipos y jugadores (Hito 4); documentos persistentes del partido (Hito 10) |
| Neo4j | Predicciones de usuarios | Estructura del fixture y relaciones entre partidos, equipos, estadios y eventos (Hito 5) |
| Cassandra | Logs de partidos | Comentarios masivos por partido y país (Hito 6) |
| Redis | Estado de partidos en vivo | Sesiones con TTL (Hito 7); prode y ranking en tiempo real son responsabilidades previstas |
| InfluxDB | Métricas y estadísticas históricas | Estadísticas de partido por ventana (Hito 8); series de actividad y jugadas |
| — | — | IRIS retirado; sus datos persistentes de partido pasan a MongoDB |

El criterio de fondo es el mismo: elegir la base por el patrón de acceso. Lo que cambió es el dato concreto de cada una. Las decisiones de distribución y consistencia del Hito 3 se reinterpretan abajo para el dato que cada base guarda hoy.

## Por qué no una sola base

Cada módulo tiene un patrón de acceso distinto, y forzarlos a una sola estructura vuelve caro justo lo que más se usa:

- Los comentarios en vivo son muchas escrituras pequeñas, concentradas después de un gol, que se leen por partido, país y ventana: Cassandra los particiona por patrón de acceso.
- Las sesiones, el prode y el ranking requieren acceso rápido a estado temporal: Redis; las puntuaciones que deban perdurar se guardan en MongoDB.
- Recorrer partido → equipos → estadio → jugadas son relaciones: en un grafo es seguir aristas; Neo4j conserva esa estructura del fixture.
- La actividad de la aplicación y las jugadas con fecha se consultan por ventana: InfluxDB almacena esas series temporales.
- Equipos, jugadores y registros detallados/históricos de partidos son documentos persistentes en MongoDB, con eventos embebidos y transición condicional del estado.

**El costo:** cinco productos para operar, cinco estrategias de respaldo y más superficie de monitoreo. La API los integra. Cada endpoint consulta una sola base, salvo crear comentario (Neo4j + Cassandra), y ningún pedido consulta todas las fuentes en serie.

## MongoDB: documentos persistentes

| Punto | Respuesta |
|---|---|
| Qué dato guarda | Fichas y planteles (`equipos`, `jugadores`), más documentos persistentes de partidos con eventos y estado |
| Qué acceso motivó la elección | Leer documentos completos y conservar historial que debe sobrevivir a la expiración de estado temporal |
| Modelo | Documental |
| Estructura implementada | `equipos`, `jugadores` y `partidos{codigo,equipo_local,equipo_visitante,fecha_hora,sede,estado,eventos}`; índice único por código del partido |
| Carga y recuperación | Documentos de partidos insertados solo si no existen para preservar el estado ya actualizado; consulta por `GET /partidos/{id}/detalle`; transición mediante actualización atómica condicionada por el estado previo. Los resultados del prode que deban perdurar también se guardarán aquí |
| Escala y distribución | Laboratorio: un nodo. **Propuesta:** réplica de 3 nodos; evaluar sharding solo si el volumen de registros históricos lo requiere |
| Consistencia necesaria | Fuerte para estado persistente y resultados consolidados; el detalle no debe perderse al expirar Redis |
| Si se cae | Los endpoints documentales y el detalle/estado del partido responden 503. Neo4j y las demás bases siguen funcionando |
| Costo que introduce | Validar e indexar la colección histórica; el estado temporal no debe duplicarse como autoridad en Redis |
| Evidencia | Exportador con operaciones y conexiones en el panel; p95 desde la API de 9,4 ms como máximo en la ventana de la demo ([series](../evidencia/dashboards/demo_20261030_223042_todo/series_prometheus.json)) |

## Neo4j: partidos, equipos, estadios y eventos

| Punto | Respuesta |
|---|---|
| Qué dato guarda | La estructura del fixture y sus relaciones: equipos, partidos, estadios y jugadas/eventos |
| Qué acceso motivó la elección | Recorrer relaciones del fixture sin duplicar la autoridad de los documentos persistentes de partido |
| Modelo | Grafo de propiedades |
| Estructura implementada | Nodos `Equipo`, `Partido`, `Estadio`, `Evento`; relaciones `PARTICIPA_EN`, `SE_JUEGA_EN`, `OCURRE_EN`. Restricciones de unicidad en los cuatro identificadores |
| Carga y recuperación | `MERGE` (repetible). `GET /partidos/{id}` y `/partidos/{id}/eventos`. El detalle persistente y el estado del partido se leen/escriben en MongoDB |
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
| Qué dato guarda | Sesiones con TTL y, como responsabilidad de tiempo real, prode y ranking |
| Qué acceso motivó la elección | Estado efímero de acceso, cálculos repetidos y consultas frecuentes de ranking; los resultados finales se persisten en MongoDB |
| Modelo | Clave-valor en memoria |
| Estructura implementada | Hash `f2030:sesion:{usuario}` con TTL de 1.800 s; `maxmemory 128mb` con política `volatile-lru`; persistencia `appendonly yes` |
| Carga y recuperación | Implementado: `GET /sesiones/{usuario}` lee el hash y `DELETE` lo invalida; Redis maneja el TTL. Prode/ranking son responsabilidades previstas, todavía sin endpoints |
| Escala y distribución | Laboratorio: un nodo. **Propuesta:** réplica de respaldo; particionar por usuario en Redis Cluster si el volumen de sesiones/ranking lo requiere |
| Consistencia necesaria | Leer la propia escritura: si cierro sesión, no puede seguir válida. La réplica asíncrona puede perder la última escritura al cambiar de nodo; el costo es que algunos usuarios vuelvan a iniciar sesión |
| Si se cae | `/sesiones` responde 503; comentarios, consultas de grafo y estadísticas siguen funcionando. Los resultados persistidos en MongoDB no dependen de Redis |
| Costo que introduce | Todo está en memoria: si se llena, expulsa sesiones con TTL. Por eso el panel muestra la memoria usada frente al límite |
| Evidencia | Prueba de falla y panel de memoria y comandos del exportador |

## InfluxDB: estadísticas de partido

| Punto | Respuesta |
|---|---|
| Qué dato guarda | Series temporales de actividad de la aplicación y jugadas; además, estadísticas con fecha por partido, equipo y fuente |
| Qué acceso motivó la elección | Consultar una ventana de tiempo acotada y agregarla (promedio, máximo) |
| Modelo | Series temporales |
| Estructura implementada | Base `fixture2030_metrics` (retención 90 días), tabla `estadisticas_partido` con tags `partido_id, equipo_id, sede, fuente, fase` y cinco campos numéricos |
| Carga y recuperación | Escritura en line protocol (reescribir el mismo instante no duplica). `GET /partidos/{id}/estadisticas` con ventana y agregación |
| Escala y distribución | Laboratorio: un nodo. **Propuesta (Hito 3):** réplica asíncrona entre nodos regionales; partición por partido y período |
| Consistencia necesaria | Eventual: un retraso breve en una estadística es aceptable si la ingesta no se frena |
| Si se cae | `/estadisticas` responde 503. Las mediciones que lleguen durante la caída se pierden si nadie las retiene: hace falta una cola delante (**propuesta**) |
| Costo que introduce | Un producto con su propio lenguaje de consulta; cada combinación de tags crea series, así que hay que cuidar no agregar tags de mucha variedad |
| Evidencia | 4.800 puntos sembrados; p95 desde la API de 9,1 ms como máximo en la ventana de la demo |

## Retiro de IRIS

Se eliminó IRIS del stack y sus dependencias. El detalle persistente del partido, sus eventos y la validación del cambio de estado pasan a documentos MongoDB; Neo4j mantiene las relaciones y recorridos del fixture. Las evidencias de fecha anterior conservan los resultados del diseño previo y no representan el estado actual.

## Preguntas transversales

**¿Qué datos son operacionales y cuáles podrían ir a una vista analítica?** Los cinco módulos son operacionales: atienden pedidos de usuarios. La actividad de comentarios por partido y minuto ya la proyectamos en el Data Mart del Hito 12, fuera del camino de la API. Las métricas de Prometheus también son analíticas, pero sobre la plataforma, no sobre el torneo.

**¿Dónde hay caché y cómo vence?** En Redis: las sesiones vencen por TTL (30 minutos de inactividad). La API no tiene otra caché hoy. La marca de "partido abierto a comentarios" es una propuesta.

**¿Cómo se evita que una consulta de alto volumen bloquee todo?**
- Cada endpoint toca una sola base, así que un problema en una base no frena a las otras. Lo vimos en la prueba de falla: con Redis caído, los comentarios siguieron devolviendo 201.
- La API tiene un tiempo máximo por pedido (504) y paginación con límite de 100 en las lecturas.
- El punto débil que encontramos es que los pedidos a una base caída esperan su timeout completo (ver [mejora transversal](limitaciones_y_evidencia.md#mejora-transversal-propuesta)).

**¿Qué haríamos si una base queda indisponible?** Seguir atendiendo lo que no depende de ella (la API ya lo hace), avisar con la alerta `BaseNoDisponible` y recuperar la base. Si es Neo4j, también se cortan los comentarios, y por eso proponemos desacoplar esa validación.

**¿Qué costo operativo agrega mantener cinco productos?** Cinco configuraciones, cinco estrategias de respaldo, cinco lenguajes de consulta y más superficie de seguridad. Lo compensamos con la API como punto único de entrada y métricas medidas desde la API para todas las bases.

**¿Qué parte de la escalabilidad está medida y qué parte es proyección?** Ver [limitaciones y evidencia](limitaciones_y_evidencia.md#medido-frente-a-proyectado).
