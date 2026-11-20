# Prode Mundial 2030 — proyecto final

Aplicación de prode para el Mundial 2030: los usuarios pronostican cada partido, suman puntos y compiten en un ranking general y en prodes privados con amigos.

Esta carpeta es independiente de los hitos: se levanta sola y no usa nada de las otras carpetas del repositorio.

## Qué hay construido

| Parte | Base | Estado |
|---|---|---|
| Usuarios, prodes, pronósticos, puntuación, ranking | MongoDB (tres nodos) | Construido |
| Fixture, partidos, jugadas y sus cadenas | Neo4j | Construido |
| Sesiones, presencia en los partidos en vivo, reparto de comentarios | Redis (primario y réplica) | Construido |
| Ranking en vivo y puntuación por lotes | Redis | Construido |
| Comentarios por partido y país | Cassandra (dos regiones) | Construido |
| Estadísticas de la simulación, audiencia y comentarios por minuto | InfluxDB | Construido |
| Monitoreo | Prometheus y Grafana | Construido |
| API y interfaz de demostración | — | Construido |

IRIS no forma parte del proyecto final: [por qué](docs/por_que_no_iris.md).

Cómo se reparten los datos entre regiones y qué se prioriza en cada caso: [arquitectura por regiones](docs/arquitectura_regiones.md).

## Documentación

- [Decisiones sobre las bases](docs/decisiones.md): qué guarda cada una, por qué, qué pasa si falla y qué cuesta.
- [Arquitectura por regiones](docs/arquitectura_regiones.md): qué se escribe en un solo lugar, qué en cada región y qué se sacrifica.
- [Rendimiento](docs/rendimiento.md): qué medimos, qué mejoramos y qué no podemos afirmar.
- [Modelo de datos](docs/modelo_de_datos.md)
- [La API](docs/api.md)
- [Cómo sumar una base](docs/como_sumar_una_base.md): cómo está organizada la API y dónde vive cada base.
- [Por qué IRIS no entra](docs/por_que_no_iris.md)
- [Evidencia de las mediciones](evidencia/README.md)

## Levantar el entorno

Hace falta Docker Desktop. Todos los comandos se corren desde esta carpeta (`TPO`), en PowerShell.

```powershell
.\scripts\levantar.ps1
```

La primera vez crea el archivo `.env` y se detiene: hay que completar ahí `MONGO_PASSWORD`, `NEO4J_PASSWORD` (8 caracteres o más), `ADMIN_CLAVE`, `REDIS_PASSWORD` y `GRAFANA_PASSWORD` con valores propios, y volver a correr el script. El archivo `.env` no se versiona.

Levanta tres nodos de MongoDB, Neo4j, Redis y su réplica, Cassandra en dos regiones, InfluxDB, la API, Prometheus y Grafana. Todo junto ocupa unos 3,7 GB de memoria en reposo (medido con `docker stats`); si hay contenedores de los hitos levantados, conviene detenerlos. Cuando termina:

- Interfaz de demostración: http://127.0.0.1:8010/demo/
- Contrato de la API: http://127.0.0.1:8010/docs
- Estado de las bases: http://127.0.0.1:8010/health/dependencias
- Tablero de Grafana: http://127.0.0.1:3001 (se ve sin ingresar; para editar, usuario `admin` y la `GRAFANA_PASSWORD`)

Después, cargar los datos de laboratorio:

```powershell
docker compose run --rm herramientas python -m seed.run --dias-hasta-inicio 3
```

Carga 48 equipos, sus planteles y los 104 partidos, con el primer partido sin jugar ubicado a tres días de hoy. Se puede repetir: no duplica nada. Para comprobarlo:

```powershell
docker compose run --rm herramientas python -m seed.run --verificar
```

