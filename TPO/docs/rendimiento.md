# Rendimiento: qué medimos, qué mejoramos y qué no podemos afirmar

Este documento tiene tres partes que no hay que mezclar: lo que **medimos** en el laboratorio, lo que **buscamos con el diseño** y lo que **proyectamos** para el volumen real del Mundial. Cada número de la primera parte sale de una corrida guardada en [`evidencia/`](../evidencia/README.md); al lado de cada tabla está el nombre del archivo.

## 1. Cómo medimos

- Todos los pedidos medidos pasan por la API. En el Hito 12 la carga iba directo a Cassandra y nos quedó marcado como límite; acá no.
- El generador de carga ([`carga/`](../carga/ejecutar.py)) simula usuarios que piden sin pausa durante 30 segundos. "50 a la vez" quiere decir 50 usuarios virtuales, cada uno mandando su siguiente pedido apenas recibe la respuesta del anterior.
- Antes de medir cargamos 100.000 usuarios y sus pronósticos directo en MongoDB ([`carga/poblar.py`](../carga/poblar.py)). Eso es preparación y no se mide.
- La latencia se informa sobre los pedidos que salieron bien; los errores se cuentan aparte.

**Entorno.** Una notebook con Windows 11 y Docker Desktop (12 núcleos y 7,6 GB asignados a Docker). Límites por contenedor: API con 1 CPU, 512 MB y 2 procesos; cada uno de los tres nodos de MongoDB con 1 CPU y 512 MB; Neo4j con 1 CPU y 1 GB. El generador corre en la misma máquina.

**Tres advertencias sobre estos números:**

1. Mientras medíamos estaban levantados también los contenedores de los Hitos 10 y 13 (Cassandra, IRIS, otro Neo4j, Grafana y demás), que compiten por memoria y CPU. Cada resumen lo dice en sus notas. Con la máquina libre los valores deberían mejorar, pero eso no lo medimos.
2. Hicimos una corrida por configuración. Entre dos corridas iguales vimos diferencias de hasta un 30 %, así que las comparaciones valen cuando la diferencia es grande, no por unos pocos puntos.
3. Las corridas dicen `"commit": "sin commit"` porque se hicieron antes de versionar la carpeta. Para dejarlas atadas a un commit hay que repetirlas con [`scripts/medir.ps1`](../scripts/medir.ps1).

### Un error nuestro que vale la pena contar

La primera versión del generador de carga estaba hecha con un solo proceso y se saturaba ella misma cerca de los 100 pedidos por segundo. Estábamos midiendo el límite del generador y no el de la API. Lo notamos porque, con la carga corriendo, ni la API ni MongoDB llegaban a su tope de CPU, y un cliente distinto obtuvo cuatro veces más pedidos por segundo contra la misma API. Reescribimos el generador con varios procesos e hilos, **descartamos todas las corridas hechas con el anterior** y volvimos a medir. Lo que sigue es todo posterior a ese arreglo.

## 2. Lo que medimos

### 2.1 Pico de pronósticos

Usuarios distintos cargando y corrigiendo el pronóstico de un mismo partido (`PUT /partidos/{id}/pronostico`). Cada pedido verifica que el usuario exista y escribe en MongoDB con confirmación de la mayoría de los nodos.

| Usuarios a la vez | Pedidos por segundo | p50 | p95 | p99 | Errores | Archivo |
|---|---|---|---|---|---|---|
| 10 | 154,3 | 75,8 ms | 100,9 ms | 120,0 ms | 0 | `pico_pronosticos_c10_registro_minimo_20261117_184544` |
| 50 | 164,5 | 299,0 ms | 414,9 ms | 507,1 ms | 0 | `pico_pronosticos_c50_registro_minimo_20261117_184617` |
| 200 | 151,7 | 1.300,2 ms | 1.803,9 ms | 2.209,3 ms | 0 | `pico_pronosticos_c200_registro_minimo_20261117_184649` |

Con esta configuración la API atiende unos 150 a 165 pronósticos por segundo y no pasa de ahí: al sumar usuarios no entran más pedidos, solo esperan más. No hubo errores ni con 200 a la vez.

### 2.2 Dónde está el cuello de botella

Para saber si el límite era la API o la base medimos MongoDB solo, sin la API, con el mismo tipo de escritura ([`carga/diagnostico_mongo.py`](../carga/diagnostico_mongo.py), 50 hilos):

| Garantía de escritura | Escrituras por segundo | p50 |
|---|---|---|
| Un nodo, sin esperar al diario | 1.530,1 | 24,9 ms |
| Un nodo, esperando al diario | 1.253,2 | 28,6 ms |
| Mayoría de los nodos (la que usa la API) | 992,8 | 41,1 ms |

