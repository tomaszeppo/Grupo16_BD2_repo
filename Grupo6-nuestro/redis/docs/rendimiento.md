# Rendimiento — Caché de usuarios y sesiones (Hito 7)

No está en la estructura mínima que lista la consigna, pero RF12 y RF13
piden registrar una medición con método, entorno y resultado — así que
tiene su propio documento en vez de mezclarse con las decisiones de diseño.

## Lo que ya se validó (lógica, sin Redis real de por medio)

El script de actualización del ranking (`scripts/actualizar_ranking.lua`) y
el patrón completo de `carga_muestra.redis` se probaron contra un Redis
simulado en memoria (no contra el contenedor real), para confirmar que la
lógica de atomicidad y de desempate funciona antes de medir cualquier
tiempo. Eso ya está documentado en `ciclo_de_vida_e_invalidacion.md` — acá
no se repite, porque **validar lógica no es lo mismo que medir rendimiento**:
un Redis en memoria simulado en Python no tiene ninguna relación con la
tasa de operaciones por segundo que daría el servidor real.

## Lo que falta medir (esto requiere Redis real corriendo)

```
pip install redis
python3 scripts/prueba_rendimiento.py --operaciones 10000
```

Mide dos cosas por separado, porque tienen patrones de costo distintos:

1. **Actualización atómica del ranking** (`EVALSHA` del script de
   `concurrencia.redis`) — la operación de escritura más compleja del
   módulo, la que más importa que no se degrade bajo carga.
2. **Lectura de caché** (`GET`) — la operación más simple y más frecuente
   de todo el módulo, para tener un punto de comparación.

## Plantilla para completar con el resultado real

| Campo | Valor |
| :--- | :--- |
| Fecha de ejecución | _completar_ |
| Versión de Redis (`INFO server`) | _completar_ |
| Recursos asignados a Docker Desktop (CPU / RAM) | _completar_ |
| Operaciones por prueba | _completar_ |
| Tasa — `EVALSHA` ranking (ops/seg) | _completar_ |
| Tasa — `GET` caché (ops/seg) | _completar_ |
| ¿`GET` fue notablemente más rápido que `EVALSHA`? ¿Por qué tendría sentido que lo sea? | _completar_ |

La consigna es explícita: no importa si la cifra queda lejos de algún
número ideal — lo que se evalúa es el método y el análisis. Completar
además:

- Qué se observó como límite (CPU del contenedor, latencia de red local,
  límite de conexiones).
- Si la tasa de `EVALSHA` se degrada con el tamaño del ranking (probar con
  un ranking de 100 usuarios vs. uno de 100.000, si da el tiempo).
