# Hito 8 — Series temporales de estadísticas en vivo 

**Alcance:** captura de estadísticas de partidos, actividad de usuarios, consultas temporales, agregaciones, cardinalidad, retención, carga por lotes y evidencia.

## 1. Qué resuelve este módulo

El módulo modela las estadísticas que cambian durante los partidos del Fixture 2030 y mantiene una segunda serie para la métrica de usuarios conectados. InfluxDB queda dedicado al componente temporal: registrar cómo evolucionan las medidas y permitir consultas por partido, equipo, sede, fuente y rango temporal.

La arquitectura anterior mantiene sus responsabilidades: Redis conserva el estado transitorio de los partidos, MongoDB la persistencia estática/finalizada, Cassandra los comentarios/logs de alto volumen, IRIS los grupos y puntajes e Neo4j las relaciones de usuarios, grupos y predicciones. InfluxDB agrega las métricas y estadísticas históricas temporales.

La selección es consistente con las decisiones anteriores del grupo, donde InfluxDB fue elegido para métricas históricas, usuarios conectados, eventos por minuto y evolución de estadísticas. El Hito 3 también contempla a InfluxDB como uno de los subsistemas sensibles por el crecimiento de escrituras.

## 2. Modelo implementado

### Tabla `estadisticas_partido`

Fenómeno: evolución de métricas deportivas de cada equipo durante cada partido.

**Tags (dimensiones indexables):**
- `partido_id`: M001–M127.
- `equipo_id`: código de selección, reutilizado desde los hitos previos.
- `sede`: una de 20 sedes sintéticas, acorde al inventario previo.
- `fuente`: fuente de observación de baja cardinalidad.
- `fase`: grupo, ronda_32, octavos, cuartos, semifinal, final.

**Fields (valores observados):**
- `posesion_pct` (float): porcentaje de posesión medido en el instante; se puede promediar o comparar.
- `pases_completados` (integer): pases completados dentro del intervalo de muestreo; se puede sumar en una ventana.
- `tiros` (integer): tiros registrados en el intervalo; se suma para obtener tiros de la ventana.
- `recuperaciones` (integer): recuperaciones registradas en el intervalo; se suma.
- `velocidad_kmh` (float): velocidad instantánea; se puede promediar o tomar máximo.

### Tabla `usuarios_conectados`

Fenómeno: evolución de usuarios activos por región durante un partido.

**Tags:** `partido_id`, `region`.  
**Field:** `usuarios_activos` (integer).

No se utiliza `usuario_id` como tag porque sería una dimensión de alta variación sin una necesidad de consulta que lo justifique; el objetivo es medir carga agregada por región.

## 3. Patrón de timestamps y precisión

La captura se modela a precisión de **segundos**. El generador sintético usa timestamps UTC de forma determinista y la carga declara `--precision second` / `precision=second`.

La precisión de segundos es suficiente para el objetivo de esta práctica: evolución de estadísticas y agregaciones por minuto. La métrica de usuarios también se genera a segundos para mantener un único criterio temporal en el módulo.

## 4. Objetivo de volumen 10M+

El generador define una estrategia reproducible de **10.160.000 puntos**:

`127 partidos × 2 equipos × 8 fuentes × 5.000 instantes = 10.160.000 puntos`

Las 8 fuentes son una dimensión acotada (`scouting`, `tracking`, `broadcast`, `telemetria`, `analitica`, `arbitraje`, `app`, `estadistica`). Cada punto contiene cinco medidas deportivas.

El laboratorio local por defecto carga **8 partidos = 640.000 puntos deportivos**, más la serie de usuarios conectados. Esto permite medir sobre un volumen razonable para una notebook y evita afirmar que se procesaron 10M puntos cuando no se ejecutaron. El mismo cargador acepta `--matches 127` para ejecutar el escenario completo de 10,16M puntos si el hardware disponible lo soporta.

## 5. Batching y concurrencia

La carga utiliza la API nativa `POST /api/v3/write_lp`, que es el endpoint recomendado para nuevas cargas de line protocol en InfluxDB 3 Core. Se usa batching y workers configurables.

Parámetros por defecto del laboratorio:
- 8 partidos.
- 80.000 puntos deportivos por partido (2 equipos × 8 fuentes × 5.000 instantes).
- lote de 2.000 puntos por request.
- 2 workers.
- timestamps generados de manera determinista.
- `accept_partial=false` para que una falla de un lote no se oculte como éxito parcial.
- reintentos limitados con backoff.

La segmentación por partido hace que cada worker trabaje sobre series separadas, evitando depender de un orden global único de timestamps. El modo de carga concurrente puede provocar que lotes de diferentes partidos lleguen en distinto orden, pero no intercalan series de un mismo partido entre workers distintos.

## 6. Retención y granularidad

