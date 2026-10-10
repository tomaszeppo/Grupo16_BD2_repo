# Ciclo de vida e invalidación — Caché de usuarios y sesiones (Hito 7)

## Sesiones

**Cuándo es válida:** mientras exista la clave `sesion:{id}` en Redis. No hay un campo "válida: true/false" que consultar — la propia existencia de la clave es la validez. Si `EXISTS sesion:{id}` da 0, la sesión no es válida, haya vencido por tiempo o haya sido cerrada explícitamente.

**Qué renueva la actividad:** cualquier acción del usuario ya logueado dispara un `EXPIRE sesion:{id} 1800` (y el mismo `EXPIRE` sobre el puntero `usuario:{id}:sesion_activa`), reiniciando la cuenta de 30 minutos desde cero. Es una ventana deslizante: mientras el usuario esté activo, nunca vence; si se queda quieto 30 minutos, se la lleva el TTL nativo de Redis.

**Por qué 30 minutos:** es un balance entre no obligar a un usuario activo a reloguearse en medio de un partido largo (con entretiempo incluido) y no mantener memoria reservada por usuarios que ya se fueron. Durante un partido, las acciones son frecuentes (consultar equipos, ver el ranking), así que la renovación constante mantiene viva la sesión de cualquiera que esté realmente mirando el partido.

**Por qué el TTL nativo y no un barrido manual:** la consigna lo pide explícitamente, y además tiene sentido para el volumen del Fixture 2030 — recorrer periódicamente millones de claves de sesión para buscar cuáles vencieron sería mucho más caro que dejar que Redis las expire solo, de forma perezosa y en segundo plano.

**Sesión inexistente:** la aplicación la trata como un usuario anónimo — no es un error, es el comportamiento esperado de una sesión vencida o nunca creada.

## Caché de catálogo (`cache:equipo:{codigo}`)

- **Fuente de verdad:** la colección `equipos` de MongoDB (Hito 4).
- **Cache hit:** `GET cache:equipo:{codigo}` devuelve algo distinto de `nil`. Se usa directo, sin tocar Mongo.
- **Cache miss:** `GET` devuelve `nil`. La aplicación busca en Mongo, arma el JSON, lo guarda con `SETEX cache:equipo:{codigo} 300 <json>` y recién ahí responde. El usuario nunca ve un error por un miss — como mucho, una respuesta un poco más lenta esa vez.
- **TTL:** 5 minutos. El catálogo de equipos cambia poco (según el Hito 1, prácticamente nada durante el torneo salvo alguna corrección puntual de ranking), así que 5 minutos es tiempo de sobra para absorber picos de lectura sin arriesgar mostrar un dato desactualizado por mucho tiempo.
- **Invalidación explícita:** si alguien corrige un equipo en Mongo (por ejemplo, un cambio de ranking), la aplicación hace `DEL cache:equipo:{codigo}` en el mismo momento del `UPDATE` en Mongo. No se espera a que venza el TTL — la consigna es clara en que un TTL solo no alcanza como estrategia de coherencia.
- **Si Redis no está disponible:** la aplicación cae directo a Mongo. Es más lento, pero sigue siendo correcto — Redis es una aceleración, nunca una dependencia obligatoria para que el dato exista.

## El ranking público: el problema que motivó este módulo

Ya lo habíamos visto venir desde el Hito 2: "demoras en la consolidación de la información impactan directamente en la confianza del usuario" — un usuario que ve un primer puesto que después cambia es exactamente ese problema.

**El escenario concreto:** apenas termina el último partido del torneo, se recalculan muchas predicciones casi en simultáneo. Es común que varios usuarios terminen con el mismo puntaje. Sin una regla de desempate resuelta de antemano, hay que decidir el orden en el momento — recorriendo y comparando usuarios empatados — y eso es lento justo cuando más gente está mirando la tabla.

**La regla de desempate** (ya la teníamos anotada de una conversación anterior sobre el módulo de predicciones): en caso de empate en puntos, gana quien cargó o actualizó sus pronósticos con más antelación respecto de cada partido, sumando la antelación de todas sus predicciones — no solo la última.

**Cómo se resuelve sin recalcular nada al leer:** el score del Sorted Set combina los dos criterios en un solo número:

```
score = puntos + (antelacion_total / 10_000_000)
```

