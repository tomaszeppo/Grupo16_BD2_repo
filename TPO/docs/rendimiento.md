# Rendimiento: qué medimos, qué mejoramos y qué no podemos afirmar

Este documento tiene tres partes que no hay que mezclar: lo que **medimos** en el laboratorio, lo que **buscamos con el diseño** y lo que **proyectamos** para el volumen real del Mundial. Cada número de la primera parte sale de una corrida guardada en [`evidencia/`](../evidencia/README.md); al lado de cada tabla está el nombre del archivo.

## 1. Cómo medimos

- Todos los pedidos medidos pasan por la API. En el Hito 12 la carga iba directo a Cassandra y nos quedó marcado como límite; acá no.
- El generador de carga ([`carga/`](../carga/ejecutar.py)) simula usuarios que piden sin pausa durante 30 segundos. "50 a la vez" quiere decir 50 usuarios virtuales, cada uno mandando su siguiente pedido apenas recibe la respuesta del anterior. Cada usuario virtual usa la sesión de un usuario distinto, creada antes de medir.
- Antes de medir cargamos 100.000 usuarios y sus pronósticos directo en MongoDB ([`carga/poblar.py`](../carga/poblar.py)), y una sesión por usuario directo en Redis ([`carga/sesiones.py`](../carga/sesiones.py)). Eso es preparación y no se mide.
- La latencia se informa sobre los pedidos que salieron bien; los errores se cuentan aparte.

**Entorno.** Una notebook con Windows 11 y Docker Desktop (12 núcleos y 7,6 GB asignados a Docker). Límites por contenedor: API con 1 CPU, 512 MB y 2 procesos; cada uno de los tres nodos de MongoDB con 1 CPU y 512 MB; Neo4j con 1 CPU y 1 GB; cada nodo de Cassandra con 0,75 CPU y 900 MB; Redis con 0,5 CPU y 256 MB. El generador corre en la misma máquina.

**Las corridas.** Todas las de este documento se hicieron el 20/11/2026 con [`scripts/medir.ps1`](../scripts/medir.ps1) y [`scripts/prueba_de_falla.ps1`](../scripts/prueba_de_falla.ps1), sobre el commit `9b8f940` (cada resumen lo dice en `"commit"`), sin otros contenedores pesados levantados. La sección 2.3 cuenta además dos mejoras con corridas del 17/11, que están en [`evidencia/anterior/`](../evidencia/anterior/).

**Dos advertencias sobre estos números:**

1. Hicimos una corrida por configuración. Entre dos corridas iguales vimos diferencias de hasta un 30 %, así que las comparaciones valen cuando la diferencia es grande, no por unos pocos puntos.
2. Todo comparte la misma máquina: la API, las bases y el generador compiten por el procesador. Los números dicen cómo se comporta esta configuración, no cuánto rendiría cada pieza sola.

### Un error nuestro que vale la pena contar

La primera versión del generador de carga estaba hecha con un solo proceso y se saturaba ella misma cerca de los 100 pedidos por segundo. Estábamos midiendo el límite del generador y no el de la API. Lo notamos porque, con la carga corriendo, ni la API ni MongoDB llegaban a su tope de CPU, y un cliente distinto obtuvo cuatro veces más pedidos por segundo contra la misma API. Reescribimos el generador con varios procesos e hilos, **descartamos todas las corridas hechas con el anterior** y volvimos a medir. Lo que sigue es todo posterior a ese arreglo.

## 2. Lo que medimos

### 2.1 Pico de pronósticos

Usuarios distintos cargando y corrigiendo el pronóstico de un mismo partido (`PUT /partidos/{id}/pronostico`). Cada pedido valida la sesión en Redis y escribe en MongoDB con confirmación de la mayoría de los nodos.

| Usuarios a la vez | Pedidos por segundo | p50 | p95 | p99 | Errores | Archivo |
|---|---|---|---|---|---|---|
| 10 | 232,3 | 36,9 ms | 84,3 ms | 105,1 ms | 0 | `pico_pronosticos_c10_20261120_022443` |
| 50 | 227,7 | 208,1 ms | 310,3 ms | 390,7 ms | 0 | `pico_pronosticos_c50_20261120_022517` |
| 200 | 218,4 | 903,8 ms | 1.083,2 ms | 1.351,6 ms | 0 | `pico_pronosticos_c200_20261120_022550` |

