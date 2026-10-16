# Pruebas y evidencia

## Método

| Nivel | Qué hace | Dónde corre | Comando |
|---|---|---|---|
| Unitarias (118) | Rutas y servicios con adaptadores falsos: válido, inválido, inexistente, vacío, sesión expirada, dependencia caída, paginación, escritura repetida, contrato OpenAPI y colección Postman | Notebook (solo `requirements.txt`) | `scripts/ejecutar_pruebas.sh unit` |
| Dependencia inaccesible (6) | Cada adaptador real contra un host inaccesible: error controlado, acotado en tiempo y sin filtrar hosts | Contenedor `api` (necesita los drivers) | `scripts/ejecutar_pruebas.sh drivers` |
| Integración (18) | Black-box contra la API y las seis bases reales | Notebook, contra la API en `:8000` | `scripts/ejecutar_pruebas.sh integration` |
| Postman / Newman / cURL | Mismos escenarios: 38 requests con 95 aserciones (estado, `X-Request-ID`, formato de error) | Postman, `npx newman run postman/fixture2030_collection.json` o `postman/ejemplos_curl.sh` | ver README |

Resultado de la última ejecución (stack real levantado con `scripts/levantar_servicios.sh`): unitarias 118/118, dependencia inaccesible 6/6, integración 18/18, Newman 38 requests / 95 aserciones sin fallos. La entrega también se verificó desde un clon limpio del repositorio, siguiendo el README desde cero.

## Cobertura de §5.12 de la consigna

| Requisito | Prueba | Evidencia |
|---|---|---|
| Request válida por módulo | `test_equipos`, `test_partidos_grafo`, `test_comentarios`, `test_sesiones`, `test_estadisticas`, `test_partidos_iris`; integración por módulo | `*_endpoints.txt` |
| Parámetro inválido | los mismos archivos (casos parametrizados que además verifican que el adaptador no fue invocado) | `*_endpoints.txt` (422) |
| Recurso inexistente | 404 en cada módulo | `*_endpoints.txt` (404) |
| Respuesta vacía válida | jugadores sin coincidencia, partido sin eventos, partición vacía, ventana sin puntos | `*_endpoints.txt` |
| Sesión ausente o expirada | `test_sesiones` (inexistente y cerrada), integración | `*_endpoints.txt` |
| Dependencia detenida | `test_dependencia_caida` (6 bases), `test_health`, y prueba real con Redis detenido | `*_dependencia_caida.txt` |
| Escritura repetida | `test_comentarios`, `test_partidos_iris`, integración (201 luego 200) | `*_endpoints.txt` (201/200/409) |
| Límites, paginación, ventanas | `limit`, `offset`, cursor, ventana de 30 min, ventana y tope de InfluxDB | `*_endpoints.txt` |
| Documentación y respuesta real compatibles | `test_contrato`, fixture `documentado`, `test_postman` | — |
| Request lenta | `test_request_lenta_se_corta_con_504_dentro_del_deadline` | `*_dependencia_caida.txt` |

La evidencia está en [evidencia/](evidencia/): `*_endpoints.txt` (respuestas reales de cada endpoint y escenario de error), `*_dependencia_caida.txt` (Redis detenido), `*_logs_api.txt` (logs de la API), `*_latencia.txt` y `*_newman.txt` (colección Postman ejecutada con Newman: 38 requests, 95 aserciones, 0 fallos). Se genera con `scripts/capturar_evidencia.sh` y `scripts/medir_latencia.py`.

## Rendimiento básico

Método: 50 requests secuenciales por endpoint, después de 5 de calentamiento, medidas en el cliente. Entorno: Windows 11, cliente Python 3.14, la API y las seis bases en contenedores Docker (un nodo cada una), datos de la siembra (`P-01`…`P-08`), un solo cliente y sin carga concurrente.

| Endpoint | p50 | p95 | Errores |
|---|---|---|---|
| MongoDB `GET /equipos/ARG` | 4,2 ms | 6,8 ms | 0/50 |
| Neo4j `GET /partidos/P-01` | 11,8 ms | 14,5 ms | 0/50 |
| Cassandra `GET /comentarios` | 5,9 ms | 7,5 ms | 0/50 |
| Redis `GET /sesiones/U001` | 2,9 ms | 4,0 ms | 0/50 |
| InfluxDB `GET /estadisticas` (5 min, 1m) | 11,1 ms | 12,1 ms | 0/50 |
| IRIS `GET /detalle` | 3,0 ms | 3,8 ms | 0/50 |

Limitaciones: laptop de desarrollo, un solo cliente, datos mínimos (80 jugadores, 5 comentarios, 4800 puntos), sin red real entre cliente y servidor, sin réplicas ni particiones distribuidas. **Estas cifras no permiten afirmar nada sobre carga ni sobre millones de usuarios**; solo muestran que el camino API → adaptador → base funciona con baja latencia en condiciones ideales.

## Seguridad

- **Secretos:** contraseñas y token en el `.env` local (ignorado por git). No hay credenciales en código, compose, scripts, logs, documentación ni evidencia. La evidencia se revisó con una búsqueda de `password`, `token` y `apiv3_` (0 coincidencias).
- **Logs:** cada request registra método, ruta, estado, duración y `request_id`; cada operación contra una base registra dependencia, operación, resultado, tipo de excepción (`causa`, solo el nombre de la clase) y duración. No se registran cuerpos, cabeceras ni mensajes de los drivers, que podrían incluir hosts o credenciales.
- **Respuestas:** los errores de dependencia no incluyen el detalle del driver. La sesión no expone `token_ref`. IRIS no expone su id interno.
- **Verificación manual antes de entregar:** `git grep -n -i -E "password|apiv3_" -- ':!*.example' ':!*.md'` no debe mostrar valores.

## Coherencia con el TPO

| Módulo | Hito de origen | Qué se tomó del hito | Qué cambia en este hito |
|---|---|---|---|
| MongoDB | 4 | Colecciones `equipos` y `jugadores`, relación por `jugadores.equipo = equipos.codigo`, validación e índices | Solo datos: 16 equipos y 80 jugadores sintéticos |
| Neo4j | 5 | `Equipo`, `Partido`, `Estadio`, `Evento` y sus relaciones | Identificadores de partido `P-01`…`P-08` (en el Hito 5 son `P001`…`P032`) |
| Cassandra | 6 | `comentarios_por_partido_pais` y `comentarios_por_likes_partido_pais` con su clave de partición | Tabla auxiliar de idempotencia (ver [cambios_en_las_bases.md](cambios_en_las_bases.md)) |
| Redis | 7 | Sesión como Hash `f2030:sesion:{usuario}` con TTL de 30 min | Contraseña en el servidor; ids de usuario `U001`… |
| InfluxDB | 8 | Tabla `estadisticas_partido` con sus tags y campos | `partido_id` = `P-01`… (en el Hito 8 son `M001`…) |
| IRIS | 9 | Clases `Fixture.Partido` y `Fixture.Evento` sin modificar | `Codigo` = `P-01`… (en el Hito 9 es un código generado por la demo) |

Se unificó el identificador de partido en `P-NN` para que un mismo partido se pueda cruzar entre las seis fuentes. Los esquemas no cambian; solo los valores de los datos de ejemplo. El detalle de cada cambio está en [cambios_en_las_bases.md](cambios_en_las_bases.md).

### Limitaciones del laboratorio

Un nodo por base, sin réplicas ni particionado real, sin carga concurrente, datos sintéticos y sin autenticación de consumidores en la API. No es una prueba de capacidad para millones de usuarios.