Archivo: `diagnostico_mongo_20261117_182300`.

Dos conclusiones. La primera: MongoDB acepta cerca de 1.000 escrituras por segundo con la garantía que usamos y la API deja pasar unas 160, así que **el cuello de botella es la API**, no la base. Mirando el consumo de los contenedores durante una corrida (`docker stats`) vimos lo mismo: la API pegada a su tope de CPU y los nodos de MongoDB lejos del suyo; esa observación no quedó guardada en un archivo. La segunda: pedir confirmación de la mayoría cuesta alrededor de un tercio de las escrituras frente a confirmar con un solo nodo sin esperar al diario (992,8 contra 1.530,1). Lo pagamos a propósito: un pronóstico confirmado no se pierde aunque se caiga el primario (ver 2.8).

### 2.3 Dos mejoras, con su antes y su después

**Antes.** La primera tanda con el generador arreglado dio esto:

| Escenario | Usuarios a la vez | Pedidos por segundo | p95 | Errores | Archivo |
|---|---|---|---|---|---|
| Pronósticos | 50 | 99,2 | 805,8 ms | 0 | `pico_pronosticos_c50_20261117_183042` |
| Lecturas del fixture | 10 | 44,8 | 878,9 ms | 0 | `lecturas_fixture_c10_20261117_183149` |
| Lecturas del fixture | 50 | 37,8 | 3.908,1 ms | 6 (504) | `lecturas_fixture_c50_20261117_183225` |
| Pronósticos y lecturas | 50 | 88,1 | 1.086,4 ms | 0 | `pico_mixto_20261117_183333` |

**Mejora 1: el listado del fixture sale de la copia del calendario.** El desglose por ruta mostró que `GET /partidos` (72 partidos con sus equipos y estadios) era el pedido más lento: 2.392 ms de mediana con 50 usuarios, contra unos 700 ms de los demás. La API ya guardaba una copia del calendario en memoria para validar pronósticos, así que hicimos que el listado saliera de ahí. Con solo ese cambio las lecturas con 10 usuarios pasaron de 44,8 a 73,8 por segundo (`lecturas_fixture_c10_listado_desde_la_copia_20261117_183540`).

**Mejora 2: el registro anota solo problemas.** La API escribía una línea por cada pedido y otra por cada operación contra una base. Comparando con y sin esas líneas vimos que costaban cerca de la mitad del rendimiento. Ahora por defecto se anotan solo los pedidos con error y las operaciones que fallan; el detalle completo se activa con `LOG_NIVEL=DEBUG`. La duración de cada operación no se pierde: queda en las métricas.

**Después**, con las dos mejoras:

| Escenario | Usuarios a la vez | Pedidos por segundo | p95 | Errores | Archivo |
|---|---|---|---|---|---|
| Pronósticos | 50 | 164,5 | 414,9 ms | 0 | `pico_pronosticos_c50_registro_minimo_20261117_184617` |
| Lecturas del fixture | 10 | 164,2 | 99,9 ms | 0 | `lecturas_fixture_c10_registro_minimo_20261117_184722` |
| Lecturas del fixture | 50 | 143,8 | 514,5 ms | 0 | `lecturas_fixture_c50_registro_minimo_20261117_184755` |
| Lecturas del fixture | 200 | 102,0 | 2.991,3 ms | 0 | `lecturas_fixture_c200_registro_minimo_20261117_184827` |
| Pronósticos y lecturas | 50 | 157,6 | 480,9 ms | 0 | `pico_mixto_registro_minimo_20261117_184900` |

El listado del fixture, que tardaba 2.392 ms de mediana con 50 usuarios, quedó en 211,9 ms. Y desaparecieron los errores 504 de las lecturas.

En la corrida mixta, pronósticos (MongoDB) y lecturas (Neo4j) conviven sin errores: las lecturas tuvieron una mediana de unos 300 ms y los pronósticos de 313,6 ms. Las dos comparten el límite de la API, no se frenan entre sí por las bases.

### 2.4 Darle más recursos a la API

Como el límite era la API, le dimos 4 CPU y 4 procesos, sin tocar las bases:

| Escenario | Usuarios a la vez | Pedidos por segundo | p95 | Errores | Archivo |
|---|---|---|---|---|---|
| Pronósticos | 50 | 494,6 | 187,3 ms | 0 | `pico_pronosticos_c50_api_4cpu_4procesos_20261117_184959` |
| Pronósticos | 200 | 581,9 | 540,2 ms | 0 | `pico_pronosticos_c200_api_4cpu_4procesos_20261117_185032` |
| Lecturas del fixture | 50 | 692,0 | 113,8 ms | 0 | `lecturas_fixture_c50_api_4cpu_4procesos_20261117_185104` |
| Lecturas del fixture | 200 | 693,4 | 381,2 ms | 0 | `lecturas_fixture_c200_api_4cpu_4procesos_20261117_185137` |