Con esta configuración la API atiende unos 220 a 230 pronósticos por segundo y no pasa de ahí: al sumar usuarios no entran más pedidos, solo esperan más. No hubo errores ni con 200 a la vez.

El 17/11 la misma prueba dio entre 150 y 165 por segundo. Entre una corrida y otra cambiaron dos cosas: ahora la máquina estaba libre (aquella vez estaban levantados los contenedores de los Hitos 10 y 13) y el usuario se valida con la sesión en Redis en lugar de buscarlo en MongoDB. No medimos cuánto aporta cada una, así que no atribuimos la diferencia a ninguna.

### 2.2 Dónde está el cuello de botella

Para saber si el límite era la API o la base medimos MongoDB solo, sin la API, con el mismo tipo de escritura ([`carga/diagnostico_mongo.py`](../carga/diagnostico_mongo.py), 50 hilos):

| Garantía de escritura | Escrituras por segundo | p50 |
|---|---|---|
| Un nodo, sin esperar al diario | 1.184,9 | 30,0 ms |
| Un nodo, esperando al diario | 880,7 | 65,1 ms |
| Mayoría de los nodos (la que usa la API) | 855,0 | 69,3 ms |

Archivo: `diagnostico_mongo_20261120_023043`.

Dos conclusiones. La primera: MongoDB acepta unas 850 escrituras por segundo con la garantía que usamos y la API deja pasar unas 230, así que **el cuello de botella es la API**, no la base (la sección 2.4 lo confirma: dándole más CPU a la API, sube). La segunda: pedir confirmación de la mayoría cuesta alrededor de un cuarto de las escrituras frente a confirmar con un solo nodo sin esperar al diario (855,0 contra 1.184,9). Lo pagamos a propósito: un pronóstico confirmado no se pierde aunque se caiga el primario (ver 2.8).

### 2.3 Dos mejoras, con su antes y su después

Esta parte se midió el 17/11, con los contenedores de los Hitos 10 y 13 levantados en la misma máquina; los archivos están en [`evidencia/anterior/`](../evidencia/anterior/). La conservamos porque muestra de dónde salieron dos decisiones que siguen en el código.

**Antes:**

| Escenario | Usuarios a la vez | Pedidos por segundo | p95 | Errores | Archivo |
|---|---|---|---|---|---|
| Pronósticos | 50 | 99,2 | 805,8 ms | 0 | `anterior/pico_pronosticos_c50_20261117_183042` |
| Lecturas del fixture | 10 | 44,8 | 878,9 ms | 0 | `anterior/lecturas_fixture_c10_20261117_183149` |
| Lecturas del fixture | 50 | 37,8 | 3.908,1 ms | 6 (504) | `anterior/lecturas_fixture_c50_20261117_183225` |
| Pronósticos y lecturas | 50 | 88,1 | 1.086,4 ms | 0 | `anterior/pico_mixto_20261117_183333` |

**Mejora 1: el listado del fixture sale de la copia del calendario.** El desglose por ruta mostró que `GET /partidos` (72 partidos con sus equipos y estadios) era el pedido más lento: 2.392 ms de mediana con 50 usuarios, contra unos 700 ms de los demás. La API ya guardaba una copia del calendario en memoria para validar pronósticos, así que hicimos que el listado saliera de ahí. Con solo ese cambio las lecturas con 10 usuarios pasaron de 44,8 a 73,8 por segundo (`anterior/lecturas_fixture_c10_listado_desde_la_copia_20261117_183540`).

**Mejora 2: el registro anota solo problemas.** La API escribía una línea por cada pedido y otra por cada operación contra una base. Comparando con y sin esas líneas vimos que costaban cerca de la mitad del rendimiento. Ahora por defecto se anotan solo los pedidos con error y las operaciones que fallan; el detalle completo se activa con `LOG_NIVEL=DEBUG`. La duración de cada operación no se pierde: queda en las métricas.

**Después**, con las dos mejoras, el 17/11:

| Escenario | Usuarios a la vez | Pedidos por segundo | p95 | Errores | Archivo |
|---|---|---|---|---|---|
| Pronósticos | 50 | 164,5 | 414,9 ms | 0 | `anterior/pico_pronosticos_c50_registro_minimo_20261117_184617` |
| Lecturas del fixture | 10 | 164,2 | 99,9 ms | 0 | `anterior/lecturas_fixture_c10_registro_minimo_20261117_184722` |
| Lecturas del fixture | 50 | 143,8 | 514,5 ms | 0 | `anterior/lecturas_fixture_c50_registro_minimo_20261117_184755` |
| Pronósticos y lecturas | 50 | 157,6 | 480,9 ms | 0 | `anterior/pico_mixto_registro_minimo_20261117_184900` |