Se crea la base `fixture2030_metrics` con una **retención de 90 días**. En InfluxDB 3 Core la retención de la base se define al crearla y luego es inmutable.

Política propuesta:
- durante 90 días: mantener puntos originales a precisión de segundos para análisis operativo y troubleshooting;
- para análisis de largo plazo: generar consultas/agregados de 5 minutos y, si el proyecto evoluciona a producción, conservar esa representación en una base histórica separada con mayor retención;
- no convertir medidas ni identificadores individuales en tags solo para facilitar consultas ocasionales.

La implementación aplica la parte obligatoria mediante la retención de la base y deja la granularidad histórica como estrategia documentada, sin fingir una política de downsampling automático que no fue ejecutada en el laboratorio.

## 7. Fuentes y coherencia con hitos anteriores

- **Redis:** estado actual / transitorio del partido y caché de acceso rápido.
- **MongoDB:** partidos finalizados y datos estáticos.
- **Cassandra:** comentarios y logs distribuidos por partido, país y ventana.
- **IRIS:** grupos, puntajes y composición.
- **Neo4j:** relaciones entre usuarios, grupos, predicciones y partidos.
- **InfluxDB:** evolución temporal de estadísticas y métricas históricas.

Los códigos de equipos y los identificadores de partidos siguen el criterio previo (`ARG`, `FRA`, `M001`, etc.) para conservar trazabilidad entre módulos.

## 8. Inicio

### Requisitos

- Docker Desktop funcionando.
- Docker Compose disponible.
- `curl` y Python 3 en el host.

### Persistencia

```bash
mkdir -p ~/docker/data/influxdb
```

Si aparece un error de permisos al crear el catálogo:

```bash
sudo chown -R "$(id -u):$(id -g)" ~/docker/data/influxdb
sudo chmod -R 777 ~/docker/data/influxdb
```

### Levantar InfluxDB

```bash
docker compose up -d
docker compose ps
```

Ver versión del servidor después de obtener el token:

```bash
bash scripts/inicializacion.sh
```

El script crea el token administrativo local la primera vez y lo guarda en `.secrets/influxdb_admin_token`, que está excluido por `.gitignore`.

## 9. Flujo recomendado para la entrega

### Paso 1 — inicialización

```bash
bash scripts/inicializacion.sh
```

Genera/recupera el token local, crea la base con 90 días de retención, crea las tablas y guarda evidencia de versión/health.

### Paso 2 — carga reproducible

Carga local recomendada:

```bash
python3 scripts/carga_lotes.py --matches 8 --batch-size 2000 --workers 2
```

Escenario completo de diseño (10.160.000 puntos deportivos):

```bash
python3 scripts/carga_lotes.py --matches 127 --batch-size 2000 --workers 2
```

La segunda opción puede ser muy exigente para una notebook; usarla solo si la medición local lo permite.

### Paso 3 — consultas temporales

```bash
bash scripts/consultas_temporales.sh
```

Resuelve:
- ventana temporal de un equipo en un partido;
- comparación entre los dos equipos;
- comparación entre fuentes;
- pico de usuarios por región.

### Paso 4 — agregaciones

```bash
bash scripts/agregaciones.sh
```

Resuelve agregación por equipo y agregación por ventana de 1 minuto con `DATE_BIN`.

### Paso 5 — validación

```bash
bash scripts/validacion.sh
```

Comprueba tablas, columnas, conteos, distribución y retención.

### Paso 6 — medición

```bash
python3 scripts/medir.py --matches 8 --batch-size 2000 --workers 2
```

La medición registra el método, el ambiente, la cantidad real cargada, el tiempo observado y la tasa calculada para esa ejecución. No se deben copiar esos números a mano a la documentación.

### Paso 7 — evidencia

```bash
bash scripts/capturar_evidencia.sh
```

Genera un archivo fechado en `docs/evidencia/` sin incluir el token.

## 10. Consultas principales

Las consultas se encuentran versionadas en:

- `scripts/q01_ventana.sql` … `q04_pico_usuarios.sql`
- `scripts/ag01_equipo.sql` y `ag02_por_minuto.sql`
- `scripts/validacion.sh`

Todos los ejemplos usan rangos temporales acotados y filtros por dimensiones antes de agregar.

## 11. Seguridad

El token administrativo se crea localmente y se guarda fuera del repositorio en `.secrets/influxdb_admin_token`. No se incluye en documentación, scripts versionados ni evidencia. El repositorio contiene únicamente identificadores y datos sintéticos.

## 12. Nodo local vs. escala futura

Este laboratorio utiliza un único nodo local. No demuestra tolerancia a fallos, distribución geográfica ni capacidad real de 10M+ puntos en producción.

Para una evolución del diseño se deberían revisar: número de writers, tamaño de lotes, presión de disco, concurrencia, cardinalidad, particionamiento, retención, consultas del dashboard y estrategia de réplica/observabilidad del despliegue elegido.

