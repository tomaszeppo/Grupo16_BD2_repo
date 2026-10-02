# Memoria, evicción y escalabilidad

## Política

El Compose configura:

```text
maxmemory 128mb
maxmemory-policy volatile-lru
```

Se elige `volatile-lru` porque el conjunto de datos del módulo es temporal: sesiones, caché, ranking, contador y claves de demostración tienen TTL. Bajo presión de memoria, Redis puede eliminar claves que ya tienen expiración; las claves sin TTL no son candidatas de esta política.

La elección se apoya en una idea central del hito: **el TTL y la evicción resuelven problemas distintos**.

- TTL: cuánto tiempo debe vivir un dato desde el punto de vista del negocio.
- Evicción: qué puede sacrificarse cuando la RAM disponible se agota.

## Persistencia local

Además de RAM, el contenedor usa AOF (`appendonly yes`, `appendfsync everysec`) y monta `/data` sobre `~/docker/data/redis`. Esto permite reiniciar el entorno sin perder automáticamente el contenido que aún sea válido según su TTL.

La persistencia de Redis no cambia la clasificación funcional de una caché: una copia derivada sigue siendo reconstruible y no reemplaza la fuente de verdad.

## Límite de 128 MB

El límite es deliberadamente pequeño y adecuado a una práctica local. No representa el tamaño necesario para el escenario completo del Fixture 2030 con 2–3 millones de usuarios simultáneos.

Antes de una instancia productiva habría que medir el tamaño real de las sesiones, overhead de Redis, tasa de crecimiento, concurrencia y patrón de acceso; luego dimensionar memoria y nodos.

## Escalabilidad

Este hito usa **un único nodo**. No se presenta como alta disponibilidad.

### Primary + replicas

Permite mantener copias y disponer de recuperación/lecturas adicionales, pero las réplicas pueden estar temporalmente retrasadas.

### Sentinel

Coordina monitorización y failover de una topología primary/replica.

### Redis Cluster

Distribuye claves entre slots y permite sumar nodos para capacidad horizontal. Si el diseño futuro necesita operaciones atómicas multi-clave, deberá analizarse que las claves estén en el mismo slot; el laboratorio local no necesita esa complejidad.

## Inspección segura

La métrica usa `SCAN` con cursor y lotes. `KEYS *` no se utiliza como mecanismo normal de medición porque recorre todas las claves antes de responder y no es apropiado para un servidor con tráfico alto.
