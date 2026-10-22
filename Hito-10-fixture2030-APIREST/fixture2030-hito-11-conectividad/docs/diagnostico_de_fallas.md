# Diagnóstico de fallas

## Método

Seguir el orden de menor a mayor costo: configuración → resolución del host → TCP → handshake/protocolo → autenticación → autorización → contexto → operación de lectura → endpoint de API. Cada hallazgo debe registrar fecha, origen (`notebook` o `api-container`), dependencia, prueba, duración, resultado y próximo paso. No copiar el mensaje literal del driver cuando pudiera incluir host, URI o credenciales.

| Síntoma | Hipótesis inicial | Prueba mínima | Interpretación / siguiente paso |
|---|---|---|---|
| Host no resuelto | nombre incorrecto o DNS/red Docker equivocados | prueba de resolución del script TCP | Desde Compose, usar nombre de servicio (`mongodb`, `neo4j`, etc.); desde el host, host publicado correcto. |
| `Connection refused` | host encontrado, pero no hay listener en ese puerto o se rechaza la conexión | TCP a host/puerto exactos | Revisar `docker compose ps`, logs y puertos publicados/internos. |
| Timeout TCP | ruta bloqueada, firewall, servicio saturado o host incorrecto | repetir TCP con timeout explícito desde el mismo origen que la API | Inspeccionar red, binding, firewall y recursos; no empezar cambiando la consulta. |
| TCP OK pero el cliente falla | protocolo, TLS, autenticación, permisos o driver incompatibles | cliente/driver específico | Revisar credenciales y versión del cliente sin mostrarlas; no usar `curl` como prueba universal. |
| Database/keyspace/namespace no existe | contexto equivocado o inicialización incompleta | listar/consultar contexto con cliente adecuado | Confirmar variable de contexto y pasos de inicialización/seed. |
| Lectura sin resultados | recurso ausente, filtro incorrecto o ventana vacía | leer un recurso de control (`ARG`, `P-01`, partición o rango documentado) | Diferenciar respuesta vacía válida (frecuentemente `200`) de excepción de dependencia. |
| API no responde / `000` | la API no está iniciada o puerto 8000 no accesible | `curl` a `/openapi.json` y verificar proceso/contenedor | Iniciar API y revisar logs; no confundir con dependencia interna caída. |
| `404 NO_ENCONTRADO` | recurso inexistente | repetir con ID/código conocido | Para el contrato del Hito 10 es una ausencia de dominio válida, no prueba de caída del motor. |
| `422 VALIDACION` | path, query o cuerpo no cumple el contrato | probar un valor inválido de forma intencional (ej. `/equipos/arg`) | Corregir formato; es una respuesta de validación, no una falla de red. |
| `409 CONFLICTO` | transición/clave idempotente incompatible | revisar código y recurso, sin repetir escrituras en pruebas de lectura | Resolver el conflicto del dominio; no reintentar ciegamente. |
| `503 DEPENDENCIA_NO_DISPONIBLE` | el adaptador no puede usar el producto, credenciales/contexto incluidos | correlacionar `X-Request-ID` con logs y prueba nativa | Corregir la dependencia; la API no debe devolver `200` falso. |
| `504 DEPENDENCIA_TIMEOUT` | la dependencia superó el timeout del driver o deadline de request | medir duración y revisar timeout del driver y `DEADLINE_SEGUNDOS` | Ajustar tras identificar causa; no elevar límites como sustituto de diagnóstico. |
| `500 ERROR_INTERNO` | error inesperado en API/adaptador | revisar log correlacionado por request ID | Registrar tipo de excepción; no exponer mensajes internos al cliente. |
| InfluxDB `401/403` en query | token inválido o usuario sin permiso | la prueba HTTP registra solo el status y la clasificación, nunca el token ni el cuerpo completo. |
| InfluxDB `4xx` con token aceptado | database, tabla, consulta o contexto rechazado | contrastar database/tabla configuradas y una query temporal válida sin ampliar el rango. |
| Redis `TTL=-2` | la clave no existe en el instante de consulta; pudo no crearse o haber expirado | `PING`/driver distinguen esta situación de Redis no disponible; revisar una clave de demostración vigente si el caso de uso la exige. |

## Contrato de errores heredado del Hito 10

| Condición | Código HTTP esperado | Código de error del contrato |
|---|---:|---|
| Recurso de dominio inexistente | `404` | `NO_ENCONTRADO` (o código específico como `SESION_NO_VIGENTE`) |
| Parámetro/cuerpo inválido | `422` | `VALIDACION` |
| Conflicto de dominio/idempotencia | `409` | `CONFLICTO` |
| Dependencia no disponible o rechazo técnico de conexión | `503` | `DEPENDENCIA_NO_DISPONIBLE` |
| Dependencia o request supera el tiempo permitido | `504` | `DEPENDENCIA_TIMEOUT` |
| Error inesperado de aplicación | `500` | `ERROR_INTERNO` |

Las respuestas de error siguen `{"error":{"codigo":"...","mensaje":"...","request_id":"..."}}`; el encabezado `X-Request-ID` debe coincidir con `request_id` cuando hay cuerpo de error.

## Protección de evidencia

- Registrar nombre de dependencia y operación, tipo de error, status, duración y request ID.
- No guardar `.env`, passwords, tokens, URI con credenciales o encabezados de autenticación.
- No ejecutar DDL, `DEL`, actualizaciones ni escrituras para comprobar conectividad. La única acción de falla controlada es detener y volver a iniciar el contenedor Redis local, conservando el volumen.
