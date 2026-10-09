Guardar en esta carpeta las capturas de pantalla o salidas de consola de:

1. `docker compose up -d` corriendo sin errores, y `docker ps` mostrando el
   contenedor `fixture2030-redis` con la imagen `redis:latest`.
2. Resultado de `scripts/inicializacion.redis` -- en particular la linea de
   `INFO server` con la version real (RNF10, se usa la etiqueta latest) y
   la fecha en que se corrio.
3. Resultado de `scripts/carga_muestra.redis`: el `ZREVRANGE` final mostrando
   el ranking ya ordenado y desempatado (el caso de los tres usuarios
   empatados en 300 puntos).
4. Resultado de `scripts/sesiones.redis`: el `TTL` de una sesion recien
   creada, y la confirmacion de que se renueva al "tocarla" de nuevo.
5. Resultado de `scripts/cache.redis`: el cache miss (nil) y despues el
   cache hit tras el SET.
6. Resultado de `scripts/concurrencia.redis`: el EVAL del script de ranking
   y el ZREVRANGE posterior.
7. Resultado de `scripts/metricas.redis`: en particular `INFO memory` (para
   contrastar contra el maxmemory de 256mb) y el `SCAN` de sesiones (no
   KEYS, ver RNF8).
8. (Opcional pero recomendado) Repetir `scripts/carga_muestra.redis` una
   segunda vez y mostrar que el ranking no queda duplicado ni roto -- al
   usar HINCRBY/HINCRBYFLOAT, los puntos y la antelacion se SUMAN de nuevo
   en cada corrida (no es una carga idempotente en el sentido estricto,
   es un acumulador); documentar esto si se repite la carga a proposito.

Se puede borrar este archivo de texto una vez que las capturas esten cargadas.
