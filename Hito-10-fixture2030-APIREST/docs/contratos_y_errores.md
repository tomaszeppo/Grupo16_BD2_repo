# Contratos, validación, errores e idempotencia

El contrato está en [../openapi/openapi.yaml](../openapi/openapi.yaml). Se genera desde el código con `python scripts/exportar_openapi.py`; nunca se edita a mano.

## Formato de error único

```json
{"error": {"codigo": "NO_ENCONTRADO", "mensaje": "No existe el partido 'P-99'.", "request_id": "…", "detalle": [{"campo": "…", "motivo": "…"}]}}
```

`detalle` solo aparece en errores de validación. El `request_id` coincide con la cabecera `X-Request-ID` de la respuesta y con los logs de la API y de los adaptadores.

| Situación | HTTP | `codigo` | Ejemplo |
|---|---|---|---|
| Parámetro, cabecera o cuerpo inválido | 422 | `VALIDACION` | `/equipos/arg` |
| Recurso inexistente | 404 | `NO_ENCONTRADO` | `/partidos/P-99` |
| Sesión ausente, expirada o cerrada | 404 | `SESION_NO_VIGENTE` | `/sesiones/U999` |
| Conflicto de negocio | 409 | `CONFLICTO` | `Programado → Finalizado`; misma `Idempotency-Key` para otro partido |
| Dependencia no disponible | 503 | `DEPENDENCIA_NO_DISPONIBLE` | Redis detenido |
| Timeout de la dependencia o tope de la request | 504 | `DEPENDENCIA_TIMEOUT` | consulta que excede `TIMEOUT_SEGUNDOS` o `DEADLINE_SEGUNDOS` |
| Error inesperado | 500 | `ERROR_INTERNO` | el detalle técnico queda solo en los logs |

Nunca se devuelve 200 para esconder una caída. En `GET /health` el 503 conserva el cuerpo con el estado de cada fuente.

## Respuesta vacía válida frente a dependencia caída

Son 200 con lista vacía: jugadores sin coincidencia con el filtro, partido sin eventos, partición de comentarios sin datos y ventana de InfluxDB sin puntos. Es un resultado correcto de una consulta que funcionó. Un timeout, una credencial inválida o una base caída producen 503/504 aun si la consulta habría devuelto una lista vacía. En InfluxDB, además, cualquier respuesta HTTP distinta de 200 se trata como dependencia caída.

## Validación (antes de consultar)

| Dato | Regla |
|---|---|
| `partido_id` | `^P-\d{2,3}$` |
| `codigo` de equipo, `pais`, `equipo` | `^[A-Z]{3}$` |
| `usuario_id` | `^U\d{3,6}$` |
| `limit` | 1–100 (eventos: 1–200) |
| `offset` | ≥ 0 |
| `posicion` | `Portero`, `Defensa`, `Centrocampista`, `Delantero` |
| `ventana` (comentarios) | ISO-8601 con zona, minuto `:00` o `:30`, sin segundos |
| `desde`/`hasta` (estadísticas) | ISO-8601 con zona; `hasta > desde`; máximo 120 minutos |
| `agregacion` | `raw`, `1m`, `5m` |
| `cursor` | Base64 URL-safe válido (si no, 422) |
| `Idempotency-Key` | 8–64 caracteres `[A-Za-z0-9_-]`, obligatoria |
| cuerpo de comentario | `contenido` 1–280, `usuario_nombre` 1–60; sin campos extra |
| cuerpo de estado | `Programado`, `En juego` o `Finalizado`; sin campos extra |

Un parámetro inválido se rechaza con 422 sin tocar la base. En los tests unitarios se verifica que el adaptador no fue invocado.

## Timeouts

`TIMEOUT_SEGUNDOS` (3 s) aplica a cada operación de red del driver. `DEADLINE_SEGUNDOS` (10 s) es un tope duro por request: pasado ese tiempo la API responde 504 sin esperar al driver. Medición real con Redis detenido: 503 en unos 4 segundos (ver `docs/evidencia/`).

## Idempotencia y escrituras

| Operación | Efecto | Si se repite |
|---|---|---|
| Todos los `GET` | Ninguno | Igual |
| `POST /partidos/{id}/comentarios` | Alta en Cassandra | Con la misma `Idempotency-Key`: 200 con el mismo comentario (mismo `comentario_id` y `creado_en`), sin duplicar. Si la clave se reutiliza para otro partido o país: 409 |
| `DELETE /sesiones/{usuario}` | `DEL` de la clave | 204 siempre (aunque no exista) |
| `POST /partidos/{id}/estado` | `CambiarEstado` + `%Save` | Si ya está en ese estado: 200 sin escribir. Transición inválida: 409 |

**Cómo se evita el duplicado en comentarios.** `comentario_id` se deriva de la clave (UUID v5). En Cassandra, `creado_en` y `ventana` forman parte de la clave primaria, así que un reintento tardío que cayera en otra ventana de 30 minutos crearía otra fila. Para evitarlo, la API usa la tabla auxiliar `comentarios_idempotencia` (TTL de 24 h), que fija `ventana` y `creado_en` en el primer intento mediante `INSERT … IF NOT EXISTS`. Las inserciones en las dos tablas de comentarios también son `IF NOT EXISTS`, de modo que un reintento tras una caída entre ambas completa lo que faltó. La tabla auxiliar no está en el diseño del Hito 6; se documenta en [cambios_en_las_bases.md](cambios_en_las_bases.md).

## Cómo se verifica que OpenAPI describe el comportamiento real

- `tests/unit/test_contrato.py` compara `openapi.yaml` con lo que genera la aplicación y exige exactamente los 12 endpoints previstos y los códigos de error comunes en cada operación.
- La fixture `documentado` de las pruebas unitarias comprueba que cada código HTTP devuelto esté declarado en el contrato de esa operación y que los errores tengan los campos comunes.
- `tests/unit/test_postman.py` comprueba que cada request de la colección Postman exista en OpenAPI.
- Las pruebas de integración ejecutan los mismos escenarios contra las bases reales.
