# Limitaciones y evidencia

Todo lo medido corrió en una notebook con Windows y Docker Desktop, con un nodo por base, el 30/10/2026 (hora de Argentina; en UTC ya era 31/10). La corrida que usamos como evidencia es la de 22:26 a 22:31, sobre el commit `c7eed72` con los cambios de este hito todavía sin commitear. Las cifras de este documento salen de los archivos de [`evidencia/`](../evidencia/README.md). Antes hubo dos corridas que explicamos en [corridas previas](../evidencia/corridas_previas/README.md): de la primera salió una corrección del monitoreo.

## Prueba controlada (RF10)

Se ejecutó `scripts/ejecutar_prueba_controlada.ps1 -Momento todo -PartidoEstado P-05`, con los tres momentos seguidos.

### 1. Pico de comentarios por país

| Dato | Valor |
|---|---|
| Comentarios enviados | 3.000 (750 por país: ARG, BRA, ESP, MAR), partido `P-01`, de 22:26:12 a 22:27:12 |
| Tasa | 50 por segundo objetivo; 50,01 real durante 59,99 s |
| Respuestas | 3.000 con 201, ninguna con error |
| Verificación en Cassandra | 4 particiones (una por país, todas en la misma ventana de media hora) leídas: 3.000 encontrados, 0 faltantes, 0 duplicados |
| Tiempo visto por el cliente | p50 11,85 ms, p95 13,93 ms, p99 20,91 ms, máximo 180,98 ms |
| Visto en Prometheus | unos 12,5 comentarios/s por país (ventana de 1 min); hasta 50,0 respuestas 201 por segundo; duración p95 de Cassandra de 85,3 ms como máximo |

Archivos: [resumen](../evidencia/resultados_sin_secretos/pico_comentarios_20261030_222612_resumen.json), [cada pedido](../evidencia/resultados_sin_secretos/pico_comentarios_20261030_222612.jsonl), captura de [comentarios por país](../evidencia/dashboards/demo_20261030_223042_todo/05_comentarios_por_pais.png).

Los percentiles del cliente los calculamos del campo `duracion_ms` de los 3.000 pedidos, por rango más cercano. Incluyen la red local entre la notebook y el contenedor.

### 2. Cambio de estado del partido en IRIS

`P-05`: `Programado → En juego` (200), `En juego → Finalizado` (200), y `Finalizado → En juego` rechazado con 409 y el mensaje "El partido 'P-05' no puede pasar de 'Finalizado' a 'En juego'". Archivo: [`estado_partido_20261030_222740.json`](../evidencia/estado_partido_20261030_222740.json).

### 3. Falla controlada de Redis

Con tráfico de fondo continuo (sesión, partido y comentario, en un bucle de un solo hilo), se detuvo el contenedor de Redis durante 91 s y se lo volvió a iniciar sin borrar su volumen. Antes de la prueba volvimos a sembrar las sesiones, porque vencen a los 30 minutos sin uso.

| Hora (Argentina) | Qué se observó |
|---|---|
| 22:27:40 | Empieza el tráfico de fondo |
| 22:28:10 | `/health` 200, sesión `U001` 200, sin alertas; acto seguido, `docker stop` de Redis |
| 22:28:26, a los 15 s | `/health` 503 con Redis "caída"; sesión 503. Alertas pendientes: `BaseNoDisponible{fuente="redis"}` y `DestinoCaido{job="redis"}` (el exportador tampoco llega a Redis) |
| 22:29:33, fin de la caída | `BaseNoDisponible` disparada; `ErroresServidorAltos` pendiente |
| 22:29:41 | `docker start` de Redis |
| 22:30:26, después | `/health` 200, sesión `U001` 200 (sobrevivió gracias a la persistencia en disco), sin alertas |

Tráfico de fondo durante toda la ventana:
- `GET /partidos`: 275 respuestas 200.
- Comentarios: 275 respuestas 201.
- `GET /sesiones`: 252 respuestas 200, 22 respuestas 503 y 1 respuesta 504 (ese pedido superó el tiempo máximo de la API).

Los comentarios y los partidos no se enteraron de la caída de Redis. La recolección de la API tardó como máximo 2,03 s y su destino siguió en UP toda la prueba.

