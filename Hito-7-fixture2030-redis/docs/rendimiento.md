# Rendimiento — Caché de usuarios y sesiones (Hito 7)

RF12 y RF13 piden registrar una medición con método, ambiente y resultado. Todas las salidas
completas están en `docs/evidencia/`.

## Ambiente de la corrida

| Campo | Valor |
| :--- | :--- |
| Fecha | 09/10/2026 |
| Redis | 8.10.2 (imagen `redis:latest`), un solo nodo |
| Configuración | `appendonly yes`, `maxmemory 256mb`, `maxmemory-policy volatile-lru` |
| Recursos de Docker Desktop | 12 CPU, 15,5 GB de RAM (WSL2) |
| Cliente | Contenedor `python:3.11-slim` en la misma red del compose, driver `redis` de Python |

## Concurrencia (RF8)

`scripts/prueba_concurrencia.py`: 8 procesos en paralelo, 5.000 repeticiones cada uno, sobre las
mismas claves (`07_prueba_concurrencia.txt`).

| Caso | Esperado | Obtenido |
| :--- | ---: | ---: |
| `INCRBY` sobre el contador de visitas | 40.000 | 40.000 |
| `ZINCRBY` sobre el score de un mismo usuario | 120.000,0400000 | 120.000,0399999 |
| Para comparar: `GET` + suma en el programa + `SET` | 40.000 | 7.996 (se perdieron 32.004 sumas) |

La diferencia en el último decimal del score es el redondeo propio de los números con coma
flotante; no se perdió ninguna suma. El caso no atómico muestra por qué se usa `INCRBY` y
`ZINCRBY` en lugar de leer y escribir desde la aplicación.

## Hit rate (RF13)

Con `INFO stats`, antes y después de 1.000 lecturas de caché de equipo (`08_hit_rate.txt`):

| | keyspace_hits | keyspace_misses |
| :--- | ---: | ---: |
| Antes | 40.824 | 328 |
| Después | 41.524 | 628 |
| Diferencia | 700 | 300 |

Hit rate de la microprueba: 70,0 %. Es por construcción: 7 de cada 10 lecturas son de equipos
cacheados y 3 de equipos que no lo están. Sirve para mostrar el método, no para predecir un
valor real.

## Operaciones por segundo (RF12)

`scripts/prueba_rendimiento.py --operaciones 10000` (`09_rendimiento.txt`):

| Operación | Tiempo | Operaciones por segundo |
| :--- | ---: | ---: |
| `ZINCRBY` (actualizar el ranking) | 16,02 s | 624 |
| `GET` (leer la caché) | 5,74 s | 1.742 |

## Limitaciones

- Estas cifras no son la capacidad de Redis. El cliente manda un comando, espera la respuesta y
  recién manda el siguiente, desde un solo proceso de Python y a través de la red de Docker
  Desktop: lo que se mide es sobre todo la latencia de cada ida y vuelta. Un servidor Redis
  atiende cientos de miles de operaciones por segundo con varios clientes en paralelo.
- La prueba de concurrencia tardó 68 s para 80.000 operaciones por el mismo motivo, y porque
  quedaban otras tareas corriendo en la máquina.
- Es un único nodo, sin réplicas. `ZINCRBY` fue más lento que `GET` porque modifica un Sorted
  Set y, con `appendonly yes`, cada escritura se anota en el archivo de persistencia.