Puertos en el equipo: 8010 (API), 27217 a 27219 (MongoDB), 7475 y 7688 (Neo4j), 6380 y 6381 (Redis y su réplica), 9043 y 9044 (Cassandra América y Europa), 9091 (Prometheus) y 3001 (Grafana). InfluxDB no publica puerto al equipo. Si alguno está ocupado, cambiarlo en `.env`; los hitos pueden usar algunos de los mismos puertos.

## Recorrer la demostración

### El partido en vivo, con dos hinchas de países distintos

1. Abrir http://127.0.0.1:8010/demo/ en dos navegadores distintos (o uno normal y una ventana privada: cada uno guarda su propia sesión). En uno crear un usuario de Argentina; en el otro, uno de España.
2. Los dos entran al mismo partido programado (por ejemplo, desde **Fixture**). La página abre la conexión en vivo: el bloque **Audiencia** muestra cuántos están mirando, en total y desde su país.
3. En un tercer navegador (o en el de uno de ellos, después), entrar a **Administración** con la `ADMIN_CLAVE` y tocar **Iniciar simulación** en ese partido. Cada segundo real es un minuto de partido.
4. Cada uno comenta y ve, al instante, la tribuna de su país. La pestaña **Todos los países** muestra las dos. Comentar dos veces seguidas muestra el modo lento.
5. La curva de audiencia se dibuja minuto a minuto. Al terminar, el bloque muestra el análisis: pico, promedio, minutos vistos, espectadores únicos y tiempo medio, con los goles marcados sobre la curva.
6. En Grafana se ven las conexiones abiertas, los comentarios por segundo, la demora de entrega y la audiencia por país.

