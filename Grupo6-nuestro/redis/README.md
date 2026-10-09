# Fixture 2030 — Caché de Usuarios y Sesiones (Hito 7)

Módulo de sesiones, caché e información temporal del Fixture 2030, sobre Redis. Diseñado por patrones de acceso — el detalle está en `docs/patrones_de_acceso.md`, `docs/modelo_clave_valor.md` y `docs/ciclo_de_vida_e_invalidacion.md`.

Resuelve en particular el problema del cierre del ranking público: cuando termina el último partido y muchos usuarios quedan empatados en puntos, la tabla tiene que mostrar el orden correcto (con el desempate por antelación ya resuelto) sin ningún paso extra de recálculo. Ver `docs/ciclo_de_vida_e_invalidacion.md`, sección "El ranking público", para el detalle completo con un caso probado.

## Qué incluye

```
redis/
├── docker-compose.yml           Ambiente Redis (redis:latest)
├── scripts/
│   ├── inicializacion.redis       Verificaciones de arranque y configuración
│   ├── carga_muestra.redis        Sesiones, caché, ranking, likes y espectadores de ejemplo (se puede repetir)
│   ├── sesiones.redis             Ciclo de vida de una sesión (renovación en MULTI/EXEC)
│   ├── cache.redis                Patrón cache-aside: miss, hit, invalidación
│   ├── concurrencia.redis         Likes, límite de comentarios y actualización atómica del ranking
│   ├── actualizar_ranking.lua     El script de concurrencia.redis, legible, comentado
│   ├── espectadores.redis         Latidos y conteo de gente en vivo, con TTL de respaldo de 6 horas
│   ├── metricas.redis             Memoria, SCAN (no KEYS), ranking, TTL
│   ├── prueba_concurrencia.py     Varios procesos en paralelo sobre el mismo usuario y el mismo contador
│   ├── hit_rate.py                Hit rate con INFO stats antes y después de una microprueba
│   └── prueba_rendimiento.py      Mide EVALSHA (ranking) y GET (caché) reales
├── docs/
│   ├── patrones_de_acceso.md      Qué operaciones motivan el diseño
│   ├── modelo_clave_valor.md      Claves, estructuras, convención de nombres
│   ├── ciclo_de_vida_e_invalidacion.md   Sesiones, caché, ranking y consistencia por tipo de dato
│   ├── memoria_y_escalabilidad.md Política de memoria y qué claves tienen TTL
│   ├── rendimiento.md             Mediciones reales con ambiente y limitaciones
│   └── evidencia/                 Salidas de consola con fecha y versión
└── README.md
```

## Cómo levantarlo

Necesitás Docker Desktop corriendo.

1. Crear la carpeta de persistencia en el host (la misma convención que el
   Hito 6 con Cassandra):

   ```
   mkdir -p ~/docker/data/redis
   ```

   En Windows, Docker Desktop resuelve `~` contra la carpeta del usuario. Si da
   error, crear la carpeta a mano y reemplazar `~/docker/data/redis` en
   `docker-compose.yml` por una ruta absoluta (por ejemplo `C:/docker/data/redis`).

2. Levantar el contenedor:

   ```
   docker compose up -d
   docker compose ps
   ```

3. Verificar que levantó bien y registrar la versión real (se usa la etiqueta
   `latest`):

   ```
   docker exec fixture2030-redis redis-cli ping
   docker exec fixture2030-redis redis-cli info server
   ```

## Cómo correr los scripts

La carpeta `scripts/` está montada en `/scripts` dentro del contenedor. Cada
archivo `.redis` se corre entero así (funciona igual en PowerShell, `cmd` y bash,
sin usar el operador `<` del lado del anfitrión):

```
docker exec fixture2030-redis sh -c "redis-cli < /scripts/inicializacion.redis"
docker exec fixture2030-redis sh -c "redis-cli < /scripts/carga_muestra.redis"
docker exec fixture2030-redis sh -c "redis-cli < /scripts/sesiones.redis"
docker exec fixture2030-redis sh -c "redis-cli < /scripts/cache.redis"
docker exec fixture2030-redis sh -c "redis-cli < /scripts/concurrencia.redis"
docker exec fixture2030-redis sh -c "redis-cli < /scripts/espectadores.redis"
docker exec fixture2030-redis sh -c "redis-cli < /scripts/metricas.redis"
```

Para confirmar la carga de muestra:

```
docker exec fixture2030-redis redis-cli zrevrange ranking:publico 0 -1 withscores
```

Tiene que mostrar 15 usuarios, con los tres primeros empatados en 300 puntos pero
en el orden correcto por antelación (ver `docs/ciclo_de_vida_e_invalidacion.md`).

## Reiniciar o recargar

- **Reiniciar sin perder datos:** `docker compose restart`. Con `appendonly yes`,
  un reinicio pierde como mucho el último segundo de escrituras; los datos sin
  TTL sobreviven. Las sesiones y la caché, si ya vencieron, no vuelven.
- **Recargar la muestra:** `carga_muestra.redis` empieza borrando sus propias
  claves (una lista finita, nunca `KEYS`), así que se puede correr todas las
  veces que haga falta y da el mismo resultado: los puntos y la antelación del
  ranking no se suman de nuevo.
- **Empezar de cero:** `docker exec fixture2030-redis redis-cli FLUSHALL`.

## Pruebas con Python

Necesitan el driver (`pip install redis`) o un contenedor de Python en la red del
compose. Sin instalar nada en el anfitrión:

```
docker run --rm --network <proyecto>_default -v "${PWD}/scripts:/scripts:ro" python:3.11-slim sh -c "pip install -q redis && python /scripts/prueba_concurrencia.py --host redis --procesos 8 --repeticiones 5000"
```

- `prueba_concurrencia.py`: varios procesos ejecutan `EVALSHA` del script de
  ranking sobre el mismo usuario y `INCR` sobre el mismo contador de likes. Al
  final el total tiene que ser exactamente procesos × repeticiones × delta; si no,
  sale con error.
- `hit_rate.py`: toma `keyspace_hits` y `keyspace_misses` de `INFO stats` antes y
  después de una microprueba de lecturas de caché. Correrlo justo después de
  `carga_muestra.redis` (la caché de equipo vence a los 5 minutos).
- `prueba_rendimiento.py`: mide `EVALSHA` y `GET` por separado (RF12). El
  resultado y el ambiente están en `docs/rendimiento.md`.

(`<proyecto>` es el nombre de la carpeta del módulo en minúsculas; se ve con
`docker network ls`.)

## Nodo único vs. despliegue real

Este ambiente es un único nodo Redis, para desarrollo y aprendizaje. No hay
réplicas, no hay Sentinel para failover automático, y no hay Redis Cluster
para particionar los datos entre varios nodos — todo lo cual haría falta en
producción para sostener los 2-3 millones de usuarios simultáneos del
escenario del Fixture 2030 (ver `docs/memoria_y_escalabilidad.md`). Este
laboratorio no se presenta en ningún momento como una topología de alta
disponibilidad.

## Variables de entorno

Este módulo no define credenciales propias: el ambiente de laboratorio usa
Redis sin autenticación (`requirepass` sin configurar), documentado como
configuración de desarrollo (RNF7), no apta para un ambiente real.
