# Matriz de conectividad

## Criterios de clasificación

| Estado | Significado operacional |
|---|---|
| `UP` / `OK` | La prueba indicada se ejecutó correctamente en el origen y contexto documentados. |
| `DOWN` / `FAIL` | Se ejecutó una prueba válida y falló; registrar capa, hipótesis y próximo paso. |
| `DEGRADED` | La API sigue respondiendo, pero una o más dependencias están fallando. |
| `NOT_CONFIGURED` | El producto no está configurado en ese entorno. |
| `SKIP` | La prueba no se ejecutó por falta de herramienta, configuración o contenedor; no significa que esté caído. |
| `UNKNOWN` | No existe evidencia suficiente para determinar el estado. |

## Mapa base y última evidencia histórica

La evidencia histórica de Hito 10 se ejecutó el **16/10/2026** en un stack de Docker con la API y los seis productos. En `../../docs/evidencia/20261016_120555_endpoints.txt`, `GET /health` devolvió `200` y las seis fuentes (`mongodb`, `neo4j`, `cassandra`, `redis`, `influxdb`, `iris`) quedaron `ok`. El mismo archivo contiene lecturas `200` representativas de los seis módulos. Es una observación histórica del Hito 10, no una afirmación de estado actual permanente.

| Producto | Host/puerto según entorno | Protocolo/contexto | Operación de API validada en evidencia anterior | Estado histórico (16/10/2026) | TCP Hito 11 |
|---|---|---|---|---|---|
| MongoDB | Host: `localhost:27017`; Compose: `mongodb:27017` | MongoDB; database `fixture2030` | `GET /equipos/ARG` → `200` | `UP` en el momento de prueba | `OK` — 22/10/2026; TCP accesible desde notebook y api-container |
| Neo4j | Host: `localhost:7687`; Compose: `neo4j:7687`; Browser HTTP `7474` por separado | Bolt; database `neo4j` | `GET /partidos/P-01` → `200` | `UP` en el momento de prueba | `OK` — 22/10/2026; TCP accesible desde notebook y api-container |
| Cassandra | Host: `localhost:9042`; Compose: `cassandra:9042` | CQL; keyspace `fixture2030` | `GET /partidos/P-01/comentarios?...` → `200` | `UP` en el momento de prueba | `OK` — 22/10/2026; TCP accesible desde notebook y api-container |
| Redis | Host: `localhost:6379`; Compose: `redis:6379` | RESP; base lógica 0, clave de sesión | `GET /sesiones/U001` → `200` | `UP` en prueba normal; `DOWN` durante la prueba de caída controlada | `OK` — 22/10/2026; TCP accesible desde notebook y api-container |
| InfluxDB | Host: `localhost:8181`; Compose: `influxdb:8181` | HTTP `/api/v3/query_sql`; `fixture2030_metrics` | `GET /partidos/P-01/estadisticas?...` → `200` | `UP` en el momento de prueba | `OK` — 22/10/2026; TCP accesible desde notebook y api-container |
| IRIS | Host: `localhost:1972`; Compose: `iris:1972`; portal HTTP `52773` por separado | Superserver; namespace `USER` | `GET /partidos/P-01/detalle` → `200` | `UP` en el momento de prueba | `OK` — 22/10/2026; TCP accesible desde notebook y api-container |

## Falla y recuperación histórica

El archivo `../../docs/evidencia/20261016_120557_dependencia_caida.txt` registra Redis detenido mediante `docker compose stop redis`: `GET /sesiones/U001` devolvió `503 DEPENDENCIA_NO_DISPONIBLE` y `/health` devolvió `503` con `estado=degradado`; las otras cinco fuentes continuaron en `ok`. `../../docs/evidencia/20261016_120557_logs_api.txt` relaciona la solicitud con `request_id=cec7beeeaf714c48b312d7747a224847` y muestra la causa de tipo `ConnectionError`, sin divulgar credenciales.

## Ejecuciones de Hito 11

Al ejecutar los scripts, las salidas completas se guardan en `docs/evidencia/resultados_tcp.txt`, `docs/evidencia/resultados_clientes.txt` y `docs/evidencia/resultados_api.txt`. Actualizar esta matriz únicamente a partir de salidas reales y conservar fecha, origen, entorno y limitaciones. No convertir `SKIP`, `UNKNOWN` ni una evidencia histórica en un `UP` actual.

**Ejecución real verificada el 22/10/2026** en macOS arm64, commit observado `e5f3949` (timestamps originales en UTC).

- TCP: notebook 9/9 OK; contenedor API 9/9 OK. El endpoint HTTP de InfluxDB sin token respondió 401 y se clasificó como alcanzable con autenticación requerida; no se interpretó como fallo TCP.
- Clientes nativos: 8 OK, 0 FAIL y 0 SKIP. Las seis bases permitieron sus lecturas mínimas.
- API REST: 15 OK y 0 FAIL. `/health` devolvió 200 con las seis dependencias en estado OK. Se diferenciaron los 404, el 422 y las respuestas vacías válidas.
- Falla controlada de Redis: a las 19:26:34Z, `GET /sesiones/U001` devolvió 503 `DEPENDENCIA_NO_DISPONIBLE` con request ID correlacionado. Tras reiniciar Redis, respondió `PONG` y `/health` devolvió 200. Conservar la evidencia en `docs/evidencia/capturas_redactadas/`.

