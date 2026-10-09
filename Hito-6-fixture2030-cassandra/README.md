# Fixture 2030 — Comentarios Masivos (Hito 6)

Módulo de comentarios de partidos del Fixture 2030, sobre Apache Cassandra.
Diseñado por patrones de acceso, no por traducción de un modelo relacional.
El detalle está en `docs/patrones_de_acceso.md`, `docs/modelo_tabular.md` y
`docs/decisiones_de_particionamiento.md`.

## Qué incluye

```
Hito-6-fixture2030-cassandra/
├── docker-compose.yml          Ambiente Cassandra (cassandra:latest)
├── scripts/
│   ├── esquema.cql               Keyspace + las 3 tablas
│   ├── carga_muestra.cql         40 comentarios de ejemplo (5 partidos)
│   ├── crud.cql                  Create, read, update, delete sobre las dos tablas (se corre sin editar)
│   ├── consultas.cql             Las 4 consultas de lectura del módulo
│   ├── generar_carga_masiva.py   Genera los CSV de 1,2 millones de comentarios (semilla fija)
│   ├── validar_carga_masiva.py   Compara Cassandra con el conteo esperado, partición por partición
│   ├── cargar_y_validar.sh       Vacía, carga con COPY, valida; con "dos" repite la carga y valida de nuevo
│   └── prueba_rendimiento.py     Mide escrituras por segundo contra el contenedor
├── data/                        CSV generados (no se versionan, salvo partidos_referencia.csv)
├── docs/
│   ├── patrones_de_acceso.md     Qué consultas motivan el diseño
│   ├── modelo_tabular.md         Tablas, claves, cardinalidades
│   ├── decisiones_de_particionamiento.md   Por qué el bucket, por qué la tabla duplicada
│   ├── rendimiento.md            Carga masiva y medición de escrituras por segundo, con ambiente y limitaciones
│   └── evidencia/                Salidas de consola con fecha y versión
├── Docuemntación & Justificación (1).pdf    Documento de la primera entrega
├── EVIDENCIA.pdf                            Capturas de la primera entrega
└── README.md
```

Los dos PDF son de la primera entrega. La evidencia vigente, generada con los
scripts de esta carpeta, está en `docs/evidencia/`.

## Cómo levantarlo

Necesitás Docker Desktop corriendo.

1. Crear la carpeta de persistencia en el host. La consigna pide esta ruta, no
   un volumen nombrado de Docker:

   ```
   mkdir -p ~/docker/data/cassandra
   ```

   En Windows, Docker Desktop resuelve `~` contra la carpeta del usuario
   (`C:\Users\<usuario>\docker\data\cassandra`); se comprobó que Cassandra crea ahí
   `commitlog`, `data`, `hints` y `saved_caches`. Si diera error de permisos o de
   ruta, crear la carpeta a mano o poner una ruta absoluta en `docker-compose.yml`.

2. Levantar el contenedor y esperar a que figure como `healthy` (puede tardar
   uno o dos minutos):

   ```
   docker compose up -d
   docker compose ps
   ```

3. Registrar la versión real (la imagen usa la etiqueta `latest`):

   ```
   docker exec fixture2030-cassandra cqlsh -e "SHOW VERSION;"
   ```

## Cómo cargar y probar

La carpeta `scripts/` está montada en `/scripts` dentro del contenedor:

```
docker exec fixture2030-cassandra cqlsh -f /scripts/esquema.cql
docker exec fixture2030-cassandra cqlsh -f /scripts/carga_muestra.cql
docker exec fixture2030-cassandra cqlsh -f /scripts/consultas.cql
docker exec fixture2030-cassandra cqlsh -f /scripts/crud.cql
```

`carga_muestra.cql` usa identificadores fijos, así que se puede repetir sin
duplicar filas. `crud.cql` se corre de punta a punta sin editar nada: usa un
`comentario_id` fijo, trabaja sobre las dos tablas, muestra una lectura de
verificación antes y después de cada operación (incluido el `DELETE`) y deja las
tablas como estaban.