Para mostrar que se cae una región sin que se corten los comentarios: `.\scripts\prueba_de_falla.ps1 europa -Brusco -Partido P-10` (ver [arquitectura por regiones](docs/arquitectura_regiones.md#demostración-se-cae-una-región)).

### El prode

1. Abrir http://127.0.0.1:8010/demo/ y crear un usuario.
2. En **Fixture**, entrar a un partido programado y cargar un pronóstico.
3. Entrar al primer partido (ya jugado) y tocar "¿De dónde vino?" en un gol: muestra la cadena de jugadas recorrida en Neo4j.
4. En **Administración** (pide la `ADMIN_CLAVE` del `.env`): elegir el partido pronosticado, ponerlo en juego, cargar un par de jugadas y cerrarlo. Se ve la puntuación paso por paso.
5. En **Ranking**, ver el puesto del usuario.

Al ingresar con la clave de administración, la aplicación también inicia el usuario reutilizable «Administrador de prueba» y prepara su «Grupo X» con cinco compañeros sintéticos. Desde Mis prodes se puede consultar el código para invitar a otros usuarios o crear y unirse a otros grupos. La identidad de laboratorio y la clave compartida no constituyen autenticación real. En un partido finalizado, el botón «Ver rankings» abre el ranking general o el de cualquiera de los grupos del usuario. Ambos muestran puntos acumulados de todos los partidos puntuados; mientras se está puntuando, la tabla puede cambiar.

Para pronosticar, entrar en **Fixture**, elegir un partido programado y usar **Tu pronóstico** debajo del marcador. Hay que guardarlo antes de iniciar el partido. En el cierre, el resultado se calcula para todos los pronósticos válidos, incluido el del administrador; la vista vuelve a consultar el pronóstico durante el minuto posterior al final mientras se persiste la puntuación.
6. En **Mis prodes**, crear uno, compartir el código y ver su tabla.

Cada bloque de la pantalla tiene una etiqueta con la base que respondió.

Para empezar de cero entre un ensayo y otro (borra usuarios, pronósticos y resultados del laboratorio):

```powershell
docker compose run --rm herramientas python -m seed.run --reiniciar --dias-hasta-inicio 3
```

## Pruebas

Las unitarias no necesitan bases. Hace falta Python 3.12:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest tests/unit -q
```

Las de integración corren contra las bases reales, dentro de Docker:

```powershell
docker compose run --rm -e PERMITIR_REINICIO=1 herramientas python -m pytest tests/integration -q
```

En MongoDB usan una base aparte y en Redis la base 1; no tocan los datos del laboratorio. En Neo4j no se puede (la edición comunitaria tiene una sola base), así que **borran el grafo**; por eso piden `PERMITIR_REINICIO=1`. Después hay que volver a cargar los datos con `seed.run --reiniciar`.

## Mediciones y pruebas de falla

```powershell
.\scripts\medir.ps1                              # toda la serie de carga; borra los datos de laboratorio al empezar
.\scripts\prueba_de_falla.ps1 primario           # apaga con orden el primario de MongoDB durante una carga
.\scripts\prueba_de_falla.ps1 primario -Brusco   # lo corta de golpe
.\scripts\prueba_de_falla.ps1 neo4j -Brusco      # corta Neo4j
.\scripts\prueba_de_falla.ps1 europa -Brusco -Partido P-10   # corta la región Europa de Cassandra durante un partido en vivo
docker compose run --rm herramientas python -m carga.ejecutar vivo --espectadores 1000 --partido P-07   # partido en vivo con espectadores
docker compose run --rm herramientas python -m scripts.medir_replica_redis   # atraso de la réplica de Redis
```

Cada corrida deja su resultado en [`evidencia/`](evidencia/README.md). Las pruebas de falla detienen un contenedor de este proyecto y lo vuelven a levantar; no borran datos. Los resultados y cómo leerlos están en [docs/rendimiento.md](docs/rendimiento.md).

Para ver el detalle de cada pedido en el registro de la API: poner `LOG_NIVEL=DEBUG` en `.env` y correr `docker compose up -d api`. Por defecto se anotan solo los problemas.

## Mirar las bases directamente

```powershell
# MongoDB (pide la contraseña del .env)
docker compose exec mongo1 mongosh -u admin -p --authenticationDatabase admin prode2030

# Neo4j (pide la contraseña del .env); también en http://127.0.0.1:7475
docker compose exec neo4j cypher-shell -u neo4j

# Redis (toma la contraseña del contenedor)
docker compose exec redis redis-cli
#   KEYS audiencia:*            quién está mirando cada partido, por país
#   ZRANGE audiencia:P-07:ARG 0 -1 WITHSCORES

# Cassandra: cada región por separado
docker compose exec cassandra_america cqlsh
docker compose exec cassandra_europa cqlsh
#   SELECT * FROM fixture2030.comentarios_por_partido_pais WHERE partido_id='P-07' ALLOW FILTERING;

# InfluxDB
docker compose exec influxdb influxdb3 query --database fixture2030_metrics "SELECT * FROM audiencia_partido LIMIT 10"
```

Desde fuera de Docker (Compass, por ejemplo) se puede entrar a un nodo de MongoDB con conexión directa: `mongodb://admin:<contraseña>@127.0.0.1:27217/?directConnection=true&authSource=admin`. No se puede usar la dirección del conjunto de réplicas completo, porque los nodos se anuncian con sus nombres internos de Docker.

## Detener

```powershell
.\scripts\limpiar.ps1                # detiene los contenedores y conserva los datos
.\scripts\limpiar.ps1 -BorrarDatos   # además borra los volúmenes de este proyecto
```

## Si algo no anda

- **La interfaz dice que una base no responde.** Mirar http://127.0.0.1:8010/health/dependencias y `docker compose ps`. Recién levantado, Neo4j tarda un rato en quedar listo; `docker compose ps` lo muestra como `healthy` cuando está.
- **"Falta el encabezado X-Admin-Clave o no es correcto".** La clave es la `ADMIN_CLAVE` del `.env`. Si se cambió, hay que correr `docker compose up -d api`.
- **Un puerto está ocupado.** Cambiarlo en `.env` (están listados en `.env.example`).
- **El fixture muestra un partido con el estado viejo.** El listado sale de una copia que se renueva cada 30 segundos; el detalle del partido está siempre al día.
- **La interfaz manda a "Entrá al Prode" al abrir una página.** La sesión venció (dura 24 horas desde el último uso) o se reinició Redis sin sus datos: volver a entrar.
- **"Modo lento: esperá unos segundos".** Cada usuario puede comentar una vez cada 5 segundos (`CHAT_SEGUNDOS_ENTRE_COMENTARIOS`).
- **No se puede simular un partido que ya se simuló.** Volver a cargar los datos con `seed.run --reiniciar`, que también borra el estado de las simulaciones.

## Estructura

```
TPO/
├── app/          la API: rutas, servicios, adaptadores (uno por base) y puertos
├── seed/         datos de laboratorio y carga en las dos bases
├── carga/        generador de carga y escenarios de medición
├── scripts/      levantar, limpiar, medir, pruebas de falla y control de puntajes
├── ui/           interfaz de demostración
├── tests/        pruebas unitarias y de integración
├── docs/         documentación
├── evidencia/    resultados de las mediciones
├── monitoreo/    configuración de Prometheus y el tablero de Grafana
├── cassandra/    esquema de Cassandra (dos regiones)
└── mongo/        arranque del conjunto de réplicas
```


## Puntuación y ranking con Redis

1. Al iniciar un partido, un hilo prepara en Redis, por lotes, un hash con los pronósticos guardados en MongoDB. El inicio no espera a que termine esa copia. Si la preparación falla, se vuelve a intentar al cerrar. La copia se refresca al cierre para detectar pronósticos que otros procesos hayan aceptado después del inicio real; esos pronósticos se anulan.
2. Al finalizar, se aplican las reglas de `app/dominio/puntuacion.py`: 3 puntos por marcador exacto, 1 por acertar ganador o empate, y 0 en caso contrario o si se cargó después del inicio real. El proceso recorre los pronósticos por lotes y una operación Lua actualiza de manera atómica el puntaje acumulado, el sorted set y el registro de aplicación de cada usuario. Repetir un lote no suma dos veces.
3. El ranking se consulta desde Redis por puntaje, cantidad de exactos, anticipación acumulada y, ante igualdad, ID de usuario ascendente. `GET /ranking`, `GET /ranking/usuarios/{id}` y las tablas de prodes leen Redis; los nombres también se copian allí. Mientras se procesa, la tabla puede mostrar resultados parciales; `GET /partidos/{id}/puntuacion` informa el estado.
4. Después de una espera configurable (15 segundos por defecto) se vuelcan los resultados a `pronosticos` y `puntajes` de MongoDB por lotes idempotentes; se guarda la foto histórica y se marca el proceso completo. Solo entonces se eliminan los hashes temporales del partido. Si se pierde Redis, se reconstruye el ranking desde MongoDB y se puede reintentar el cierre. Para una puntuación que quedó en curso, la reserva se puede recuperar tras su vencimiento; un administrador debe repetir el pedido de cierre. No hay recuperación automática al reiniciar.

Compose activa Redis con contraseña, AOF (`everysec`), sin expulsión automática, con volumen persistente y una réplica de lectura. Es el mismo Redis de las sesiones y del partido en vivo. Esto reduce, pero no elimina, la posibilidad de perder escrituras recientes ante una falla. La implementación escribe en el primario y asume que no hay partidos puntuándose simultáneamente; no es Redis Cluster y la réplica no toma el lugar del primario si se cae. El límite local por defecto de 256 MB protege la máquina y no está dimensionado para millones de usuarios: hay que medir memoria, carga, duración y dimensionar infraestructura antes de esa escala. Los IDs existentes admiten siete dígitos.

Se pueden ajustar `REDIS_ENABLED`, `REDIS_MEMORIA`, `REDIS_CPUS`, `REDIS_LOTE` y `REDIS_PERSISTENCIA_DEMORA_SEGUNDOS` en `.env`. Con `REDIS_ENABLED=false` se conserva la puntuación y el ranking anteriores en MongoDB (las sesiones y el partido en vivo siguen usando Redis). Para ejecutar pruebas aisladas sobre Mongo y Redis reales: `docker compose exec -T -e RUN_REDIS_INTEGRATION=1 api python -m pytest tests/redis_integration -q -p no:cacheprovider`. Las pruebas exigen que la DB 15 de Redis esté vacía y crean una base Mongo de prueba de nombre único.

### Simular pronósticos y lecturas por la API

Con el entorno levantado y desde `TPO`, ejecutar con Python y las dependencias instaladas:

```powershell
python -m carga.simulacion_api --partido P-19 --usuarios 100 --concurrencia 2 --lectores 2 --intervalo 1
```

Elegir un partido programado de laboratorio: la prueba crea usuarios y pronósticos persistentes, ejecuta la simulación completa y finaliza ese partido. No borra datos. Registra las respuestas y latencias de preparación, consultas concurrentes del ranking y comprobación de los puntos de cada usuario. Deja JSONL y un resumen en `evidencia/`. La preparación y las lecturas pasan por HTTP; los datos son sintéticos. Los lectores hacen una consulta cada `--intervalo` segundos, por lo que no equivalen a usuarios en concurrencia máxima. Empezar con valores bajos y medir el consumo antes de subirlos; el generador comparte máquina con la API.

## Estadísticas de la simulación (InfluxDB)

Las simulaciones nuevas registran cada jugada en `jugadas_partido` con categoría, jugador y timestamp; además escriben posesión por jugador y minuto. La API agrega las acciones por jugador y selección desde las jugadas y calcula la posesión a partir de los segundos atribuidos a cada equipo. Las simulaciones anteriores conservan su lectura histórica. La precisión de pases se calcula dividiendo pases completados por intentados. Los datos son sintéticos y no representan mediciones reales del partido.

Al pulsar «Iniciar simulación», el generador utiliza HTTP contra la propia API: prepara y reutiliza 25 hinchas sintéticos por país (los cuatro fijos y los de quienes ya estén mirando), registrados en MongoDB; cada uno abre su sesión como un usuario real. Ingresa pronósticos para algunos hinchas argentinos antes del inicio. Si el partido ya no admite pronósticos, omite esos intentos. Luego inicia el partido con `/estado`, publica cada comentario mediante el mismo `POST /partidos/{id}/comentarios` que utiliza la pantalla (con su sesión y su `comentario_id`; los hinchas comentan por turno para no chocar con el modo lento), envía cada minuto a `POST /administracion/simulaciones/{id}/muestras` —que guarda la muestra, cierra la audiencia del minuto y avisa el estado a quienes miran—, cierra con `/resultado` y solicita el archivo en Neo4j. La preparación del guion, los planteles y los metadatos internos todavía accede a las bases desde el proceso servidor. La creación de usuarios y comentarios es persistente. El generador utiliza por defecto `http://127.0.0.1:8010`; se puede configurar con `SIMULADOR_API_URL` en el entorno del proceso de la API.

Por defecto se generan 4 comentarios por país y segundo (1.440 en total con cuatro países), además de una muestra por segundo. Se puede ajustar `SIMULADOR_COMENTARIOS_POR_REGION_SEGUNDO` entre 1 y 10; con más de 4, cada hincha comenta más seguido que el modo lento y parte de los comentarios se rechaza con 429. Los comentarios llegan a la pantalla por la conexión en vivo; la tribuna muestra los últimos 40 y el resto queda en Cassandra para el historial. Un comentario o un minuto que falla no corta el partido: queda marcado (`comentarios_incompletos`, `audiencia_incompleta`). Recorrer la API permite observar esas operaciones en sus métricas, pero por sí solo no demuestra cuántos espectadores concurrentes soporta. Para medir lecturas adicionales se usa el escenario `vista_partido` descrito más abajo.

La pantalla consulta `GET /partidos/{id}/estadisticas`; los totales individuales están en `GET /partidos/{id}/estadisticas/jugadores` y las jugadas en `GET /partidos/{id}/jugadas/temporales`. Al finalizar, se validan las muestras, el guion y el marcador antes de archivar resúmenes de jugadores, equipos y minutos en Neo4j. Ante una falla, el archivo queda pendiente. Detalle y limitaciones en [estadísticas por jugador](docs/diseno_estadisticas_jugador.md).

Compose inicia InfluxDB 3 con una base local, sin vencimiento de datos y límites configurables. En este laboratorio no publica el puerto ni usa autenticación; no usar esa configuración en un entorno compartido.

## Audiencia y comentarios por minuto (InfluxDB)

Mientras alguien tiene un partido abierto en la interfaz, su conexión en vivo cuenta como un espectador de su país. En cada minuto simulado, el simulador cuenta en Redis los espectadores de cada país y los comentarios del minuto, y lo guarda en la base de resúmenes de InfluxDB, que no vence (`audiencia_partido`, `comentarios_partido`); al terminar, guarda los espectadores únicos (`audiencia_resumen`). Con eso:

- `GET /partidos/{id}/audiencia` arma el análisis del partido como el de una transmisión: curva de espectadores simultáneos, pico, promedio, minutos vistos, únicos y tiempo medio. Acepta un tramo de minutos y un país.
- `GET /partidos/{id}/comentarios/por-minuto` cuenta los comentarios por minuto, país y origen.
- `GET /analisis/audiencia-por-minuto` promedia la audiencia por minuto de partido entre todas las simulaciones: es la consulta pensada para decidir cuándo poner publicidad.
- `GET /partidos/{id}/estadisticas?desde_minuto=&hasta_minuto=` da posesión, pases, tiros y faltas de un tramo.

Cada simulación es de tipo `demo` o `carga` (la de las pruebas de carga); las consultas de análisis aceptan `tipo=` para separarlas.

## Histórico en Neo4j

Al finalizar una simulación, el TPO consulta las muestras por equipo y minuto de InfluxDB y sus resúmenes. Si están las 91 muestras de ambos equipos y los goles coinciden con el marcador, las guarda en Neo4j como relaciones `ESTADISTICA_MINUTO` y `RESUMEN_ESTADISTICO` entre el partido y sus equipos. El guardado usa claves estables y se puede repetir sin duplicar. `GET /partidos/{id}/historico` devuelve el resumen y los 182 puntos archivados; después del archivo, el bloque de estadísticas consulta Neo4j.

Cada simulación usa un guion de jugadas de MongoDB y, al terminar, lo cruza con las muestras de InfluxDB. Neo4j conserva los eventos, sus jugadores y las relaciones entre jugadas, además de los totales y las muestras por minuto. Las acciones estadísticas sintéticas que no están en el guion siguen siendo contadores, no jugadas individuales. Si faltan muestras o falla el traspaso, el partido puede quedar finalizado con `archivo_estado=pendiente`. Un administrador puede reintentar con `POST /administracion/simulaciones/{id}/archivar` y el encabezado `X-Admin-Clave`. Las simulaciones antiguas sin muestras completas o sin goles por minuto no pueden archivarse como completas.

Las simulaciones nuevas guardan las muestras y jugadas crudas en la base InfluxDB `fixture2030_raw`, creada por defecto con retención de **7 días**. Al cerrar se calculan totales por equipo y jugador y se guardan en la base separada `fixture2030_resumenes`, sin vencimiento, como `resumen_partido_equipo` y `resumen_partido_jugador`. Reintentar el archivo usa claves y timestamp estables. Neo4j conserva el histórico, sus relaciones y las estadísticas por minuto; MongoDB conserva el guion y los metadatos de la simulación, sin copiar el relato completo.

La retención se aplica por tiempo desde la muestra, no inmediatamente al cerrar ni condicionada al éxito del archivo. Si falla el cierre o archivo, hay hasta siete días para corregirlo y reintentar antes de que caduquen datos crudos; pasado ese plazo puede resultar imposible reconstruir un histórico incompleto. La liberación física de espacio depende del proceso de retención de InfluxDB. Los datos anteriores siguen en `fixture2030_metrics` sin migración ni borrado; las corridas antiguas se siguen leyendo desde allí. Los resúmenes antiguos se copian a la nueva base solo si se vuelve a ejecutar el archivo mientras sus datos originales estén disponibles.

`INFLUX_RAW_DB`, `INFLUX_RESUMEN_DB` e `INFLUX_RAW_RETENCION` permiten configurar los nombres y la duración al crear las bases. Cambiar la duración en el entorno no modifica una base ya creada: requiere una operación administrativa separada. La retención de datos crudos no se aplica a Cassandra.

Los comentarios permanecen en Cassandra, particionados por partido, país y ventanas de 30 minutos, sin vencimiento automático configurado. `GET /partidos/{id}/comentarios?pais=ARG` (o `alcance=todos`) devuelve páginas de hasta 20 comentarios, del más nuevo al más viejo, durante y después del partido; para la página siguiente se manda `antes_de` con el valor `siguiente` de la anterior, incluso entre ventanas. La pantalla lo usa en el botón «Ver comentarios anteriores».

### Medir la vista de partido por la API

Con los servicios ya levantados, usar un partido que tenga simulación y estadísticas. Por ejemplo, para un partido finalizado:

```powershell
docker compose exec -T api python -m carga.ejecutar vista_partido --partido P-15 --pais ARG --finalizado --concurrencia 1 --duracion 5
```

Para uno en juego, quitar `--finalizado`. Cada usuario virtual consulta en secuencia el estado en vivo, las estadísticas, las jugadas y los comentarios mediante HTTP. Con un partido en juego se puede añadir `--usuario-id U0000001` para incluir un `POST` de comentario en cada vuelta; esto deja comentarios reales en Cassandra, del país asociado al usuario. El resumen y las muestras quedan en `evidencia/` con latencias y errores por ruta. Es una prueba en bucle sin pausa, no una reproducción exacta del ritmo de la pantalla. Empezar con concurrencia y duración bajas y aumentarlas solo si los recursos lo permiten. Un partido inexistente, sin estadísticas o con un estado que no corresponde produce errores HTTP, que figuran en el resultado.

El antiguo `scripts/medir.ps1` prepara volúmenes directamente en MongoDB y reinicia datos: sus consultas medidas usan la API, pero esa preparación no prueba los endpoints de escritura. No ejecutarlo para esta prueba de la vista. El diagnóstico histórico directo de MongoDB tampoco mide la capacidad de la aplicación.


## Preparar jugadas simuladas

La plantilla editable es [`seed/guion_simulacion.json`](seed/guion_simulacion.json): cada entrada indica tipo, minuto, equipo (`local` o `visitante`), dorsal y, opcionalmente, el número de una jugada anterior en `previa`. Los dorsales se resuelven contra los jugadores ya cargados en MongoDB y se usan los mismos IDs del grafo.

Con el entorno levantado y el fixture cargado, ejecutar desde `TPO` en PowerShell:

```powershell
.\scripts\cargar_guion.ps1 -Partido P-12
```

Se puede repetir sin borrar ni sobrescribir el guion ya guardado. Al iniciar una simulación sin guion, se crea automáticamente desde la plantilla. La plantilla se aplica solamente a nuevos guiones; editarla no modifica los que ya se guardaron. No usar `seed.run --reiniciar` para este procedimiento.
