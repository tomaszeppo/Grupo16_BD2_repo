# Fixture 2030 — Módulo de Grafos (Hito 5)

Módulo de relaciones deportivas y de programación del Fixture 2030, sobre Neo4j.
Retoma los identificadores de equipos y jugadores del módulo documental
(Hito 4) sin conectarse técnicamente a esa base — el detalle está en
`docs/decisiones.md`, y el modelo completo (nodos, relaciones, propiedades)
en `docs/modelo_grafo.md`.

## Qué incluye

```
neo4j/
- docker-compose.yml          Ambiente Neo4j (neo4j:5)
- .env.example                Modelo del .env (el .env real no se versiona)
- queries/
    - estructura.cypher         Restricciones e indices
    - carga.cypher              64 equipos, 1536 jugadores, 10 sedes, 32 partidos, eventos de muestra
    - verificar_carga.cypher    Conteos de nodos y relaciones
    - crud.cypher               Create, read, update, delete (con lectura antes y despues)
    - consultas_grafo.cypher    Consultas con patrones + analisis de camino
- docs/
    - modelo_grafo.md           Nodos, relaciones, cardinalidades, indices
    - decisiones.md             Por que el modelo quedo asi
    - evidencia/                Salidas reales de consola (con fecha y version)
- README.md
```

El hito se concentra en fixture, partidos, eventos y entidades deportivas. Usuarios, grupos y predicciones quedan para su etapa y no tienen nodos ni consultas en este módulo.

No hay carpeta `import/`: la consigna la lista como parte de la estructura de referencia, pero en este proyecto toda la carga se hace con Cypher puro (`carga.cypher`), sin archivos CSV ni de importación. La consigna aclara que "los nombres de archivos y carpetas pueden variar" mientras el contenido esté, así que se optó por el camino más simple.

## Cómo levantarlo

Necesitás Docker Desktop corriendo.

1. En esta carpeta, crear un archivo `.env` tomando `.env.example` como base:

   ```
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=elegir-una-clave
   ```

   No se versiona y el `docker-compose.yml` no trae valores por defecto: sin
   `.env` no levanta. La clave tiene que tener al menos 8 caracteres.

2. Levantar el contenedor y esperar a que figure como `healthy`:

   ```
   docker compose up -d
   docker compose ps
   ```

3. Abrir Neo4j Browser en `http://localhost:7474` y conectarse con el usuario y
   la contraseña del `.env`.

## Cómo cargar los datos

La carpeta `queries/` está montada en `/queries` dentro del contenedor, así que
los archivos se corren enteros con `cypher-shell`, que toma las credenciales del
propio contenedor (sirve igual en PowerShell, `cmd` y bash):

```
docker exec fixture2030-neo4j sh -c 'cypher-shell -u "${NEO4J_AUTH%%/*}" -p "${NEO4J_AUTH#*/}" -f /queries/estructura.cypher'
docker exec fixture2030-neo4j sh -c 'cypher-shell -u "${NEO4J_AUTH%%/*}" -p "${NEO4J_AUTH#*/}" -f /queries/carga.cypher'
docker exec fixture2030-neo4j sh -c 'cypher-shell -u "${NEO4J_AUTH%%/*}" -p "${NEO4J_AUTH#*/}" -f /queries/verificar_carga.cypher'
```

También se pueden pegar los mismos archivos en Neo4j Browser, en este orden:

1. `estructura.cypher`: restricciones e índices.
2. `carga.cypher`: equipos, jugadores, sedes, partidos y eventos de muestra.
   Se puede volver a correr sin duplicar nada. Los datos de referencia
   (equipos, jugadores, sedes) se reescriben con `SET`; la fase y la fecha de
   cada partido y el tipo y el minuto de cada evento se escriben con
   `ON CREATE SET`, así que recargar no pisa lo que se cambió con el CRUD.
3. `crud.cypher`: creación, lectura, actualización y eliminación, cada una con
   su lectura de verificación antes y después.
4. `consultas_grafo.cypher`: las consultas de dos y tres saltos y la de
   análisis de camino.

Después de cargar (y antes del CRUD), los conteos esperados son:

| Nodos | | Relaciones | |
| :--- | ---: | :--- | ---: |
| Equipo | 64 | PERTENECE_A | 1536 |
| Jugador | 1536 | DISPUTA | 64 |
| Sede | 10 | SE_JUEGA_EN | 32 |
| Partido | 32 | OCURRE_EN | 10 |
| Evento | 10 | PROTAGONISTA_DE | 10 |

## Evidencia (RF11)

Las salidas reales están en `docs/evidencia/`, cada una con fecha, versión de
Neo4j (5.26) y recursos de Docker:

- `01_estructura_constraints_indices.txt`: `SHOW CONSTRAINTS` y `SHOW INDEXES`.
- `02_carga_primera_vez.txt` y `03_carga_segunda_vez_idempotencia.txt`: mismos
  conteos de nodos y relaciones después de cargar una y dos veces.
- `04_crud.txt`: CRUD con lectura antes y después de cada operación.
- `05_recarga_no_pisa_crud.txt`: recarga luego del CRUD; el partido P-01 sigue
  en "Octavos de final" y el evento P-01-EV1 en el minuto 25.
- `06_consultas_grafo.txt`: consultas de dos y tres saltos y el camino ARG–SCO
  de RF9.

Las capturas de pantalla del Neo4j Browser (resultado del CRUD, consulta de camino, subgrafo e idempotencia) se sacan a mano; la lista y el orden estan en `docs/evidencia/CAPTURAS_PENDIENTES.md`.

## Variables de entorno

Las credenciales de Neo4j se definen por variable de entorno (`NEO4J_USER`,
`NEO4J_PASSWORD` en el `.env`) y no están escritas en el `docker-compose.yml`.