La parte entera ordena por puntos (lo que realmente define quién ganó). La parte decimal, siempre menor a 1, ordena el desempate dentro del mismo puntaje — sin que la antelación de un usuario alcance jamás a mover el puntaje de otro a otro nivel. El divisor (10 millones) es una cota bien por encima de cualquier antelación acumulada real (en minutos, ni sumando todos los partidos del torneo varias veces se acerca a ese número), así que la parte decimal nunca se sale del rango (0, 1).

Se probó con este caso: tres usuarios con 300 puntos cada uno y distinta antelación acumulada (5000, 1200 y 8800 minutos), más un cuarto con 250 puntos y la mayor antelación de todos. El resultado de `ZREVRANGE`:

1. `user-00003` (300 puntos, 8800 de antelación) — el que más temprano cargó, con el mismo puntaje que los demás
2. `user-00001` (300 puntos, 5000 de antelación)
3. `user-00002` (300 puntos, 1200 de antelación)
4. `user-00004` (250 puntos, 9000 de antelación) — pese a tener la mayor antelación de todos, no le gana a nadie con más puntos

Exactamente el comportamiento buscado, y sin ningún paso de "reordenar" aparte: `ZREVRANGE` ya devuelve esto directo, en O(log N + M).

**Por qué la actualización es atómica:** sumar puntos y antelación al score de un usuario es una lectura, una suma y una escritura. Si la aplicación lo hiciera con comandos separados (leer el score, sumarle, escribirlo), dos actualizaciones del mismo usuario en paralelo podrían pisarse y perderse una. `ZINCRBY` suma el delta al score dentro de Redis, en un solo paso: el delta ya trae los dos criterios (`puntos + antelacion / 10_000_000`) y ninguna otra operación se intercala. Es el mismo principio que `INCRBY` para un contador. `queries` y la prueba `scripts/prueba_concurrencia.py` lo comprueban con varios procesos sobre el mismo usuario.

## Qué no llegamos a resolver

- El ranking privado (por grupos de amigos) usa el mismo patrón que el público, pero no se cargaron datos de ejemplo para esa variante en este hito.
- No se modeló qué pasa si la fuente de verdad de las predicciones (que todavía no existe como módulo propio — quedó pendiente desde el Hito 2) calcula un puntaje distinto al que tiene acumulado el hash de Redis por una falla previa. Habría que definir un proceso de reconciliación periódica, no solo el camino feliz de actualización incremental.

## Consistencia por tipo de dato (qué se sacrifica ante una partición)

Ante una partición de red no se pueden garantizar a la vez consistencia y disponibilidad. Para cada dato del módulo se elige qué propiedad se prioriza y cuál se sacrifica:

| Dato | Se prioriza | Se sacrifica | Impacto que se acepta |
| :--- | :--- | :--- | :--- |
| Sesiones | Disponibilidad | Consistencia inmediata | Un nodo aislado puede seguir aceptando y renovando sesiones. Un cierre de sesión puede tardar en verse del otro lado. Es preferible a impedir que los usuarios naveguen. |
| Caché de equipo y de partido | Disponibilidad | Consistencia inmediata | Se puede servir una copia levemente vieja hasta que venza su TTL o se invalide. La fuente de verdad sigue siendo MongoDB. |
| Contador de visitas | Disponibilidad | Consistencia inmediata | Los contadores de cada lado pueden diferir un rato. Un conteo apenas desactualizado no afecta a nadie. |
| Ranking público | Consistencia dentro de un nodo | Disponibilidad entre nodos | La actualización del score es atómica porque ocurre en un solo nodo; no hay estados intermedios visibles. Con una partición, un nodo sin acceso a quien lleva la escritura puede no aceptar actualizaciones del ranking antes que aceptar valores que luego haya que reconciliar. |

**Qué es este laboratorio y qué cambia con réplicas.** El ambiente es un único nodo de Redis, así que no hay partición posible entre nodos y la tabla describe el comportamiento esperado del diseño, no algo que se haya probado. Con réplicas, la replicación de Redis es asincrónica: una réplica puede ir atrasada respecto de quien lleva la escritura, y si este falla y se promueve una réplica, se pierden las escrituras que todavía no habían llegado. Eso es coherente con lo elegido para sesiones, caché y contadores (se acepta ver con atraso lo último que se escribió a cambio de seguir respondiendo). Para el ranking, donde sí importa no perder ni duplicar una actualización, la escritura seguiría yendo a un único nodo principal.
