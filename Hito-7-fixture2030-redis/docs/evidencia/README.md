# Evidencia de ejecución

Esta carpeta está destinada a las salidas reales del laboratorio.

## Comando principal

```bash
bash scripts/capturar_evidencia.sh
```

## Qué debe quedar registrado

- fecha de ejecución;
- `redis_version` observado;
- estado del contenedor y `PING`;
- `INFO persistence`;
- `maxmemory` y `maxmemory-policy`;
- creación/lectura/renovación/cierre de sesiones;
- TTL observados;
- cache miss/hit/invalidation;
- ranking temporal;
- resultado de la prueba concurrente;
- `keyspace_hits`, `keyspace_misses`, `expired_keys`, `evicted_keys`;
- `used_memory`, `used_memory_peak`, `maxmemory`;
- benchmark acotado y su método.

## Estado de esta entrega

La estructura y los scripts están preparados para generar la evidencia. Las cifras de rendimiento/evicción deben generarse en la máquina donde el grupo ejecute Docker; no se inventan valores en la documentación.
