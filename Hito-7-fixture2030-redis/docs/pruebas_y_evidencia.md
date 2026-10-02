# Pruebas y evidencia

## Evidencia esperada por requisito

| RF | Evidencia implementada |
|---|---|
| RF1 | `docker compose up -d`, `docker compose ps`, `PING`, `INFO server` |
| RF2 | `docs/patrones_de_acceso.md` |
| RF3 | `scripts/sesiones.redis`: crear, recuperar, actualizar y finalizar |
| RF4 | TTL 1800 s, renovación explícita y expiración nativa demostrada |
| RF5 | `HGETALL` de sesión con atributos temporales y de acceso |
| RF6 | `scripts/cache.redis`: cache hit de `f2030:cache:partido:P001:resumen` |
| RF7 | miss → fuente externa → SET+TTL, y `DEL` por invalidación |
| RF8 | `scripts/concurrencia.redis` + `scripts/prueba_concurrencia.sh` |
| RF9 | Sorted Set + `ZREVRANGE ... WITHSCORES` |
| RF10 | `CONFIG GET maxmemory` y `CONFIG GET maxmemory-policy`, más documentación |
| RF11 | claves sintéticas e idempotentes en `carga_muestra.redis` |
| RF12 | `scripts/medir.sh`, con benchmark y microprueba reproducible |
| RF13 | `scripts/capturar_evidencia.sh`, `INFO`, TTL, memoria, hits/misses, evictions |

## Prueba de caché

El script provoca `GET` sobre una clave inexistente y sobre una clave cargada. Para una medición formal se toman los valores de `INFO stats` antes y después y se calcula:

```text
tasa_hit = hits / (hits + misses) * 100
```

El resultado solo se considera válido para esa ejecución y ese entorno.

## Prueba de concurrencia

`prueba_concurrencia.sh` ejecuta múltiples workers del sistema operativo al mismo tiempo. Cada worker hace `INCRBY 1` sobre una misma clave. Se compara:

```text
esperado = workers × incrementos_por_worker
observado = GET clave
```

Un valor observado igual al esperado demuestra que no se perdieron incrementos en la prueba local.

## Limitaciones del laboratorio

Las cifras del benchmark y el tiempo de la prueba dependen del hardware, Docker, sistema operativo y carga de la máquina. No representan el rendimiento de una plataforma de 2–3 millones de usuarios.

Tampoco se prueban aquí réplicas, Sentinel, Cluster, red entre regiones ni una aplicación web real, porque el Hito 7 limita el alcance al módulo Redis local.

## Evidencia runtime

Los archivos de evidencia con resultados reales se generan al ejecutar `scripts/capturar_evidencia.sh` en una máquina que tenga Docker. No se incluyen números inventados en este repositorio.
