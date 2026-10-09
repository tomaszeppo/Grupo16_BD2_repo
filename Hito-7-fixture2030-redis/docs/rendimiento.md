# Rendimiento — Caché de usuarios y sesiones (Hito 7)

RF12 y RF13 piden registrar una medición con método, ambiente y resultado. Este documento
separa lo ya ejecutado de lo pendiente; no hay cifras inventadas.

## Ambiente de la corrida

| Campo | Valor |
| :--- | :--- |
| Fecha | 09/10/2026 |
| Redis | 8.10.2 (imagen `redis:latest`), un solo nodo |
| Configuración | `appendonly yes`, `maxmemory 256mb`, `maxmemory-policy volatile-lru` |
| Recursos de Docker Desktop | 12 CPU, 15,5 GB de RAM (WSL2) |

## Ya ejecutado (salidas en `docs/evidencia/`)

| Qué | Resultado | Archivo |
| :--- | :--- | :--- |
| Carga de muestra dos veces | Mismo ranking, mismos puntos y mismas 47 claves | `02_carga_muestra_repetida.txt` |
| Sesiones con renovación en `MULTI/EXEC` | TTL 1800 s en la sesión y en el puntero, dos corridas iguales | `03_sesiones.txt` |
| Caché de equipo y de partido | Miss, hit e invalidación | `04_cache.txt` |
| Espectadores en vivo | 3 de 4 latidos dentro de la ventana de 30 s; TTL de respaldo de 21.600 s | `05_concurrencia_y_espectadores.txt` |
| Concurrencia real: 8 procesos × 5.000 repeticiones sobre el mismo usuario y el mismo contador | Puntos 120.000 (esperado 120.000), antelación 400.000 (400.000), likes 40.000 (40.000): no se perdió ninguna actualización | `07_prueba_concurrencia.txt` |
| Hit rate con `INFO stats` | Diferencia de 700 hits y 300 misses en 1.000 lecturas: 70,0 % | `08_hit_rate.txt` |

La prueba de concurrencia corrió con la máquina ocupada por otra tarea (una carga masiva de
Cassandra), así que el tiempo que informa (4.562 operaciones por segundo) no representa la
capacidad del servidor.

## Pendiente

Medición de operaciones por segundo con `scripts/prueba_rendimiento.py --operaciones 10000`
(`EVALSHA` del ranking y `GET` de caché por separado), con la máquina libre. Completar:

| Campo | Valor |
| :--- | :--- |
| Fecha de ejecución | _pendiente_ |
| Operaciones por prueba | _pendiente_ |
| `EVALSHA` ranking (ops/seg) | _pendiente_ |
| `GET` caché (ops/seg) | _pendiente_ |
| Límite observado (CPU del contenedor, cliente, red local) | _pendiente_ |