Los pronósticos pasaron de unos 160 a entre 495 y 582 por segundo, y las lecturas de 144 a 692. La API no guarda estado propio (salvo la copia del calendario, que cada proceso renueva solo), así que crece sumando procesos. Con 4 procesos los pronósticos ya se acercan a lo que MongoDB mostró en la prueba directa: el siguiente límite sería la base.

### 2.5 Cierre de un partido

Al cerrar un partido la API responde enseguida y la puntuación corre aparte. Medimos cuánto tarda hasta quedar completa:

| Pronósticos del partido | Total | Puntuar | Sumar a los puntajes | Guardar el ranking | Archivo |
|---|---|---|---|---|---|
| 20.000 | 8,4 s | 1,8 s | 4,0 s | 0,06 s | `cierre_partido_20000_pronosticos_20261117_185226` |
| 100.000 | 25,9 s | 8,4 s | 17,3 s | 0,01 s | `cierre_partido_100000_pronosticos_20261117_185238` |

Con cinco veces más pronósticos tardó unas tres veces más: el tiempo acompaña a la cantidad de pronósticos **de ese partido**, no al total acumulado del torneo.

En las dos corridas repetimos el cierre con el mismo marcador y el ranking quedó igual. Después corrimos el control que recalcula todos los puntajes desde cero ([`scripts/recalcular_puntajes.py`](../scripts/recalcular_puntajes.py)): sobre 120.001 pronósticos puntuados de 100.001 usuarios, sin diferencias (`recalculo_puntajes_20261117_191922.txt`).

### 2.6 Saber el puesto de un usuario en el ranking

Con los puntajes reales de 100.000 usuarios:

| Consulta | Usuarios a la vez | p50 | p95 | Errores | Archivo |
|---|---|---|---|---|---|
| Primeros 100 (`GET /ranking`) | 10 | 8,3 ms | 90,9 ms | 0 | `posicion_ranking_c10_100000_usuarios_20261117_185321` |
| Puesto de un usuario (`GET /ranking/usuarios/{id}`) | 10 | 304,4 ms | 690,3 ms | 0 | mismo archivo |
| Puesto de un usuario | 50 | 1.795,3 ms | 5.512,5 ms | 80 de 603 (504) | `posicion_ranking_c50_100000_usuarios_20261117_185354` |

Los primeros 100 salen recorriendo un índice y cortando: 8 ms. El puesto de un usuario obliga a contar cuántos tienen mejor puntaje que él, y con 100.000 usuarios ya tarda 300 ms; con 50 pedidos a la vez empieza a fallar. Este es el dato con el que justificamos que el ranking en vivo vaya a Redis: en un conjunto ordenado el puesto se obtiene directo, sin contar. MongoDB queda como fuente de verdad y como respaldo.

### 2.7 Validar el pronóstico con y sin la copia del calendario

Para aceptar un pronóstico hay que saber si el partido existe, si tiene equipos y si no empezó. Eso lo gobierna Neo4j. Medimos las dos formas, con 50 usuarios a la vez:

| Forma | Pedidos por segundo | p95 | Archivo |
|---|---|---|---|
| Consultando Neo4j en cada pronóstico | 91,7 | 795,0 ms | `pico_pronosticos_c50_sin_copia_del_calendario_20261117_185445` |
| Con la copia en memoria (30 s) | 199,5 | 335,7 ms | `pico_pronosticos_c50_con_copia_del_calendario_20261117_185535` |