Estos resultados describen las pruebas y el entorno observados; no constituyen una prueba de rendimiento o carga masiva.


## Trazabilidad de requisitos funcionales (RF)

| Requisito | Implementación / evidencia en esta entrega |
|---|---|
| RF1 | `docs/mapa_de_dependencias.md`: seis productos, módulo, host, puerto, protocolo, contexto, driver, lectura y endpoint. |
| RF2 | `docs/topologia_y_entornos.md`: notebook vs red Compose, hosts/puertos publicados e internos. |
| RF3 | `config/configuracion-ejemplo.env`, `config/.gitignore` y scripts que no imprimen variables sensibles. |
| RF4 | `scripts/prueba_tcp.sh`: DNS/resolución desde notebook y desde `api` cuando está en ejecución. |
| RF5 | `scripts/prueba_tcp.sh`: TCP con timeout, resultado y próximo paso; incluye los seis puertos de datos. |
| RF6 | `scripts/prueba_clientes_nativos.sh`: drivers reales del Hito 10, no un `curl` genérico contra puertos binarios. |
| RF7 | Prueba por driver con identidad configurada y acceso al contexto; Cassandra se documenta sin autenticación CQL en el adaptador existente. |
| RF8 | Las lecturas driver son limitadas y no escriben datos ni alteran el dominio. |
| RF9 | MongoDB: `ping` y lectura `equipos.codigo=ARG`. |
| RF10 | TCP/HTTP distingue Neo4j Browser `7474` de Bolt `7687`; driver ejecuta lectura Cypher de `P-01`. |
| RF11 | Cassandra: puerto CQL `9042`, keyspace y `SELECT` limitado por la partición completa del módulo comentarios. |
| RF12 | Redis: `PING` más lectura de sesión/TTL; la clave ausente se informa separada de un error de conexión. |
| RF13 | InfluxDB: `ping` HTTP con cliente configurado y consulta temporal de 1 minuto, máximo 5 puntos, con database/token del entorno. |
| RF14 | TCP/HTTP distingue portal IRIS `52773` de Superserver `1972`; el driver comprueba namespace y lectura de `Fixture.Partido`. |
| RF15 | `scripts/prueba_api.sh` ejecuta rutas GET de todos los módulos y registra método, path, status, duración, request ID y resumen. |
| RF16 | Esta matriz registra origen y estado histórico; los archivos `resultados_*.txt` conservan resultados fechados de cada ejecución. |
| RF17 | `docs/diagnostico_de_fallas.md`, `/health` existente y modo `fallo-redis` documentan/ejercitan comportamiento ante dependencia caída. |
| RF18 | `scripts/prueba_api.sh` verifica respuesta exitosa, 404, 422 y vacíos válidos; códigos 503/504/500 se explican en diagnóstico. |
| RF19 | Scripts imprimen `request_id`, duración, producto/prueba/resultado y correlacionan logs del contenedor cuando disponible; logs del Hito 10 ya incluyen duración y tipo de causa. |
| RF20 | `fallo-redis` restaura Redis, repite `/health` y registra el resultado tras recuperación. |
| RF21 | `fallo-redis` usa `docker compose stop/start redis`, sin `down -v` ni borrado de volúmenes; también existe evidencia histórica. |
| RF22 | Estructura preparada para añadir al repositorio GitHub existente; `README.md` incluye comandos de `git add`, `commit` y `push`. El push requiere ejecutarse con las credenciales del equipo. |

## Trazabilidad de requisitos no funcionales (RNF)

| Grupo | Requisitos cubiertos por el diseño |
|---|---|
| RNF1, RNF15, RNF16 | README reproducible, modos separados (`todo`, `tcp`, `native`, `api`, `fallo-redis`), nombres predecibles y ubicación navegable dentro del proyecto. |
| RNF2, RNF3, RNF4, RNF14 | Diagnóstico por capas, origen de conexión explícito, cliente/protocolo adecuado y contexto indicado por producto. |
| RNF5, RNF12 | Timeout por socket, `curl --max-time`, timeouts configurados por los drivers y ausencia de bucles de reintentos de conexión no acotados. |
| RNF6 | Verificaciones nativas de lectura/ping; el único fallo inducido detiene/reinicia Redis sin modificar datos ni volúmenes. |
| RNF7, RNF8 | `.env` fuera del repositorio, ejemplo sin secretos, logs redactados y carpeta prevista para capturas revisadas. |
| RNF9, RNF10 | Estados `UP`, `DOWN`, `DEGRADED`, `UNKNOWN`, `NOT_CONFIGURED`, `SKIP`; cada fallo sugiere hipótesis y paso siguiente. |
| RNF11 | Request ID, dependencia/operación, duración, status y causa por tipo de excepción. |
| RNF13 | Cada modo se ejecuta de forma independiente y el resultado distingue `SKIP` de fallo. |
| RNF17 | La documentación limita la conclusión de cada prueba a la operación efectivamente observada; no afirma capacidad de carga. |
| RNF18 | Salidas fechadas, origen, versión/commit si el repositorio Git existe, producto, prueba, resultado y limitaciones. |