**Hoy**, el 20/11, con la máquina libre:

| Escenario | Usuarios a la vez | Pedidos por segundo | p95 | Errores | Archivo |
|---|---|---|---|---|---|
| Lecturas del fixture | 10 | 197,2 | 95,5 ms | 0 | `lecturas_fixture_c10_20261120_022623` |
| Lecturas del fixture | 50 | 206,8 | 368,4 ms | 0 | `lecturas_fixture_c50_20261120_022655` |
| Lecturas del fixture | 200 | 205,3 | 1.194,8 ms | 0 | `lecturas_fixture_c200_20261120_022728` |
| Pronósticos y lecturas | 50 | 207,3 | 315,8 ms | 0 | `pico_mixto_20261120_022800` |

El listado del fixture, que antes de la mejora 1 tardaba 2.392 ms de mediana con 50 usuarios, hoy tarda 173,8 ms. En la corrida mixta, pronósticos (MongoDB) y lecturas (Neo4j) conviven sin errores, con medianas parecidas (230,6 ms los pronósticos, entre 123,5 y 257,0 ms las lecturas): comparten el límite de la API y no se frenan entre sí por las bases.

### 2.4 Darle más recursos a la API

Como el límite era la API, le dimos 4 CPU y 4 procesos, sin tocar las bases:

| Escenario | Usuarios a la vez | Pedidos por segundo | p95 | Errores | Archivo |
|---|---|---|---|---|---|
| Pronósticos | 50 | 655,2 | 125,1 ms | 0 | `pico_pronosticos_c50_api_4cpu_4procesos_20261120_023207` |
| Pronósticos | 200 | 813,2 | 362,7 ms | 0 | `pico_pronosticos_c200_api_4cpu_4procesos_20261120_023312` |
| Lecturas del fixture | 50 | 754,9 | 106,8 ms | 0 | `lecturas_fixture_c50_api_4cpu_4procesos_20261120_023240` |
| Lecturas del fixture | 200 | 699,3 | 399,1 ms | 0 | `lecturas_fixture_c200_api_4cpu_4procesos_20261120_023346` |

Los pronósticos pasaron de unos 230 a entre 655 y 813 por segundo, y las lecturas de unos 205 a entre 700 y 755. La API no guarda estado propio que tenga que compartir (las sesiones están en Redis; la copia del calendario la renueva cada proceso solo), así que crece sumando procesos. Con 4 procesos los pronósticos ya se acercan a lo que MongoDB mostró en la prueba directa: el siguiente límite sería la base.

### 2.5 Cierre de un partido

Al cerrar un partido la API responde enseguida (21 a 24 ms) y la puntuación corre aparte. Medimos cuánto tarda hasta quedar completa:

| Pronósticos del partido | Total | Puntuar | Sumar a los puntajes | Guardar el ranking | Archivo |
|---|---|---|---|---|---|
| 20.000 | 9,7 s | 2,4 s | 6,8 s | 0,05 s | `cierre_partido_20000_pronosticos_20261120_022833` |
| 100.000 | 45,0 s | 12,2 s | 32,2 s | 0,01 s | `cierre_partido_100000_pronosticos_20261120_022846` |

Con cinco veces más pronósticos tardó unas 4,6 veces más: el tiempo acompaña a la cantidad de pronósticos **de ese partido**, no al total acumulado del torneo. El 17/11 la relación había sido de tres veces; con una sola corrida por volumen no sabemos cuál es la representativa.

En las dos corridas repetimos el cierre con el mismo marcador y el ranking quedó igual. Después corrimos el control que recalcula todos los puntajes desde cero ([`scripts/recalcular_puntajes.py`](../scripts/recalcular_puntajes.py)): sobre 120.000 pronósticos puntuados de 100.000 usuarios, sin diferencias (`recalculo_puntajes_20261120_022935.txt`).

### 2.6 Saber el puesto de un usuario en el ranking

Con los puntajes reales de 100.000 usuarios:

