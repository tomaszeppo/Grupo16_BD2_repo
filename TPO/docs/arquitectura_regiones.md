# Arquitectura por regiones

El Mundial 2030 se juega en tres continentes y los hinchas están en todo el mundo. Este documento explica cómo repartimos los datos entre regiones, qué priorizamos en cada caso y qué está armado en el laboratorio.

## El criterio

No usamos un único clúster geográfico para todo. Cada dato se reparte según lo que no puede fallar:

- **Lo que tiene que ser una sola verdad para todos** (el ranking, los pronósticos, los resultados) se escribe en **un único lugar** y cada región tiene **copias para leer**.
- **Lo masivo que tolera atraso** (comentarios, presencia, audiencia) se escribe y se lee **en la región de cada usuario**.

El ejemplo que decide el criterio es el ranking. Tiene que ser uno solo y actualizarse rápido en todo el mundo después de cada partido. Si lo partiéramos por región, la tabla global habría que armarla juntando pedazos de todas las regiones en cada consulta: nunca sería a la vez rápida y correcta. Con una sola tabla y copias de lectura, actualizarla es una sola escritura, y lo que tarda en verse en otra región es lo que tarda la réplica, que se puede medir.

## Qué se hace con cada dato

| Dato | Qué importa más | Cómo se reparte | Si se corta la comunicación entre regiones |
|---|---|---|---|
| Ranking | Una sola tabla, al día en todo el mundo | Se calcula una vez, en la región central: el puntaje en MongoDB y la tabla en Redis. Cada región tiene una réplica de Redis de solo lectura | La región aislada muestra la última tabla que recibió. Nunca se calculan dos tablas distintas |
| Pronósticos y resultados | No perder nada y respetar la hora de cierre | MongoDB con el primario en la región central y escritura confirmada por la mayoría | La región que no llega al primario rechaza el pronóstico (503). Preferimos un error a un pronóstico perdido o dudoso |
| Fixture y calendario | Leer rápido; cambia poco | Neo4j con una sola escritura (la administración) y una copia en memoria en cada proceso de la API | Se lee la última copia |
| Comentarios | Que no se corten nunca | Cassandra con un datacenter por región. Cada usuario escribe en el suyo y la copia llega a la otra región sin esperarla | Cada región sigue comentando sola; al volver, se ponen al día |
| Sesiones y presencia | Rapidez, cerca del usuario | Redis de cada región | Si una sesión se pierde, el usuario vuelve a entrar. La audiencia puede tener un hueco de algunos segundos |
| Audiencia y estadísticas | Volumen; la precisión es secundaria | Cada región cuenta lo suyo y lo manda por minuto a InfluxDB central | Se acumula y se manda al volver |

### Qué se sacrifica en cada caso

Ante una partición entre regiones no se puede tener a la vez consistencia y disponibilidad. Elegimos así:

- **Pronósticos y resultados: consistencia.** Una región aislada deja de aceptar pronósticos. El costo: los hinchas de esa región no pueden pronosticar mientras dure el corte. Lo aceptamos porque un pronóstico aceptado y después perdido, o aceptado fuera de hora, es peor que un error claro.
- **Ranking: consistencia en la escritura, disponibilidad en la lectura.** La tabla se calcula en un solo lugar. Una región aislada sigue mostrando la última tabla que recibió: puede estar atrasada, pero nunca contradice a otra región.
- **Comentarios, presencia y audiencia: disponibilidad.** Cada región sigue funcionando sola. El costo: durante el corte, un hincha de América no ve lo que se comenta en la tribuna de Europa, y la audiencia de esa región llega tarde al análisis.

## Qué está armado en el laboratorio

Todo corre en una sola máquina, así que la distancia entre regiones no es real: lo que se demuestra es la separación de los datos y que el sistema tolera la caída de una región, no la latencia.

- **Cassandra en dos datacenters**, `america` y `europa`, un nodo cada uno, con una copia completa en cada uno (`NetworkTopologyStrategy {'america': 1, 'europa': 1}`). Cada país pertenece a una región ([`app/dominio/regiones.py`](../app/dominio/regiones.py)): Sudamérica y Norteamérica van a `america`; el resto, como simplificación del laboratorio, a `europa`. La API escribe y lee con consistencia `LOCAL_ONE` en la región del usuario. Si su región no responde, atiende la otra, lo informa en la respuesta (`region_atendida`) y lo cuenta en la métrica `prode_cassandra_cambio_region_total`.
- **Redis con un primario y una réplica de lectura** (`redis_replica`), que hace de "la otra región". En el laboratorio las sesiones, la presencia y el chat usan el primario; la réplica queda lista para que el ranking se lea desde ahí (lo arma otro integrante del grupo, con `REDIS_REPLICA_URL`). Cuánto tarda en llegarle un cambio lo mide [`scripts/medir_replica_redis.py`](../scripts/medir_replica_redis.py).
- **MongoDB** queda como está: un conjunto de tres réplicas en la "región central".

Lo que no está armado: Redis de sesiones y presencia por región, InfluxDB por región con envío a la central, y la región africana como tercer datacenter de Cassandra.

### Demostración: se cae una región

```powershell
.\scripts\prueba_de_falla.ps1 europa -Brusco -Partido P-10
```

Durante un partido simulado con espectadores conectados, el script mata el nodo de Europa cerca del minuto 30 y lo levanta 30 segundos después. Mientras está caído, los hinchas europeos siguen comentando: la API los atiende desde América. Al volver, el nodo de Europa recibe lo que se escribió durante el corte. Al final, el script cuenta los comentarios del partido en cada región leyendo solo su propia copia, y deja el conteo en `evidencia/`. Los resultados están en [rendimiento.md](rendimiento.md#29-partido-en-vivo).

## Cómo sería en producción

Lo que cambia respecto del laboratorio:

1. **Una región por continente del torneo y de su público**: América, Europa y África como mínimo, con la central en una de ellas (la que concentre la operación del torneo).
2. **Cassandra**: un datacenter por región con tres nodos cada uno y replicación 3 por región (`LOCAL_QUORUM`), para que una región tolere la caída de un nodo sin cambiar de región.
3. **Redis**: un primario central para el ranking con réplicas de lectura en cada región, y un Redis propio por región para sesiones, presencia y chat (con su réplica local).
4. **MongoDB**: el conjunto de réplicas en la región central, con un secundario en cada región para lecturas que toleran atraso. Si el volumen de pronósticos lo exige, fragmentado por usuario.
5. **API**: varias instancias por región detrás de un balanceador; la conexión en vivo de cada hincha va a su región.
6. **InfluxDB**: uno por región que recibe la audiencia y las estadísticas de los partidos que se miran ahí, con un proceso que consolida por minuto en el central.

### Cuántas instancias hacen falta

La cuenta sale de lo medido en el laboratorio, no de estimaciones. La pieza que se satura primero en el partido en vivo es la CPU de la API, no las bases ([rendimiento.md](rendimiento.md#29-partido-en-vivo)). Por eso el dimensionamiento parte de cuántos espectadores sostiene una instancia de la API con su CPU antes de que la entrega de comentarios supere el segundo, y se escala de forma lineal agregando instancias. La cuenta con los números medidos está en [rendimiento.md](rendimiento.md#29-partido-en-vivo).

Esa extrapolación tiene un límite que conviene decir: en el laboratorio todas las piezas comparten la misma máquina. En producción, cada instancia tendría su CPU y las bases no competirían con la API por el procesador, así que la cuenta es una cota de lo que hace falta, no una medición del sistema distribuido.
