# Pruebas

```
bash scripts/ejecutar_pruebas.sh unit          # notebook, sin bases (pip install -r requirements.txt)
bash scripts/ejecutar_pruebas.sh drivers       # contenedor api: cada adaptador real contra una fuente inaccesible
bash scripts/ejecutar_pruebas.sh integration   # contra la API y las seis bases levantadas
bash scripts/ejecutar_pruebas.sh todo
```

| Archivo | Qué cubre | Requiere |
|---|---|---|
| `unit/test_nucleo.py` | Formato de error, `X-Request-ID`, error 500 genérico, traducción de errores de driver, tope de duración (504) | — |
| `unit/test_equipos.py` | MongoDB: ficha, plantel paginado, filtros, 404, vacíos, 422, 503 | — |
| `unit/test_partidos_grafo.py` | Neo4j: partido, eventos, 404 frente a vacío | — |
| `unit/test_comentarios.py` | Cassandra: ventana, cursor, idempotencia, 409, validación del cuerpo y de la clave | — |
| `unit/test_sesiones.py` | Redis: vigente, cerrada, expirada, invalidación idempotente | — |
| `unit/test_estadisticas.py` | InfluxDB: ventana, agregación, tope de puntos, construcción segura del SQL | — |
| `unit/test_partidos_iris.py`, `unit/test_adaptador_iris.py` | IRIS: transiciones, idempotencia, lectura de filas ligadas al cursor | — |
| `unit/test_health.py` | `/health` con todas las fuentes y con una caída | — |
| `unit/test_contrato.py`, `unit/test_postman.py` | `openapi.yaml` y la colección Postman alineados con la aplicación | — |
| `unit/test_seed_datos.py` | Coherencia de identificadores de los datos de siembra | — |
| `integration/test_dependencia_caida.py` | Fuente inaccesible: error controlado, acotado en tiempo, sin filtrar hosts | Drivers (contenedor `api`) |
| `integration/test_api_real.py` | Los 12 endpoints contra las seis bases reales | Stack levantado |

Las pruebas de integración modifican datos de laboratorio (agregan comentarios, cierran la sesión `U003`, mueven `P-08` a "En juego"). `ejecutar_pruebas.sh integration` restaura las sesiones de demostración antes de correr. No usan ni exponen secretos: toman la configuración de la API ya levantada.
