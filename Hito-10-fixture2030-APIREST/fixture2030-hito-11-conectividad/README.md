# Hito 11 — Evaluación de conectividad · Fixture Mundial 2030

Este hito se integra al proyecto del Hito 10 sin reemplazar su API REST. Implementa una secuencia repetible para diagnosticar las seis dependencias que utiliza la aplicación: MongoDB, Neo4j, Cassandra, Redis, InfluxDB 3 Core e InterSystems IRIS.

## Qué cubre

- Mapa de dependencias, topología y diferencia entre host y red Docker Compose.
- Verificación de resolución de nombres y TCP desde la notebook; cuando está disponible, también desde el contenedor `api`.
- Pruebas de protocolo, autenticación/contexto y lectura mínima a través de los mismos drivers que usa la API; InfluxDB incluye además `/health` HTTP y una consulta temporal para diferenciar autorización de rechazo de database/tabla/consulta sin mostrar el cuerpo ni el token.
- Pruebas HTTP seguras de rutas representativas, clasificación de códigos HTTP, `X-Request-ID`, duración y estado de `/health`.
- Matriz por dependencia, diagnóstico y documentación del escenario reversible de caída de Redis.
- Evidencia histórica del Hito 10, identificada por su fecha de ejecución. Las ejecuciones del Hito 11 actualizan los tres archivos `docs/evidencia/resultados_*.txt`.

## Requisitos

1. Bash en macOS/Linux o Git Bash/WSL en Windows.
2. Python 3.12+ para la prueba con drivers cuando se ejecute localmente; instalar en el entorno virtual raíz `pip install -r requirements.txt -r requirements-drivers.txt`.
3. Para aprovechar el entorno integrado, Docker Desktop y Docker Compose v2, con el stack del Hito 10 disponible.
4. `curl` para las pruebas de API. La prueba TCP está implementada en Python y no depende de `nc`. Para Redis registra `EXISTS` y `TTL` (`-2` = clave ausente en el momento, `-1` = sin expiración, valor no negativo = segundos restantes); una clave ausente no se interpreta como caída del motor.

## Preparación

Ejecutar desde la raíz del proyecto del Hito 10:

```bash
cp .env.example .env
# Editar .env local y completar las contraseñas y el token según el README raíz.
bash scripts/levantar_servicios.sh
bash scripts/iniciar_api.sh
```

No copiar contraseñas ni tokens a esta carpeta, GitHub, capturas o logs. La carpeta `config/` contiene únicamente configuración de ejemplo sin secretos; el script lee el `.env` local del Hito 10 sin imprimir sus valores.

## Ejecución

Desde la raíz del proyecto Hito 10:

```bash
bash fixture2030-hito-11-conectividad/scripts/evaluar_conectividad.sh todo
bash fixture2030-hito-11-conectividad/scripts/evaluar_conectividad.sh tcp
bash fixture2030-hito-11-conectividad/scripts/evaluar_conectividad.sh native
bash fixture2030-hito-11-conectividad/scripts/evaluar_conectividad.sh api
bash fixture2030-hito-11-conectividad/scripts/evaluar_conectividad.sh fallo-redis
```

| Modo | Qué hace | Archivos de resultado |
|---|---|---|
| `todo` | TCP, drivers/clientes y API | los tres `resultados_*.txt` |
| `tcp` | Host/puerto y resolución; también red interna si `api` está en Docker | `docs/evidencia/resultados_tcp.txt` |
| `native` | `ping` y lectura mínima por los drivers de la aplicación | `docs/evidencia/resultados_clientes.txt` |
| `api` | Rutas GET representativas, salud, ausencia, validación y correlación | `docs/evidencia/resultados_api.txt` |
| `fallo-redis` | Detiene Redis de forma temporal, verifica 503, lo restaura y comprueba recuperación | agrega el resultado de la falla a `resultados_api.txt` |

Los scripts no hacen `docker compose down -v`, no borran bases ni eliminan volúmenes. El modo `fallo-redis` detiene únicamente el servicio `redis` con `docker compose stop` y siempre intenta restaurarlo con `docker compose start`, incluso ante una interrupción del script. Ejecutarlo únicamente en el stack local de este proyecto; no usarlo contra un ambiente compartido.

### Interpretación de estados

- `OK`: esa prueba concreta terminó correctamente.
- `FAIL`: se ejecutó y falló; el informe incluye hipótesis y próximo paso.
- `SKIP`: no se ejecutó por falta de herramienta, configuración o contenedor. **No significa que el producto esté caído.**
- `UNKNOWN`: no hay evidencia suficiente para clasificar la dependencia.
- `DEGRADED`: la API responde, pero una o más dependencias fallan en el chequeo profundo.

Un `OK` TCP solo acredita un listener accesible. El `ping` del driver comprueba la sesión/protocolo. La lectura mínima comprueba el contexto y operación usados. Ninguna de estas pruebas demuestra rendimiento de carga masiva.

## Cómo leer resultados

1. Ver `docs/evidencia/resultados_tcp.txt` para host, resolución, puerto y origen de la prueba.
2. Ver `docs/evidencia/resultados_clientes.txt` para protocolo, autenticación/contexto y lectura de control por producto.
3. Ver `docs/evidencia/resultados_api.txt` para ruta, método, status, duración, `X-Request-ID` y resultado resumido.
4. Correlacionar cada request ID con los logs del contenedor (`docker compose --profile api logs --since 5m api`) o con la salida de consola si la API se ejecuta localmente.
5. Registrar cambios y completar la matriz `docs/matriz_de_conectividad.md` luego de ejecutar desde la notebook del equipo.

## Evidencia disponible y limitaciones

El Hito 10 ya contiene evidencia histórica real, fechada el 16/10/2026, de `/health` con seis fuentes en estado `ok`, lecturas por las rutas de los seis módulos y una caída controlada de Redis que generó `503 DEPENDENCIA_NO_DISPONIBLE`. Las rutas originales están en `../docs/evidencia/20261016_120555_endpoints.txt`, `../docs/evidencia/20261016_120557_dependencia_caida.txt` y `../docs/evidencia/20261016_120557_logs_api.txt`.

**Evidencia real de la notebook del equipo, 22/10/2026:** TCP terminó con 0 fallos desde la notebook y desde el contenedor API; las pruebas de clientes terminaron con 8 OK, 0 FAIL y 0 SKIP; la API terminó con 15 OK y 0 FAIL. La prueba controlada de Redis produjo 503 `DEPENDENCIA_NO_DISPONIBLE` durante la caída y confirmó la recuperación mediante `PONG` y `/health` 200. Los detalles y timestamps se encuentran en los archivos `docs/evidencia/resultados_*.txt`; la captura redactada de la caída debe conservarse en `docs/evidencia/capturas_redactadas/`.

El resultado 401 de InfluxDB corresponde únicamente a la prueba HTTP sin token. El health check autenticado y la consulta temporal fueron aceptados en la prueba de clientes. Estas verificaciones no miden capacidad de carga masiva.

## GitHub

Agregar esta carpeta al repositorio existente del equipo y registrar la evolución con un commit:

```bash
git add fixture2030-hito-11-conectividad README.md
git commit -m "Completa Hito 11: evaluación de conectividad"
git push
```

Antes de subir, verificar `git status --short` y confirmar que `.env`, tokens, passwords y capturas no redactadas estén fuera del commit.