Archivos: [`prueba_de_falla_20261030_223027.json`](../evidencia/prueba_de_falla_20261030_223027.json). Capturas:
- [Disponibilidad en el tiempo](../evidencia/dashboards/demo_20261030_223042_todo/15_disponibilidad_en_el_tiempo.png).
- [Errores por código](../evidencia/dashboards/demo_20261030_223042_todo/03_errores_por_codigo.png).
- [Duración por base](../evidencia/dashboards/demo_20261030_223042_todo/07_duracion_por_base.png).
- [Destinos UP](../evidencia/dashboards/demo_20261030_223042_todo/12_destinos_up.png).

## Corrección que salió de la primera corrida

En la primera prueba de falla, la disponibilidad de las bases se calculaba llamando al mismo servicio que `GET /health`, que espera a que respondan todas. Con Redis caído, cada recolección de la API tardó hasta 3,99 s, contra un límite de 4 s ([`recoleccion_api_falla_preliminar.json`](../evidencia/recoleccion_api_falla_preliminar.json)). En una máquina un poco más lenta, el destino de la API habría quedado DOWN justo durante la falla, y el panel se habría quedado sin datos cuando más se lo necesitaba.

Lo cambiamos: ahora el colector hace el ping a cada base en paralelo y espera como máximo 2 s; la que no contesta a tiempo cuenta como caída (test `test_disponibilidad_no_espera_a_una_base_colgada`). En la corrida final, la recolección de la API tardó como máximo 2,03 s durante la caída.

## Mejora transversal propuesta

**Lo que mostró la evidencia.** Mientras Redis estuvo caído, cada operación contra él tardó cerca de 5 s en fallar: el p95 de la duración de Redis vista desde la API llegó a 4,875 s. Por eso hubo solo 22 respuestas 503 (y un 504) en 91 s. El bucle de fondo quedaba esperando unos 5 s en cada vuelta, y `ErroresServidorAltos` no llegó a dispararse porque los errores eran pocos frente al resto del tráfico.

**Por qué importa a escala.** Por la ley de Little (pedidos en curso = tasa de llegada × tiempo de respuesta), si 1.000 pedidos por segundo tocan Redis y cada uno espera 5 s en lugar de 5 ms, se acumulan 5.000 pedidos en curso en lugar de 5. Los hilos y conexiones de la API se llenan esperando a una base que ya sabemos caída, y eso puede terminar frenando también a los endpoints que no usan Redis.

**Mejora propuesta (no implementada en el hito):**
1. **Fallar rápido:** si el último chequeo de disponibilidad marcó a una base como caída, la API responde 503 de inmediato durante unos segundos, sin intentar conectarse. Es el patrón de "disyuntor" (*circuit breaker*). La señal ya existe: es la que publica `fixture2030_dependencia_disponible`.
2. **Timeout por base:** 3 s es razonable para Cassandra o IRIS, pero excesivo para Redis, que responde en milisegundos (su p95 antes de la caída fue de 7,25 ms como máximo en la primera corrida, [series](../evidencia/corridas_previas/demo_20261030_2159_todo/series_prometheus.json)). Un timeout de unos 200 ms para Redis acotaría la espera.

**Costo:** el disyuntor puede rechazar pedidos unos segundos de más cuando la base ya volvió (falso positivo), y un timeout corto puede cortar operaciones lentas pero válidas. Se probaría repitiendo esta misma prueba de falla y comparando cuántos 503 por segundo se obtienen y cuánto tarda cada uno.

**Pendiente de explicar:** el timeout configurado en el Hito 10 es de 3 s, pero medimos cerca de 5 s por operación (y el ping aislado a `/sesiones` tardó 3,88 s). No sabemos de dónde sale la diferencia: puede ser la resolución del nombre `redis` en la red de Docker con el contenedor detenido, o que la conexión haga más de un intento. No lo investigamos.

## Métricas frente a los objetivos del TPO (RF11)

Los objetivos son los del Hito 3: entre 2 y 3 millones de usuarios simultáneos, más de 100.000 pedidos por segundo en picos, p95 menor a 100 ms en las consultas críticas y 99,99% de disponibilidad.

