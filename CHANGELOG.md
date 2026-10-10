# Changelog — correcciones de consistencia entre módulos

Registro de cambios hechos en la rama `correcciones` pensando en la futura integración de los 6 módulos de base de datos (Hitos 4 a 9) como un único sistema políglota. Mientras esa integración no empiece, este archivo documenta qué se corrigió para que el camino hacia ahí quede más corto, y qué queda pendiente.

## 2026-10-09 — `main` sumó su propio Hito 9, independiente del de `correcciones`

**Qué pasó:** llegó un commit nuevo a `origin/main` (`8bb723a "hito 9"`) con una carpeta **`Hito-9-fixture2030-iris-objetos/`** — no es la misma que `Hito-9-fixture2030-iris/` que ya existía en `correcciones`, es una implementación propia y paralela (otro namespace de clases, `Fixture.*` en vez de `Fixture2030.*`). No se tocó ni se mezcló con la de `correcciones`: cada rama conserva la suya.

**Hallazgo de consistencia (mismo patrón que el Hito 8):** el código de partido que genera `main` es un timestamp al vuelo (`H9-M-<horolog>`, ej. `H9-M-67852-73429`), no el `P-NN` que usan Neo4j, Cassandra, Redis e InfluxDB. Tampoco existe ningún campo que vincule un `Jugador` a su equipo. Como es contenido de `main` (el TP del otro grupo) y no de `correcciones`, no se corrigió — solo se documentó la comparación en `COMPARACION_main_vs_correcciones.md`.

**Qué se actualizó:**
- `COMPARACION_main_vs_correcciones.md`: sección del Hito 9 reescrita con la comparación completa entre las dos implementaciones.
- `esquema-main.html`: el motor IRIS pasó de "no existe en esta rama" a sus 6 entidades reales (Persona, Jugador, Arbitro, Tecnico, Partido, Evento), con nota explícita de que no comparte identificadores con el resto de los módulos (por eso no tiene ninguna línea de relación en el mapa).
- `esquema-correcciones.html` no cambió: sigue representando la implementación propia de `correcciones`, que no se vio afectada por este commit.

## 2026-10-09 — Unificar el formato de `partido_id` en InfluxDB (Hito 8)

**Qué estaba mal:** Neo4j, Cassandra, Redis e IRIS identifican los partidos como `P-01`, `P-02`, ... `P-NN`. InfluxDB generaba sus propios IDs como `M001`, `M002`, ... (`Hito-8-fixture2030-influxdb/lib/generador.py`, función `match_info`). El README de Hito 8 incluso afirmaba que esto "sigue el criterio previo... para conservar trazabilidad entre módulos", lo cual era incorrecto: con IDs distintos, no hay forma directa de cruzar las estadísticas de un partido en InfluxDB con el mismo partido en los demás sistemas.

**Qué se cambió:**
- `Hito-8-fixture2030-influxdb/lib/generador.py`: `match_id=f"M{idx:03d}"` → `match_id=f"P-{idx:02d}"`.
- Reemplazado `M001` por `P-01` en todos los scripts de consulta/validación que usaban ese valor como ejemplo: `scripts/ag01_equipo.sql`, `ag02_por_minuto.sql`, `q01_ventana.sql`, `q02_comparacion_equipos.sql`, `q03_comparacion_fuentes.sql`, `q04_pico_usuarios.sql`, `validacion.sql`, `validacion.sh`, `capturar_evidencia.sh`, `medir.py`.
- `datos/muestra_estadisticas.lp` (datos sintéticos de ejemplo, no evidencia de ejecución): `M001` → `P-01`.
- `README.md` de Hito 8: corregida la descripción del tag `partido_id` (antes decía "M001–M127") y la frase que afirmaba (incorrectamente) que ya seguía el criterio común.
- `README.md` raíz: la nota de convención de identificadores ahora dice "hitos 4 a 9" en vez de "4 a 7", ya que Hito 9 (IRIS) también usa `P-NN`/`XXX-NN` y ahora Hito 8 también.

**Qué queda pendiente:**
- `docs/evidencia/evidencias-influxdb.pdf` es un PDF con capturas de una ejecución real anterior a este cambio: todavía muestra `M001`. No se modificó porque es evidencia histórica real, no un ejemplo editable; hay que volver a capturar evidencia después de re-ejecutar la carga con el generador corregido.
- InfluxDB sigue generando hasta 127 partidos (torneo completo simulado) mientras que Neo4j/Cassandra/Redis usan una muestra de 32 partidos (`P-01`...`P-32`). El *formato* del ID ya es el mismo, pero los *valores* concretos sólo se van a poder cruzar 1 a 1 para los partidos P-01 a P-32 hasta que se decida un dataset común.

## 2026-10-09 — Reconciliar los cambios de motor entre Hito 1 y Hito 2/3