Contar la muestra (40 filas en cada tabla de comentarios):

```
docker exec fixture2030-cassandra cqlsh -e "SELECT COUNT(*) FROM fixture2030.comentarios_por_partido;"
```

## Volumen masivo (RF11)

La carga de muestra y la masiva usan las mismas tablas. La masiva empieza vaciándolas,
porque los conteos esperados cubren solo los datos generados.

1. Generar los CSV (semilla fija: dos corridas dan archivos idénticos, y el
   `comentario_id` sale de la hora del comentario y del número de fila, no de la
   hora de la corrida):

   ```
   cd scripts
   python generar_carga_masiva.py --target-rows 1200000 --output-dir ../data
   ```

   Escribe `comentarios_por_partido.csv`, `comentarios_por_usuario.csv`,
   `partidos_referencia.csv` y los conteos esperados por partición
   (`conteo_esperado_por_particion.csv` y `conteo_esperado_por_usuario.csv`).

2. Cargar con `COPY` y validar, dos veces seguidas (desde la carpeta del módulo,
   con bash; en Windows alcanza con Git Bash):

   ```
   bash scripts/cargar_y_validar.sh dos
   ```

   El script vacía las tablas, carga, valida, vuelve a cargar los mismos CSV sin
   vaciar y valida otra vez. La validación (`validar_carga_masiva.py`) hace un
   `SELECT COUNT(*)` acotado a cada partición: 416 consultas por partido y bucket y
   50.000 por usuario. Nunca cuenta la tabla completa. Como los identificadores son
   estables, la segunda carga sobrescribe las mismas filas y los totales no cambian.

   Los comandos `COPY` llevan `INGESTRATE=15000 AND MAXBATCHSIZE=10 AND
   NUMPROCESSES=3 AND MAXATTEMPTS=10`. Con los valores por defecto, un nodo único en
   Docker Desktop se satura (ver `docs/rendimiento.md`).

## Prueba de rendimiento (RF12)

El driver de Python para Cassandra no funciona con Python 3.12 o más nuevo en
Windows (se quitó el módulo `asyncore`). Para no depender de la versión de cada
equipo, se corre desde un contenedor de Python 3.11 en la red del compose. El nombre
de la red se ve con `docker network ls` (`<carpeta>_default`):

```
docker run --rm --network hito-6-fixture2030-cassandra_default -v "${PWD}/scripts:/scripts:ro" python:3.11-slim sh -c "pip install -q cassandra-driver && python /scripts/prueba_rendimiento.py --host cassandra --rows 200000 --concurrencia 100 --procesos 4"
```

(En Git Bash, anteponer `MSYS_NO_PATHCONV=1`.) La prueba escribe en un partido
ficticio, `P-PRUEBA`, y lo borra al terminar, así no altera los conteos de la carga
masiva. También se puede medir con `cassandra-stress`, que viene en la imagen:

```
docker exec fixture2030-cassandra /opt/cassandra/tools/bin/cassandra-stress write n=100000 -rate threads=50
```

Los resultados, el ambiente y las limitaciones están en `docs/rendimiento.md`.

## Nodo único vs. despliegue real

Este ambiente es un solo nodo Cassandra, pensado para desarrollo y aprendizaje.
No hay réplicas ni varios centros de datos, y `SimpleStrategy` con factor de
replicación 1 significa que la caída de este nodo deja el módulo sin servicio.
Un despliegue real usaría `NetworkTopologyStrategy` con réplicas por región, en
línea con el diseño distribuido del Hito 3.

## Variables de entorno

Este módulo no define credenciales: el ambiente de laboratorio usa el
autenticador por defecto de Cassandra (sin usuario ni contraseña). Es una
configuración de desarrollo, no apta para un ambiente real.
