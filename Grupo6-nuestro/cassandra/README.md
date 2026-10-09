# Fixture 2030 — Comentarios Masivos (Hito 6)

Módulo de comentarios de partidos del Fixture 2030, sobre Apache Cassandra.
Diseñado por patrones de acceso, no por traducción de un modelo relacional
— el detalle está en `docs/patrones_de_acceso.md`, `docs/modelo_tabular.md`
y `docs/decisiones_de_particionamiento.md`.

## Qué incluye

```
fixture2030-cassandra/
├── docker-compose.yml          Ambiente Cassandra (cassandra:latest)
├── scripts/
│   ├── esquema.cql               Keyspace + las 3 tablas
│   ├── carga_muestra.cql         40 comentarios de ejemplo (5 partidos)
│   ├── crud.cql                  Create, read, update, delete
│   ├── consultas.cql             Las 4 consultas de lectura del módulo
│   ├── generar_carga_masiva.py   Genera CSV para >1.000.000 de comentarios
│   └── prueba_rendimiento.py     Mide escrituras/seg contra el contenedor
├── data/                        CSV generados (no se versiona el contenido pesado)
├── docs/
│   ├── patrones_de_acceso.md     Qué consultas motivan el diseño
│   ├── modelo_tabular.md         Tablas, claves, cardinalidades
│   ├── decisiones_de_particionamiento.md   Por qué el bucket, por qué la tabla duplicada
│   ├── rendimiento.md            Resultado de la prueba de escritura
│   └── evidencia/                Capturas de carga, consultas y rendimiento
└── README.md
```

## Cómo levantarlo

Necesitás Docker Desktop corriendo.

1. Crear la carpeta de persistencia en el host (la consigna pide esta ruta
   puntual, no un volumen nombrado de Docker):

   ```
   mkdir -p ~/docker/data/cassandra
   ```

   En Windows con Docker Desktop, `~` se resuelve contra el usuario dentro
   del backend WSL2. Si da error de permisos o de ruta, crear la carpeta a
   mano y, si hace falta, reemplazar `~/docker/data/cassandra` en
   `docker-compose.yml` por una ruta absoluta de Windows (por ejemplo
   `C:/docker/data/cassandra`).

2. Levantar el contenedor:

   ```
   docker compose up -d
   docker compose ps
   ```

   Cassandra tarda un rato en estar realmente lista para aceptar conexiones
   CQL (más que Mongo o Neo4j) — el healthcheck del `docker-compose.yml` lo
   contempla, pero puede tomar 30-60 segundos igual.

3. Verificar que levantó bien y registrar la versión real (RNF9, porque se
   usa la etiqueta `latest`):

   ```
   docker exec -it fixture2030-cassandra cqlsh -e "SHOW VERSION;"
   ```

## Cómo cargar y probar

Todo se corre con `cqlsh` dentro del contenedor, apuntando a los scripts
montados en `/scripts` (ver `volumes` en `docker-compose.yml`):

```
docker exec -it fixture2030-cassandra cqlsh -f /scripts/esquema.cql
docker exec -it fixture2030-cassandra cqlsh -f /scripts/carga_muestra.cql
docker exec -it fixture2030-cassandra cqlsh -f /scripts/consultas.cql
```

Para `crud.cql`, mejor a mano y no con `-f`: tiene un `<comentario_id>` que
hay que reemplazar por un valor real (ver el comentario dentro del archivo).

Verificar la carga de muestra:

```
docker exec -it fixture2030-cassandra cqlsh -e "SELECT COUNT(*) FROM fixture2030.comentarios_por_partido;"
```

Esperado: 40.

## Volumen masivo (RF11)

```
cd scripts
python3 generar_carga_masiva.py --target-rows 1200000 --output-dir ../data
```

Genera los CSV en `data/` (no se suben al repositorio por el peso — del
orden de 280MB para 1,2M de filas) y al final imprime los tres comandos
`COPY ... FROM` exactos para cargarlos, listos para copiar y pegar, por
ejemplo:

```
docker exec fixture2030-cassandra cqlsh -e "COPY fixture2030.comentarios_por_partido (...) FROM '/data/comentarios_por_partido.csv' WITH HEADER=true;"
```

(`/data` adentro del contenedor apunta a la carpeta `data/` del proyecto,
por el montaje del `docker-compose.yml`, por eso hay que generar los CSV
justamente ahí).

## Prueba de rendimiento (RF12)

El driver de Python para Cassandra no funciona con Python 3.12 o más nuevo
en Windows (se quitó el módulo `asyncore` que usaba y no hay alternativa
compilada para Windows). Para no depender de la versión de Python de cada
uno, lo más simple es correr la prueba desde un contenedor de Python 3.11
conectado a la misma red del `docker-compose.yml`:

```
docker run --rm --network fixture2030-cassandra_default -v "$(pwd)/scripts:/scripts:ro" python:3.11-slim sh -c "pip install -q cassandra-driver && python /scripts/prueba_rendimiento.py --host cassandra --rows 50000 --concurrencia 100"
```

(En PowerShell, cambiar `$(pwd)` por `${PWD}`; en Git Bash anteponer
`MSYS_NO_PATHCONV=1` para que no reescriba la ruta `/scripts`.)

Si tienen Python 3.11 o anterior instalado, también se puede directo:

```
pip install cassandra-driver
python3 scripts/prueba_rendimiento.py --rows 50000 --concurrencia 100
```

El resultado hay que volcarlo a mano en `docs/rendimiento.md` — ese
documento tiene la plantilla y también la alternativa con `cassandra-stress`
si prefieren no usar el driver de Python.

## Nodo único vs. despliegue real

Este ambiente es un solo nodo Cassandra, pensado para desarrollo y
aprendizaje. No representa una topología de alta disponibilidad: no hay
réplicas, no hay múltiples datacenters, y `SimpleStrategy` con factor de
replicación 1 significa que la caída de este único nodo deja el módulo sin
servicio. Un despliegue real usaría `NetworkTopologyStrategy` con réplicas
por región, en línea con el diseño distribuido del Hito 3.

## Variables de entorno

Este módulo no define credenciales propias: el ambiente de laboratorio usa
el autenticador por defecto de Cassandra (sin usuario/contraseña), lo cual
está bien para desarrollo local pero no debe usarse así en producción — se
documenta como configuración de desarrollo (RNF8), no como algo a imitar en
un ambiente real.