La copia duplica largamente los pronósticos por segundo y, sobre todo, saca a Neo4j del camino: si se cae, se sigue pronosticando (2.8). El costo es que un cambio en un partido puede tardar hasta 30 segundos en verse en todos los procesos de la API; cómo lo cubrimos está en [decisiones.md](decisiones.md#la-copia-del-calendario).

### 2.8 Fallas controladas durante la carga

Las tres pruebas corren pronósticos con 20 usuarios a la vez durante 75 a 90 segundos y, en el medio, tiran un contenedor. Se repiten con [`scripts/prueba_de_falla.ps1`](../scripts/prueba_de_falla.ps1).

| Qué se cayó | Cómo | Pedidos | Errores | Archivo |
|---|---|---|---|---|
| Primario de MongoDB | Apagado con orden | 16.475 | 0 | `caida_primario_de_mongodb_20261117_185620` |
| Primario de MongoDB | Corte brusco | 14.522 | 60 (503) | `caida_primario_de_mongodb_corte_brusco_20261117_185830` |
| Neo4j | Corte brusco | 9.301 | 0 | `caida_neo4j_corte_brusco_20261117_190440` |

- **Primario apagado con orden.** MongoDB traspasó el mando a otro nodo antes de salir y el cliente repitió solo las escrituras que estaban en vuelo. Ni un error.
- **Primario cortado de golpe.** Los otros dos nodos tardaron en darse por enterados y elegir un nuevo primario. En la línea de tiempo se ve el corte: errores 503 entre el segundo 33 y el 39, y pedidos normales otra vez desde el segundo 43. Fueron unos 10 segundos sin poder escribir y 60 pedidos rechazados sobre 14.522 (0,41 %). Lo que ya estaba confirmado no se perdió, porque se había escrito en la mayoría. Cuando el nodo caído volvió, retomó como primario sin errores.
- **Neo4j cortado de golpe.** Los pronósticos siguieron con la copia del calendario: 0 errores. Bajó el ritmo (124 por segundo en toda la corrida) y hubo pedidos sueltos de hasta 9 segundos, que son los que intentaron renovar la copia. Durante la caída comprobamos a mano que el listado del fixture seguía respondiendo desde la copia, que el detalle de un partido devolvía 503 y que `/health/dependencias` informaba a Neo4j caído; eso no queda en el archivo de la corrida.

**La primera vez esta última prueba salió mal**, y sirvió. Con Neo4j caído aparecieron errores en los pronósticos, que justamente no dependen de Neo4j. La causa: cuando un pedido intentaba renovar la copia del calendario, todos los demás se quedaban esperándolo. Lo corregimos (mientras uno renueva, el resto sigue con la copia; y si Neo4j ya se sabe caído, los reintentos van aparte), agregamos dos pruebas automáticas que reproducen el caso y repetimos la medición, que es la de la tabla. Los archivos de aquella primera corrida no se conservaron, por eso no damos sus cifras.

## 3. Objetivos de diseño (no son mediciones)

- Que el pico de pronósticos antes de un partido dependa de una sola base. Hoy cada pronóstico hace dos operaciones en MongoDB y ninguna en Neo4j.
- Que cerrar un partido cueste según los pronósticos de ese partido y se pueda repetir sin duplicar puntos.
- Que un pronóstico confirmado sobreviva a la caída de un nodo.
- Que la caída de Neo4j no impida pronosticar.
- Que la API crezca sumando procesos, sin estado compartido entre ellos.

## 4. Proyección al Mundial (no medido)

El enunciado habla de 3 millones de usuarios simultáneos. **Nada de esta sección fue medido.** El laboratorio es una notebook con 100.000 usuarios, y de ahí no se puede deducir cómo se comporta un despliegue real. Lo que sí podemos decir es qué cambiaríamos y por qué.

- **La API.** Es lo primero que se satura y lo más fácil de escalar: más procesos detrás de un balanceador. Lo único que cada proceso guarda es su copia del calendario.
- **MongoDB.** Un conjunto de réplicas tiene un solo primario que recibe todas las escrituras; para repartirlas hay que fragmentar. Fragmentaríamos `pronosticos` y `puntajes` por usuario (clave *hashed*): cargar un pronóstico, ver mis pronósticos y leer mi puntaje irían a un solo fragmento. La puntuación de un partido, en cambio, tendría que recorrer todos, porque los pronósticos de un partido quedan repartidos; es un trabajo que corre una vez por partido y se puede hacer fragmento por fragmento.
- **El ranking.** Con 100.000 usuarios ya se ve que MongoDB no sirve para decir el puesto de alguien en el momento. Con millones, menos. Por eso pasa a Redis.
- **Neo4j.** El fixture son 104 partidos y casi no cambia; con la copia en memoria, Neo4j recibe sobre todo las consultas de jugadas. Usamos la edición comunitaria, que no arma clúster: en producción haría falta la edición empresarial para tener réplicas de lectura, o aceptar que el detalle de jugadas tiene un único punto de falla.
- **Cierre de partido.** Si se mantuviera la relación que medimos, puntuar 3 millones de pronósticos de un partido llevaría varios minutos. No sabemos si se mantiene. En cualquier caso el ranking ya está pensado para tolerarlo: mientras corre la suma, algunos usuarios ven el partido aplicado y otros todavía no.

## 5. Cómo repetir todo

Desde la carpeta `TPO`, con el entorno levantado:

```powershell
.\scripts\medir.ps1                          # toda la serie (borra los datos de laboratorio al empezar)
.\scripts\prueba_de_falla.ps1 primario
.\scripts\prueba_de_falla.ps1 primario -Brusco
.\scripts\prueba_de_falla.ps1 neo4j -Brusco
```

Para comparar con lo de este documento conviene apagar antes los contenedores de los otros hitos.