| Consulta | Usuarios a la vez | p50 | p95 | Errores | Archivo |
|---|---|---|---|---|---|
| Primeros 100 (`GET /ranking`) | 10 | 7,7 ms | 90,0 ms | 0 | `posicion_ranking_c10_20261120_022937` |
| Puesto de un usuario (`GET /ranking/usuarios/{id}`) | 10 | 310,7 ms | 696,6 ms | 0 | mismo archivo |
| Puesto de un usuario | 50 | 1.896,5 ms | 5.787,0 ms | 70 de 591 (504) | `posicion_ranking_c50_20261120_023009` |

Los primeros 100 salen recorriendo un índice y cortando: 8 ms. El puesto de un usuario obliga a contar cuántos tienen mejor puntaje que él, y con 100.000 usuarios ya tarda 300 ms; con 50 pedidos a la vez empieza a fallar. Este es el dato con el que justificamos que el ranking en vivo vaya a Redis: en un conjunto ordenado el puesto se obtiene directo, sin contar. MongoDB queda como fuente de verdad y como respaldo.

### 2.7 Validar el pronóstico con y sin la copia del calendario

Para aceptar un pronóstico hay que saber si el partido existe, si tiene equipos y si no empezó. Eso lo gobierna Neo4j. Medimos las dos formas, con 50 usuarios a la vez:

| Forma | Pedidos por segundo | p95 | Archivo |
|---|---|---|---|
| Consultando Neo4j en cada pronóstico | 115,7 | 594,5 ms | `pico_pronosticos_sin_copia_del_calendario_20261120_023122` |
| Con la copia en memoria (30 s) | 227,7 | 310,3 ms | `pico_pronosticos_c50_20261120_022517` |