| Objetivo | Métrica que lo observa | Lo medido en el laboratorio | ¿Alcanza para afirmarlo? |
|---|---|---|---|
| Concurrencia (millones de usuarios) | pedidos en curso, sesiones activas | 16 hilos del generador; 3 sesiones sembradas | No. Es una proyección; ver la cuenta abajo |
| Throughput (más de 100.000 pedidos/s) | `rate(fixture2030_http_requests_total[1m])` | 50 comentarios/s por la API (la tasa que fijamos, sin buscar el límite). Hito 12: medianas de 6.793,6 y 11.390,0 escrituras/s directo a Cassandra, en un nodo | No. Mide un nodo de cada cosa |
| Latencia (p95 < 100 ms) | percentiles del histograma de la API y por base | p95 del cliente de 13,93 ms al crear comentarios; p95 de cada base por debajo de 90 ms | Sí para este volumen y este entorno, no a escala |
| Disponibilidad (99,99%) | `fixture2030_dependencia_disponible`, `up`, proporción de 5xx | Caída de Redis detectada en menos de 15 s; el resto de la API siguió funcionando | Muestra la detección y el aislamiento, no un porcentaje anual |
| Distribución | carga por partición o nodo | Un nodo por base: no hay distribución que medir | No. Es una propuesta (Hito 3) |
| Recuperación | línea de tiempo de disponibilidad | Redis volvió y la sesión `U001` se conservó; todo en 200 a los 45 s del `docker start` | Sí para la caída de un proceso; no para la pérdida de un nodo o de una región |

## Medido frente a proyectado

- **Medido:** todo lo que figura arriba con su archivo. Un nodo por base, una instancia de la API, datos sintéticos de laboratorio.
- **Proyectado:** con 3 millones de usuarios que refrescan una vez cada 30 s, serían unas 100.000 lecturas/s. Si el 5% comenta en los 30 s siguientes a un gol, unos 5.000 comentarios/s. Son cuentas con supuestos nuestros, no mediciones. El Hito 12 midió escrituras del mismo orden que ese pico, pero en un solo nodo, sin la API en el medio y sin réplicas. No se puede extrapolar en línea recta.
- **Objetivos de diseño:** los cuatro números del Hito 3.

## Limitaciones del monitoreo

- **Sin métricas internas de Cassandra, Neo4j, InfluxDB ni IRIS.** De esas cuatro solo vemos lo que ve la API: disponibilidad y duración. Faltan compactaciones de Cassandra, caché de páginas de Neo4j, cantidad de series de InfluxDB y procesos de IRIS. Cassandra necesitaría un agente JMX; Neo4j, la edición Enterprise; IRIS, habilitar su endpoint de métricas.
- **Sin CPU ni memoria por contenedor de las bases.** Solo tenemos el proceso de la API y la memoria de Redis. cAdvisor no funciona bien en Docker Desktop sobre WSL2 y no lo sumamos.
- **Una sola instancia de la API.** No se puede mostrar en la práctica que los histogramas se suman entre instancias, aunque las consultas están escritas para eso (`sum by (le, ...)`).
- **La disponibilidad se mide desde la API.** Si la API cae, las seis bases aparecen en 0 aunque estén bien. Por eso también miramos `up{job="api"}` y los exportadores, que miden por otro camino.
- **El p99 calculado desde el histograma se interpola dentro de cada rango.** En el pico, Prometheus marcó un p99 de hasta 0,242 s para crear comentarios, interpolado dentro del rango de 100 a 250 ms, mientras que el cliente midió 20,91 ms. Con poco tráfico en el minuto, unos pocos pedidos lentos lo empujan al borde del rango. Para afinarlo habría que agregar rangos entre 25 y 100 ms.
- **La primera recolección después de reiniciar la API** tarda más, porque los drivers abren sus conexiones en el primer uso. En la segunda corrida previa eso hizo que una recolección superara los 4 s y que las demás bases marcaran 375 ms durante un minuto.
- **Alertas sin notificación:** las reglas se evalúan y se ven en Prometheus, pero no avisan a nadie (no hay Alertmanager).
- **Datos sintéticos:** el contenido de los comentarios es repetitivo, el reparto entre países es parejo y hay un solo partido caliente. No reproduce la popularidad real entre partidos.

## Integridad de los datos funcionales (RNF5)

La instrumentación no escribe en las bases. Los únicos datos agregados son los de las pruebas, todos de laboratorio e identificables por su clave:
- 9.000 comentarios con claves `h13-<corrida>-<n>` (tres corridas de 3.000).
- 826 de tráfico de fondo con claves `h13-falla-...`.
- 40 de una prueba de humo.
- Los cambios de estado de `P-03`, `P-04` y `P-05`, que quedaron en "Finalizado".
