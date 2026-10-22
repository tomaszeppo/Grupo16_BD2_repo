# Health, liveness, readiness y degradación

## Comportamiento que ya implementa el Hito 10

`GET /health` está implementado en `app/routes/health.py` y `app/services/health.py`. Llama a `ping()` de los seis adaptadores en paralelo y aplica los timeouts configurados por los drivers. Respuesta actual del contrato:

- HTTP `200` y `{"estado":"ok","fuentes":{...}}` cuando todas las fuentes pasan la prueba.
- HTTP `503` y `{"estado":"degradado","fuentes":{...}}` si una o más fallan; cada fuente muestra `estado` (`ok`/`caida`) y `latencia_ms`.
- La ruta agrega `X-Request-ID` y el middleware registra status, duración y request ID. Los adaptadores registran dependencia, operación, resultado, tipo de excepción y duración, sin el texto del driver.

El chequeo se ejecuta al invocar `/health`; no se ejecuta indiscriminadamente en cada endpoint de negocio. Las rutas de negocio contactan únicamente las fuentes que requieren. En el Hito 10 se midió `/health` con respuesta `200` y las seis dependencias `ok` el 16/10/2026. En una prueba posterior del mismo día, Redis detenido hizo que `/health` devolviera `503`, con Redis `caida` y las otras cinco fuentes `ok`; ambas evidencias se enlazan en `../../docs/evidencia/`.

## Distinciones

| Tipo | Estado en el Hito 10 | Semántica recomendada |
|---|---|---|
| Liveness (proceso vivo) | No existe endpoint separado | Un chequeo muy barato de que el proceso HTTP responde; no debe consultar todas las bases. Se propone como extensión futura, no es parte del contrato actual. |
| Readiness (listo para tráfico) | No existe endpoint separado | Indicar si están disponibles las dependencias esenciales para las rutas que se habilitan. Se propone como extensión futura; documentar política antes de incorporarla. |
| Health profundo por dependencia | `GET /health` implementado | Evaluación individual de las seis dependencias con resultado y latencia. El `503` representa degradación; consultar con frecuencia razonable y timeout controlado. |

No se agrega un endpoint nuevo a la API heredada porque el alcance del Hito 11 es evaluar y documentar el comportamiento existente, no cambiar el contrato REST del compañero. Si más adelante se agregan liveness/readiness, deben documentarse, probarse y versionarse por separado.

## Estados normalizados en esta evaluación

`UP`: prueba concreta correcta; `DOWN`: prueba ejecutada y fallida; `DEGRADED`: la API responde, pero una o más fuentes fallan; `UNKNOWN`: aún no comprobado; `NOT_CONFIGURED`: el entorno no preparó ese producto; `SKIP`: falta una herramienta/configuración y la prueba ni siquiera se ejecutó.

## Timeouts y recuperación

El `.env.example` del Hito 10 define `TIMEOUT_SEGUNDOS=3.0` y `DEADLINE_SEGUNDOS=10.0`. La prueba de API aplica `--max-time` a `curl`; la prueba TCP usa timeout por socket; el cliente driver reutiliza timeouts del `Settings` del Hito 10. Los fallos deben ser visibles como `503` o `504`, no como un `200` que oculte la dependencia. No implementar reintentos ilimitados en la herramienta de evaluación.