La copia casi duplica los pronósticos por segundo y, sobre todo, saca a Neo4j del camino: si se cae, se sigue pronosticando (2.8). El costo es que un cambio en un partido puede tardar hasta 30 segundos en verse en todos los procesos de la API; cómo lo cubrimos está en [decisiones.md](decisiones.md#la-copia-del-calendario).

### 2.8 Fallas controladas durante la carga

Las tres pruebas corren pronósticos con 20 usuarios a la vez durante 90 segundos y, cerca del segundo 30, tiran un contenedor que vuelven a levantar 30 segundos después. Se repiten con [`scripts/prueba_de_falla.ps1`](../scripts/prueba_de_falla.ps1).

| Qué se cayó | Cómo | Pedidos | Errores | Archivo |
|---|---|---|---|---|
| Primario de MongoDB (`mongo1`) | Apagado con orden | 17.183 | 60 (503) | `caida_primario_20261120_024011` |
| Primario de MongoDB (`mongo3`) | Corte brusco | 19.831 | 0 | `caida_primario_corte_brusco_20261120_024147` |
| Neo4j | Corte brusco | 19.499 | 0 | `caida_neo4j_corte_brusco_20261120_024320` |

- **Primario apagado con orden.** Al apagarse no hubo ningún error: MongoDB traspasó el mando a otro nodo antes de salir y el cliente repitió solo las escrituras que estaban en vuelo. Los 60 errores llegaron después, entre los segundos 77 y 84, cuando el nodo ya había vuelto (se lo levantó cerca del segundo 64): en esos segundos todos los pedidos fallaron con 503. No investigamos la causa; es compatible con una nueva elección al reincorporarse el nodo, pero eso no lo verificamos. El 17/11 la misma prueba no había tenido errores en la vuelta (`anterior/caida_primario_de_mongodb_20261117_185620`).
- **Primario cortado de golpe.** Esta vez, ningún error: los pedidos siguieron sin pausa durante el corte. El 17/11, con otro nodo como primario, el corte había dejado unos 10 segundos sin poder escribir y 60 pedidos rechazados sobre 14.522 (`anterior/caida_primario_de_mongodb_corte_brusco_20261117_185830`). Con una corrida de cada lado no podemos decir cuál es el comportamiento típico; lo que sí se mantuvo en las dos es que lo ya confirmado no se perdió, porque se había escrito en la mayoría.
- **Neo4j cortado de golpe.** Los pronósticos siguieron con la copia del calendario: 0 errores y el mismo ritmo durante el corte. Hubo pedidos sueltos de hasta 8,7 segundos; por lo que vimos en la primera corrida (abajo), son los que intentan renovar la copia mientras Neo4j no responde.

**La primera vez esta última prueba salió mal**, y sirvió. Con Neo4j caído aparecieron errores en los pronósticos, que justamente no dependen de Neo4j. La causa: cuando un pedido intentaba renovar la copia del calendario, todos los demás se quedaban esperándolo. Lo corregimos (mientras uno renueva, el resto sigue con la copia; y si Neo4j ya se sabe caído, los reintentos van aparte), agregamos dos pruebas automáticas que reproducen el caso y repetimos la medición. Los archivos de aquella primera corrida no se conservaron, por eso no damos sus cifras.

### 2.9 Partido en vivo

El escenario `vivo` ([`carga/vivo.py`](../carga/vivo.py)) abre una conexión en vivo por espectador, cada uno un usuario distinto que mira desde su país, inicia la simulación (tipo `carga`) y sigue el partido hasta el final. Un 5 % de los espectadores comenta: poco durante el juego y mucho en los segundos que siguen a un gol. Un cuarto de ellos se va a mitad del partido y vuelve unos segundos después. La demora de entrega es la de cada espectador con su propio comentario: desde que lo manda hasta que le llega por su conexión, pasando por Cassandra y por el reparto de Redis entre los procesos de la API.

| Espectadores | Conexiones fallidas | Audiencia que contó la API | Comentarios publicados | Con error | Entrega p50 | Entrega p95 | Entrega p99 | Archivo |
|---|---|---|---|---|---|---|---|---|
| 500 | 0 | 500 | 95 | 0 | 19,6 ms | 87,6 ms | 136,2 ms | `vivo_500_espectadores_20261120_023425` |
| 1.000 | 0 | 1.000 | 218 | 0 | 89,2 ms | 654,6 ms | 849,0 ms | `vivo_1000_espectadores_20261120_023606` |
| 2.000 | 368 | 2.000 | 388 | 0 | 2.039,3 ms | 7.671,0 ms | 9.707,5 ms | `vivo_2000_espectadores_20261120_023751` |

Los comentarios frenados por el modo lento (un comentario cada 5 segundos por usuario) se cuentan aparte en cada resumen y no son errores. En las tres corridas la simulación terminó completa y la audiencia contada coincidió con los espectadores conectados.

- **Hasta 1.000 espectadores** la entrega queda por debajo del segundo en el p99.
- **Con 2.000** la API se satura: la entrega pasa de los 7 segundos en el p95 y 368 intentos de conexión fallan (los espectadores reintentan y terminan entrando: la audiencia llegó a 2.000). Mirando `docker stats` durante corridas de prueba previas a las de la tabla (no quedaron guardadas en un archivo): con 2.000 espectadores la API estaba al 100 % de su CPU, y con 1.000, Redis usaba menos del 1 % de la suya. No registramos Redis ni Cassandra con 2.000. Con lo que vimos, **el cuello de botella es la CPU de la API**, como en los pronósticos.

**Atraso de la réplica de Redis.** Es lo que tardaría la tabla del ranking en llegar a "la otra región". Sobre 1.000 escrituras en el primario, la réplica tuvo el dato con una mediana de 0,39 ms, p95 0,95 ms, p99 1,11 ms y un máximo de 45,5 ms; ninguna dejó de llegar (`replica_redis_20261120_023954`). Dos aclaraciones: el script busca el dato cada milisegundo, así que por debajo de 1 ms no distingue; y primario y réplica están en la misma máquina, sin la distancia real entre regiones.

**Se cae una región de Cassandra durante un partido.** Con 500 espectadores, se mató el nodo de Europa cerca del minuto 30 y se lo levantó 30 segundos después (`vivo_cassandra_europa_corte_brusco_20261120_024453`). La simulación terminó completa y la audiencia llegó a 500. De 340 comentarios enviados, 218 se publicaron, 111 los frenó el modo lento, 10 llegaron con el partido ya terminado y 1 no tuvo respuesta de la API (el cliente se cansó de esperar a los 10 segundos). La entrega fue de 23,1 ms de mediana y 208,9 ms en el p95. Al terminar, el script contó los comentarios del partido en cada región, leyendo solo su propia copia: **las dos regiones tienen exactamente los mismos comentarios**, país por país (`cassandra_europa_corte_brusco_20261119_234657_conteo_por_region.txt`; el nombre usa la hora local de la máquina). El conteo muestra dos ventanas de media hora por país porque ese partido ya tenía comentarios de una corrida anterior que se había cortado; en las dos ventanas las regiones coinciden.

**Redis caído durante un partido.** Lo probamos a mano, sin archivo de corrida: con Redis detenido 20 segundos a mitad de una simulación, el partido terminó completo y quedó marcado `audiencia_incompleta`, como está previsto. La prueba automática que cubre el caso es `test_redis_caido_a_mitad_del_partido_no_corta_la_simulacion`.

#### Cuántas instancias de la API harían falta

Con lo medido, una instancia de la API con 1 CPU y 2 procesos sostiene **1.000 espectadores** con la entrega por debajo del segundo, y no 2.000. Para los 3 millones de usuarios simultáneos del enunciado, si todos estuvieran mirando un partido a la vez:

3.000.000 espectadores ÷ 1.000 por instancia = **3.000 instancias de 1 CPU**.

Es una cota, no una predicción, por tres razones. No medimos instancias con más CPU en este escenario (en pronósticos y lecturas, 4 CPU rindieron entre 2,9 y 3,7 veces lo de 1). En el laboratorio las bases y el generador le quitan procesador a la API. Y el código de la conexión en vivo no está optimizado: cada mensaje se convierte a texto una vez por espectador. Lo que sí muestra la cuenta es dónde está el costo: en atender conexiones abiertas, que crece sumando instancias porque la API no comparte estado entre ellas más allá de Redis.

## 3. Objetivos de diseño (no son mediciones)

- Que el pico de pronósticos antes de un partido dependa de una sola base. Hoy cada pronóstico hace dos operaciones en MongoDB y una en Redis (la sesión), y ninguna en Neo4j.
- Que cerrar un partido cueste según los pronósticos de ese partido y se pueda repetir sin duplicar puntos.
- Que un pronóstico confirmado sobreviva a la caída de un nodo.
- Que la caída de Neo4j no impida pronosticar.
- Que la caída de una región no corte los comentarios.
- Que la API crezca sumando procesos, sin estado compartido entre ellos fuera de Redis.

## 4. Proyección al Mundial (no medido)

El enunciado habla de 3 millones de usuarios simultáneos. **Nada de esta sección fue medido.** El laboratorio es una notebook con 100.000 usuarios, y de ahí no se puede deducir cómo se comporta un despliegue real. Lo que sí podemos decir es qué cambiaríamos y por qué. El reparto entre regiones está en [arquitectura por regiones](arquitectura_regiones.md).

- **La API.** Es lo primero que se satura, tanto en los pronósticos como en el partido en vivo, y lo más fácil de escalar: más procesos detrás de un balanceador. La cuenta con lo medido está en 2.9.
- **MongoDB.** Un conjunto de réplicas tiene un solo primario que recibe todas las escrituras; para repartirlas hay que fragmentar. Fragmentaríamos `pronosticos` y `puntajes` por usuario (clave *hashed*): cargar un pronóstico, ver mis pronósticos y leer mi puntaje irían a un solo fragmento. La puntuación de un partido, en cambio, tendría que recorrer todos, porque los pronósticos de un partido quedan repartidos; es un trabajo que corre una vez por partido y se puede hacer fragmento por fragmento.
- **El ranking.** Con 100.000 usuarios ya se ve que MongoDB no sirve para decir el puesto de alguien en el momento. Con millones, menos. Por eso pasa a Redis.
- **Neo4j.** El fixture son 104 partidos y casi no cambia; con la copia en memoria, Neo4j recibe sobre todo las consultas de jugadas. Usamos la edición comunitaria, que no arma clúster: en producción haría falta la edición empresarial para tener réplicas de lectura, o aceptar que el detalle de jugadas tiene un único punto de falla.
- **Cierre de partido.** Si se mantuviera la relación que medimos, puntuar 3 millones de pronósticos de un partido llevaría varios minutos. No sabemos si se mantiene. En cualquier caso el ranking ya está pensado para tolerarlo: mientras corre la suma, algunos usuarios ven el partido aplicado y otros todavía no.

## 5. Cómo repetir todo

Desde la carpeta `TPO`, con el entorno levantado y sin otros contenedores pesados corriendo:

```powershell
.\scripts\medir.ps1                          # toda la serie, incluido el partido en vivo y la réplica de Redis
.\scripts\prueba_de_falla.ps1 primario
.\scripts\prueba_de_falla.ps1 primario -Brusco
.\scripts\prueba_de_falla.ps1 neo4j -Brusco
.\scripts\prueba_de_falla.ps1 europa -Brusco -Partido P-10
```

`medir.ps1` borra los datos de laboratorio al empezar. Cada corrida deja su resumen en `evidencia/` con el commit en el que se hizo.