**Qué estaba mal:** el Hito 1 propone un motor por cada uno de 9 tipos de dato; el Hito 2 vuelve a evaluar 6 de esos casos con una matriz de decisión y en 3 de ellos termina eligiendo un motor distinto al del Hito 1, sin decirlo en ningún lado:
- "Estadísticas de grupos y partidos" (ranking): Redis (Hito 1) → IRIS (Hito 2).
- "Grupos privados" (alta de grupo): MongoDB (Hito 1) → IRIS (Hito 2, fusionado con el ranking).
- "Estadísticas de partido" (posesión, pases, tiros en vivo): Cassandra (Hito 1) → InfluxDB (Hito 2).

Leídos en orden, los tres hitos parecían contradecirse entre sí en vez de mostrar una decisión que evoluciona a medida que se profundiza el análisis.

**Qué se cambió:**
- `Hito-2-matriz-decision/Hito_2_Matriz_Decision_Fixture2030.md` (sección "RF1. Punto de partida"): se agregó una tabla que recorre los 9 datos del Hito 1 y dice, para cada uno, si la necesidad equivalente del Hito 2 cambió de motor y por qué (qué criterio pesó distinto en cada caso).
- `Hito-1-analisis/Hito_1_Analisis_Fixture2030.md` (tabla "Resumen", sección 3): se marcaron con `†` las tres filas afectadas y se agregó una nota al pie que explica el cambio y remite a la tabla del Hito 2 para el detalle.
- El Hito 3 no se tocó: ya era consistente con las decisiones del Hito 2 (las hereda sin cambios), así que no había nada que reconciliar ahí.

**Por qué se resolvió así y no reescribiendo el Hito 1:** el Hito 1 es el análisis inicial, anterior a la matriz de decisión; cambiarle las elecciones de motor para que coincidan con el Hito 2 borraría la evidencia de que el análisis se refinó con más información, que es justamente lo que la cátedra espera ver entre hitos. La corrección fue dejar el cambio explícito en vez de ocultarlo.

## 2026-10-09 — Avanzar sobre los 3 hallazgos de consistencia entre módulos

Estos habían quedado anotados como "pendientes, sin acción" porque la etapa de integración todavía no arrancó. Se revisaron de nuevo y se resolvieron dos; el tercero se dejó documentado como que no hace falta cambiarlo.

**1. Nombre de campo distinto (`codigo` vs `partido_id`/`equipo_id`) — corregido.** Al revisar con más detalle, Cassandra no usa `codigo` a secas para referenciar un partido: usa la columna `partido_codigo` (`Hito-6-fixture2030-cassandra/scripts/esquema.cql`). Ese es el patrón real del resto de los módulos cuando un campo referencia a otra entidad (`equipoCodigo` en Mongo, `partido_codigo` en Cassandra), no `codigo` solo. Se renombraron los tags de InfluxDB para seguir ese mismo patrón:
- `lib/generador.py` y todos los scripts que filtran por tag (`ag01_equipo.sql`, `ag02_por_minuto.sql`, `q01_ventana.sql`...`q04_pico_usuarios.sql`, `validacion.sql`, `validacion.sh`, `inicializacion.sh`, `capturar_evidencia.sh`, `medir.py`): `partido_id` → `partido_codigo`, `equipo_id` → `equipo_codigo`.
- `datos/muestra_estadisticas.lp` y `README.md` de Hito 8, actualizados igual, con nota `†` explicando el cambio (mismo tratamiento que se le dio a la tabla del Hito 1).
- Mismo pendiente que con el cambio de `M001`→`P-01`: `docs/evidencia/evidencias-influxdb.pdf` es anterior a este cambio y todavía muestra `partido_id=M001`; falta recapturar evidencia.

**2. Nombre de base de datos no uniforme — se decide no tocarlo.** Mongo usa la base `fixture2030`, Cassandra el keyspace `fixture2030`, InfluxDB usa `fixture2030_metrics`. Al revisarlo de nuevo, esto no es una inconsistencia a corregir: a diferencia del ID de partido (que necesita ser el mismo valor para poder cruzar datos entre motores), el nombre de la base no se comparte ni se consulta entre motores — es un detalle interno de cada uno. Que InfluxDB lo deje explícito como "_metrics" es, si acaso, más claro (dice para qué es esa base), no menos. Se deja como está.

**3. No había red Docker compartida entre los 6 módulos — agregada.** Se agregó una red nombrada `fixture2030_net` a los 6 `docker-compose.yml` (Hitos 4 a 9), con cada servicio principal conectado a ella:
```yaml
networks:
  fixture2030:
    name: fixture2030_net
```
Esto no cambia cómo se usa cada módulo hoy (se siguen levantando uno por uno, cada `docker compose up -d` crea la red si no existe o la reutiliza si otro módulo ya la creó) — es solo la preparación para que, cuando arranque la integración, los contenedores ya puedan resolverse entre sí por nombre de servicio sin tener que tocar los 6 compose de nuevo. Se validó que los 6 archivos siguen siendo YAML válido con `docker compose config`.

## Ver también

- `COMPARACION_main_vs_correcciones.md` — diferencias entre `main` y `correcciones` hito a hito.
- `REVISION_consignas_vs_entrega.md` — cumplimiento de cada hito contra su consigna oficial, incluyendo evidencia faltante.
