# Hito 7 — Redis: Caché de usuarios y sesiones — Fixture 2030

**Asignatura:** Ingeniería de Datos II  
**Grupo:** 16  
**Tecnología:** Redis  
**Entorno:** Docker Compose + `redis:latest`  
**Alcance:** sesiones, caché de consultas frecuentes, ranking temporal, concurrencia y métricas.

## 1. Qué resuelve este módulo

Este módulo implementa el hito 7 sin reemplazar los módulos de persistencia anteriores. Redis se usa para estado temporal y copias de acceso rápido que pueden reconstruirse. En la arquitectura anterior, MongoDB conserva los datos estáticos/finalizados y Neo4j mantiene las relaciones de usuarios, grupos y predicciones; este módulo agrega la capa de sesión/caché pedida para el hito.

La caché de ejemplo es `f2030:cache:partido:P001:resumen`. Se considera una **copia derivada** de una respuesta obtenida desde la fuente de verdad externa (MongoDB en el diseño del Fixture). No se usa esa clave como fuente autoritativa del partido.

## 2. Requisitos principales cubiertos

- **RF1:** Compose, `redis:latest`, healthcheck, `redis-cli`, persistencia local.
- **RF2:** patrones de acceso documentados antes del modelo de claves.
- **RF3:** crear, recuperar, actualizar y finalizar sesiones.
- **RF4:** TTL de inactividad de 30 minutos con renovación explícita.
- **RF5:** sesión como Hash con `session_id`, `usuario_id`, estado, fechas, rol y contadores.
- **RF6:** caché Cache-Aside de un dato frecuente del Fixture.
- **RF7:** cache hit, cache miss, carga desde fuente de verdad y `DEL` por invalidación.
- **RF8:** contador concurrente con `INCRBY`, que es atómico dentro de Redis.
- **RF9:** ranking temporal con Sorted Set.
- **RF10:** `maxmemory 128mb` + `volatile-lru` y explicación de TTL vs. evicción.
- **RF11:** carga reproducible e idempotente sobre el namespace `f2030:*`.
- **RF12:** scripts de medición con método, entorno y resultados generados localmente.
- **RF13:** captura de `PING`, versión, TTL, `INFO`, memoria, hits/misses y resultados de concurrencia.

## 3. Estructura

```text
fixture2030-redis/
├── docker-compose.yml
├── README.md
├── .gitignore
├── datos/
│   └── demo_mongo_response_P001.json
├── scripts/
│   ├── inicializacion.redis
│   ├── carga_muestra.redis
│   ├── sesiones.redis
│   ├── cache.redis
│   ├── concurrencia.redis
│   ├── metricas.redis
│   ├── limpieza.redis
│   ├── limpieza.sh
│   ├── run_all.sh
│   ├── prueba_concurrencia.sh
│   ├── medir.sh
│   └── capturar_evidencia.sh
└── docs/
    ├── patrones_de_acceso.md
    ├── modelo_clave_valor.md
    ├── ciclo_de_vida_e_invalidacion.md
    ├── memoria_y_escalabilidad.md
    ├── pruebas_y_evidencia.md
    ├── matriz_cumplimiento.md
    ├── coherencia_con_tpo.md
    └── evidencia/
        └── README.md
```

## 4. Inicio del ambiente

Desde esta carpeta:

```bash
mkdir -p ~/docker/data/redis
docker compose up -d
docker compose ps
```

Verificación del servidor:

```bash
docker compose exec -T redis redis-cli PING
docker compose exec -T redis redis-cli INFO server | grep -E 'redis_version|process_id|uptime_in_seconds'
```

El resultado de `PING` debe ser `PONG`.

Abrir una consola interactiva:

```bash
docker compose exec redis redis-cli
```

La persistencia queda montada en `~/docker/data/redis`. `docker compose stop`, `docker compose restart` y `docker compose down` no borran ese directorio.

## 5. Ejecución reproducible

Los scripts `.redis` se pueden ejecutar con `redis-cli` desde el contenedor:

```bash
docker compose exec -T redis redis-cli < scripts/inicializacion.redis
docker compose exec -T redis redis-cli < scripts/carga_muestra.redis
docker compose exec -T redis redis-cli < scripts/sesiones.redis
docker compose exec -T redis redis-cli < scripts/cache.redis
docker compose exec -T redis redis-cli < scripts/concurrencia.redis
docker compose exec -T redis redis-cli < scripts/metricas.redis
```

O todo junto:

```bash
bash scripts/run_all.sh
```

La carga es deliberadamente reproducible: las claves de demostración se eliminan/recrean o se sobrescriben, y los Sorted Sets/contadores se reinician con valores conocidos.

## 6. Prueba de concurrencia real

```bash
bash scripts/prueba_concurrencia.sh
```

La prueba crea un contador en cero y ejecuta 10 workers en paralelo; cada worker envía 100 `INCRBY 1`. Al finalizar compara el valor observado con el esperado de 1000.

## 7. Medición

```bash
bash scripts/medir.sh
```

El script registra el entorno, versión, un benchmark acotado, una microprueba de hit/miss, memoria usada y política de evicción. Sus números solo describen el nodo local de esa ejecución.

## 8. Evidencia verificable

```bash
bash scripts/capturar_evidencia.sh
```

Se genera un archivo con marca temporal dentro de `docs/evidencia/` y se registran los comandos y salidas relevantes. Las evidencias reales deben capturarse ejecutando los scripts en el entorno local del grupo.

## 9. Reinicio y borrado total

Reinicio conservando datos:

```bash
docker compose restart
```

Detener y volver a iniciar:

```bash
docker compose down
docker compose up -d
```

Para una práctica completamente limpia, y **solo** con esa intención:

```bash
docker compose down
rm -rf ~/docker/data/redis/*
docker compose up -d
```

## 10. Nodo único vs. despliegue distribuido

Este repositorio usa un único nodo Redis porque así lo exige el laboratorio. No es una topología de alta disponibilidad.

- **Primary + replicas:** agrega copias para lectura/recuperación; puede existir atraso entre réplicas.
- **Sentinel:** agrega monitorización y failover de una topología primary/replica.
- **Redis Cluster:** distribuye claves entre slots y permite escalar capacidad horizontalmente; operaciones multi-clave deben diseñarse teniendo en cuenta el slot.

El módulo local no prueba failover, replicación real, distribución geográfica ni consistencia entre réplicas.

## 11. Seguridad local

No se usan credenciales reales, tokens reales ni secretos en los scripts. Los identificadores de usuario y valores de sesión son datos sintéticos de demostración.
