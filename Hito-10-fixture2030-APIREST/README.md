# Hito 10 — API REST integrada del Fixture 2030

API REST (FastAPI) que expone los seis módulos NoSQL del Fixture 2030 —MongoDB, Neo4j, Cassandra, Redis, InfluxDB e IRIS— mediante adaptadores separados. Cada endpoint resuelve un caso de uso concreto contra la fuente que corresponde; no hay consultas libres ni endpoints genéricos.

- Contrato: [openapi/openapi.yaml](openapi/openapi.yaml) (generado desde el código) · Swagger UI en `http://localhost:8000/docs`.
- Pruebas: 118 unitarias, 6 de dependencia inaccesible y 18 de integración contra las bases reales (ver [tests/README.md](tests/README.md)).
- Colección Postman (38 requests, 95 aserciones; ejecutada con Newman sin fallos, ver `docs/evidencia/`): [postman/fixture2030_collection.json](postman/fixture2030_collection.json) · ejemplos cURL: [postman/ejemplos_curl.sh](postman/ejemplos_curl.sh).

## Requisitos

- Docker Desktop con Docker Compose v2 (las seis bases corren en contenedores; IRIS usa imagen `linux/amd64`).
- Git Bash, WSL, macOS o Linux (los scripts son `bash`).
- Python 3.12 o superior **solo** para correr las pruebas unitarias en el notebook (`pip install -r requirements.txt`). La API y los drivers corren dentro del contenedor.
- Unos 4 GB de RAM libres para las seis bases.

## Puesta en marcha (en este orden)

1. **Configurar el entorno.** `cp .env.example .env` y completar las contraseñas (`MONGO_PASSWORD`, `NEO4J_PASSWORD` —mínimo 8 caracteres—, `REDIS_PASSWORD`, `IRIS_PASSWORD`). El `.env` no se versiona. Si algún puerto estándar ya está ocupado por otra base (por ejemplo, los contenedores de los Hitos 4 a 7), descomentar y cambiar los `*_HOST_PORT` y los `*_PORT` correspondientes (ver [docs/conectividad_y_configuracion.md](docs/conectividad_y_configuracion.md)).
2. **Levantar las bases y sembrar datos.** `bash scripts/levantar_servicios.sh`. Espera los healthchecks (Cassandra e IRIS tardan 1–2 minutos), crea el token y la base de InfluxDB, crea el usuario de la API en IRIS, compila las clases del Hito 9 y siembra datos sintéticos (`P-01`…`P-08`). Es idempotente.
3. **Iniciar la API.** `bash scripts/iniciar_api.sh` (contenedor, puerto 8000). Alternativa en el notebook: `bash scripts/iniciar_api.sh --local` (requiere instalar también `requirements-drivers.txt`).
4. **Verificar conectividad.** `bash scripts/verificar_conectividad.sh` comprueba los puertos de cada base y `GET /health`.
5. **Explorar.** Swagger UI: `http://localhost:8000/docs`.
6. **Reproducir escenarios.** Importar `postman/fixture2030_collection.json` en Postman (variable `base_url`), ejecutarla por consola con `npx newman run postman/fixture2030_collection.json --env-var idem_key=<valor único>` (requiere Node), o correr `bash postman/ejemplos_curl.sh`.
7. **Correr las pruebas.** `bash scripts/ejecutar_pruebas.sh todo` (o `unit`, `drivers`, `integration`).
8. **Detener sin perder datos.** `docker compose --profile api stop`. Los datos quedan en volúmenes nombrados. **No usar `docker compose down -v`**, que los borra.

## Endpoints

| Método | Ruta | Fuente | Caso de uso |
|---|---|---|---|
| GET | `/equipos/{codigo}` | MongoDB | Ficha de una selección |
| GET | `/equipos/{codigo}/jugadores` | MongoDB | Plantel paginado, filtro por posición |
| GET | `/partidos/{id}` | Neo4j | Partido con equipos, estadio y resultado |
| GET | `/partidos/{id}/eventos` | Neo4j | Eventos del partido por minuto |
| GET | `/partidos/{id}/comentarios` | Cassandra | Comentarios de un país en una ventana de 30 min (paginado) |
| POST | `/partidos/{id}/comentarios` | Cassandra (+ Neo4j) | Comentar un partido, idempotente por `Idempotency-Key` |
| GET | `/sesiones/{usuario}` | Redis | Sesión vigente (404 si no existe, expiró o fue cerrada) |
| DELETE | `/sesiones/{usuario}` | Redis | Invalidar la sesión (idempotente) |
| GET | `/partidos/{id}/estadisticas` | InfluxDB | Estadísticas en una ventana acotada con agregación |
| GET | `/partidos/{id}/detalle` | IRIS | Partido y eventos como objetos |
| POST | `/partidos/{id}/estado` | IRIS | Transición validada del estado del partido |
| GET | `/health` | Las seis | Estado de cada dependencia |

## Documentación

| Documento | Contenido |
|---|---|
| [docs/casos_de_uso.md](docs/casos_de_uso.md) | Consumidores, entradas, salidas, fuentes y criterios de éxito |
| [docs/arquitectura_y_adaptadores.md](docs/arquitectura_y_adaptadores.md) | Capas, adaptadores por producto, mapa de endpoints, diseño por acceso |
| [docs/contratos_y_errores.md](docs/contratos_y_errores.md) | Formato de error, validaciones, paginación e idempotencia |
| [docs/conectividad_y_configuracion.md](docs/conectividad_y_configuracion.md) | Variables, hosts y puertos (notebook vs. Docker), timeouts |
| [docs/pruebas_y_evidencia.md](docs/pruebas_y_evidencia.md) | Pruebas, evidencia, seguridad, rendimiento y coherencia con el TPO |
| [docs/cambios_en_las_bases.md](docs/cambios_en_las_bases.md) | Qué se agregó o cambió en cada base respecto de los hitos anteriores |

## Estructura

```
app/        routes/ (HTTP) · services/ (casos de uso) · adapters/ (un driver por base) · schemas/ · config/
openapi/    openapi.yaml (generado con scripts/exportar_openapi.py)
postman/    colección Postman y ejemplos cURL
seed/       datos sintéticos e inicialización de cada base
tests/      unit/ · integration/
scripts/    levantar_servicios · iniciar_api · verificar_conectividad · ejecutar_pruebas · capturar_evidencia · medir_latencia
docs/       documentación y evidencia/
```

## Notas

- Las sesiones de demostración expiran a los 30 minutos (TTL de inactividad, como en el Hito 7). Para recrearlas: `docker compose --profile api run --rm api python -m seed.run --solo redis`.
- La colección Postman usa `idem_key` fijo: la primera corrida de "Crear comentario" da 201 y las siguientes 200; cambiar la variable entre corridas completas.
- Si Docker avisa `additional privileges requested: pass "--allow=fs.read=Dockerfile"` al construir la imagen, ejecutar antes `export BUILDX_BAKE_ENTITLEMENTS_FS=0`.
- Todos los datos son sintéticos. Los marcadores de los partidos son simulados (`origen: SIMULADO`).

## Hito 11 — Evaluación de conectividad

La carpeta [`fixture2030-hito-11-conectividad/`](fixture2030-hito-11-conectividad/README.md) agrega el procedimiento reproducible para verificar resolución, TCP, drivers, rutas de la API, health/degradación y falla reversible de Redis. Ejecutar `bash fixture2030-hito-11-conectividad/scripts/evaluar_conectividad.sh todo` luego de iniciar las bases y la API.
