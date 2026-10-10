# Revisión de cumplimiento: consignas vs. entrega (rama `correcciones`)

Generado el 2026-10-09. Comparación hito a hito entre las consignas oficiales (`C:\Users\Galli\Desktop\personal\Hitos\consignas\`) y el contenido actual del repo en la rama `correcciones` (incluye cambios aún sin commitear).

## Resumen ejecutivo

| Hito | Estado | Principal pendiente |
|---|---|---|
| 1 — Análisis | Con observaciones | Faltan entidades (Eventos, Comentarios, Auditoría), tabla incompleta, nombre de archivo mal |
| 2 — Matriz de decisión | Con observaciones | Faltan 4 necesidades de datos exigidas, nombre de archivo mal |
| 3 — Arquitectura distribuida | Con observaciones | Falta particionamiento/sharding de datos (RF6), nombre de archivo mal |
| 4 — MongoDB | **Completo** | Sin pendientes relevantes |
| 5 — Neo4j | Con observaciones | Imagen Docker fijada (`neo4j:5` en vez de `latest`), **faltan 4 capturas de Neo4j Browser** (hay un TODO explícito) |
| 6 — Cassandra | Con observaciones | Falta medir escrituras/seg (RF12), falta evidencia de validación de carga masiva, una corrida de evidencia muestra timeouts sin resolver |
| 7 — Redis | **Completo** | Sin pendientes relevantes |
| 8 — InfluxDB | Con observaciones | Imagen Docker fijada (`influxdb:3-core` en vez de `latest`) — sin cambios desde `main` |
| 9 — IRIS | Completo pero **sin commitear** | Falta integrar al repo git |

**Lectura general:** la intuición era correcta — sobran evidencias en algunos lados (4 y 7 están sólidos) pero faltan en varios otros: Hito 5 tiene capturas de Neo4j Browser pendientes (documentado por el propio equipo en `CAPTURAS_PENDIENTES.md`), Hito 6 no tiene evidencia de rendimiento ni de validación post-carga masiva, y Hito 9 ni siquiera está commiteado.

---

## Hito 1 — Análisis
**Estado:** Con observaciones

**Cumple:** identifica 9 tipos de datos (≥8 pedidos); incluye tabla de volumen/crecimiento/acceso; modelo NoSQL propuesto + alternativas; estructura en 4 secciones; conclusión con ejemplos reales (Twitter, Amazon, Netflix).

**Falta o está mal:**
- Faltan las entidades **Eventos** (goles, tarjetas, cambios), **Comentarios** (mensajes en vivo) y **Auditoría** (registro de operaciones), que la consigna pide explícitamente y que son justamente los casos de mayor volumen que mejor justifican NoSQL.
- Tabla de identificación incompleta: falta "Descripción" y "Ejemplo de operación típica" por dato.
- Sección 2 (problemas de SQL) condensada en una sola columna "Problema", sin desglosar almacenamiento SQL / impacto en rendimiento / limitaciones de escalabilidad como pide la consigna.
- No hay una verdadera matriz de decisión (RF8), solo una tabla resumen dato→modelo→motivo.
- Nombre de archivo incorrecto: debería ser `Grupo_16_Hito_1_Analisis.md`, el actual es `Hito_1_Analisis_Fixture2030.md`.

**Evidencia faltante:** no aplica (documento de análisis, sin evidencia de ejecución).

## Hito 2 — Matriz de Decisión
**Estado:** Con observaciones

**Cumple:** 5 criterios ponderados al 100%; evalúa los 6 modelos NoSQL exigidos con escala 1-5 consistente; selección de modelo + alternativa por necesidad con justificación de trade-offs; mapa de persistencia y riesgos pendientes.

**Falta o está mal:**
- Cobertura incompleta: la consigna exige mínimo 7 necesidades de datos (Equipos y jugadores, Partidos y eventos, Usuarios y sesiones, Comentarios e interacciones, Estadísticas en vivo, Entidades complejas, Auditoría e históricos). El grupo solo cubre 6 y **omite explícitamente "Equipos y jugadores"**, que la consigna pide tratar con especial atención.
- Nombre de archivo incorrecto: falta el prefijo `Grupo_16_`.
- No sigue la estructura de 5 secciones sugerida (no es obligatorio, pero complica verificar extensión por sección).

**Evidencia faltante:** no aplica.

## Hito 3 — Arquitectura Distribuida
**Estado:** Con observaciones

**Cumple:** retoma la matriz del Hito 2; análisis CAP por subsistema con razonamiento específico; selecciona 4 subsistemas prioritarios; aplica N/R/W explícito para Cassandra; 5 escenarios de fallo (mínimo 3); set de métricas; diagrama Mermaid; corrige un error de la versión anterior (Redis/CAP).

**Falta o está mal:**
- **RF6 (particionamiento) no resuelto en el `.md` actual** — pero *sí estaba resuelto en el PDF original* y se perdió al reescribir el documento. Ver la sección "Comparación directa: PDF original vs. MD nuevo" más abajo para el detalle exacto de qué columna/criterio hay que recuperar.
- RF8 (escalabilidad) es breve y genérico, no distingue escalado vertical vs. horizontal.
- Nombre de archivo sin el prefijo `Grupo_16_`.
- Extensión posiblemente por debajo del mínimo pedido (4-6 páginas).

**Evidencia faltante:** el diagrama no muestra distribución geográfica/regional como pide la consigna; no hay PDF actualizado de la versión corregida.

## Consistencia de la propuesta teórica entre Hito 1, 2 y 3

Esto no compara PDF contra MD ni estructura: compara **qué dato va a qué motor y por qué**, a lo largo de los tres hitos de diseño, para ver si la propuesta se mantiene, se amplía o cambia — y si cambia, si está explicado.

El Hito 1 propone un motor por cada uno de 9 tipos de dato. El Hito 2 no vuelve a evaluar los 9: elige 6 "necesidades" como los casos con trade-off real, y a partir de ahí el Hito 3 ya no cambia nada (hereda exactamente las 6 decisiones del Hito 2, sin tocarlas). Cruzando el Hito 1 contra el Hito 2 aparecen 3 cambios de motor reales, ninguno estaba explicado en los documentos originales:

| Dato (Hito 1) | Motor en Hito 1 | Pasa a ser (Hito 2/3) | Motor en Hito 2/3 | ¿Mismo motor? |
| :--- | :--- | :--- | :--- | :--- |
| Selecciones, Estadios, Jugadores | MongoDB | Partidos finalizados y datos estáticos | MongoDB | Sí |
| Partidos | MongoDB (un solo documento) | Se divide en dos: Partidos en tiempo real / Partidos finalizados | Redis + MongoDB | Parcial — se divide, no cambia de fondo |
| Estadísticas de grupos y partidos (ranking) | **Redis** | Grupos y puntajes | **IRIS** | **No — contradicción sin explicar en el original** |
| Grupos privados | **MongoDB** | Grupos y puntajes | **IRIS** | **No — contradicción sin explicar en el original** |
| Estadísticas de partido (posesión, pases, tiros) | **Cassandra** | Métricas y estadísticas históricas | **InfluxDB** | **No — contradicción sin explicar en el original** |
| Usuarios, Sesiones | MongoDB, Redis | No se re-evalúan en Hito 2/3 | (sin cambios) | Sí, por omisión |
| — | — | Predicciones de usuarios (nuevo) | Neo4j | No existía en Hito 1 |
| — | — | Logs generados durante el partido (nuevo) | Cassandra | Cassandra reaparece pero para otro problema (logs/eventos, no estadísticas) |

Las 3 contradicciones reales:

1. **Ranking de grupos: Redis → IRIS.** El Hito 1 eligió Redis explícitamente por rendimiento ("con sortedset, leer y actualizar es casi instantáneo, sin locks"). El Hito 2 elige IRIS por el motivo contrario: consistencia fuerte ("los integrantes de un grupo deben ver los mismos puntajes"). No es necesariamente un error — es válido que entre un hito y otro cambie qué criterio pesa más — pero el documento nunca lo dice, así que leído en orden parece que el grupo se contradice solo.
2. **Alta de grupos: MongoDB → IRIS.** El Hito 1 trataba "grupos privados" (altas masivas) como un problema de volumen de escritura, resuelto con MongoDB. El Hito 2 lo absorbe dentro de "grupos y puntajes" y lo resuelve con IRIS, sin aclarar que se fusionó con el ranking ni por qué el problema de volumen de altas ya no pesa.
3. **Estadísticas en vivo: Cassandra → InfluxDB.** Es el cambio mejor fundamentado de los tres: el propio Hito 1 ya había dejado anotado que InfluxDB era "seriamente considerado" y "ambas opciones técnicamente válidas" para este mismo dato. El Hito 2 vuelve sobre esa alternativa y la elige. Cassandra no desaparece: queda libre para un problema distinto (logs/eventos en crudo), que terminó siendo el Hito 6 (comentarios masivos).

**Corrección aplicada:** agregué al Hito 2 (`Hito_2_Matriz_Decision_Fixture2030.md`, sección "RF1. Punto de partida") una tabla que deja explícitos estos tres cambios y su motivo, para que no se lea como una contradicción entre hitos sino como una evolución justificada. El Hito 1 y el Hito 3 no se tocaron: el Hito 1 queda como el punto de partida (es correcto que no prevea estos ajustes) y el Hito 3 ya era consistente con el Hito 2.

## Hito 4 — MongoDB (Módulo Documental)
**Estado:** Completo

**Cumple:** persistencia con volumen nombrado y healthcheck; colecciones `equipos`/`jugadores` con 64 equipos y 1536 jugadores reales; modelo por referencia justificado contra embedding; validación `$jsonSchema`; carga idempotente por `bulkWrite`+`upsert` con evidencia de rechazo por índice único; consultas, agregaciones (`$lookup`), updates con evidencia real; 6 índices justificados con evidencia COLLSCAN vs IXSCAN con tiempos reales; documento de decisiones técnicas con el nombre exacto pedido (`Grupo_16_Hito_4_Decisiones_Documentales_Fixture2030.md`).

**Falta o está mal:** limitaciones menores ya reconocidas honestamente por el propio equipo (integridad referencial jugador→equipo no forzada por constraint, contador que puede desincronizarse) — no son incumplimientos ocultos.

**Evidencia faltante:** ninguna; todas las evidencias en `docs/evidencia/*.txt` son reales, con timestamps, versión de Mongo y resultados concretos.

## Hito 5 — Neo4j (Módulo de Grafos)
**Estado:** Con observaciones

**Cumple:** modelo de nodos/relaciones completo y documentado; consistencia con Hito 4; carga de 64 equipos, 1536 jugadores, 10 sedes, 32 partidos; CRUD con lectura antes/después; recorridos de 2-3 saltos y camino variable con interpretación explícita; constraints de unicidad + índices; idempotencia probada (`MERGE`) con evidencia real y versión/fecha de ejecución.

**Falta o está mal:**
- **Incumplimiento de imagen Docker**: usa `neo4j:5` en vez de `neo4j:latest` como exige la consigna, sin indicación docente registrada ni nota en README justificando la desviación.
- No usa carpeta `import/`, pero está justificado (toda la carga es Cypher puro) — aceptable.

**Evidencia faltante — la más relevante de toda la revisión:**
- Existe un archivo `docs/evidencia/CAPTURAS_PENDIENTES.md` que indica **explícitamente 4 capturas de pantalla sin tomar**: (1) resultado del CRUD, (2) consulta de camino (RF9) en vista de grafo, (3) subgrafo completo, (4) verificación de idempotencia. El archivo da instrucciones de cómo tomarlas y pide borrarse una vez hecho — es un TODO abierto, no resuelto.
- Las evidencias de texto (cypher-shell) están completas, pero no reemplazan las capturas visuales de Neo4j Browser que pide puntualmente la consigna (RF11).

## Hito 6 — Cassandra (Comentarios Masivos)
**Estado:** Con observaciones

**Cumple:** ambiente Docker con healthcheck; patrones de acceso definidos antes del modelo; partición compuesta `(partido_codigo, bucket)` justificada con números reales; CRUD y 4 consultas sin `ALLOW FILTERING`; tabla secundaria justificada contra índice secundario; generador de carga masiva reproducible (>1.2M filas, semilla fija, MD5 verificado); idempotencia con IDs fijos.

**Falta o está mal:**
- **RF12 no resuelto**: `docs/rendimiento.md` dice literalmente que no hay cifra de escrituras/segundo cargada, todo marcado como "pendiente". La consigna exige explícitamente no evaluar una cifra inventada, pero acá directamente no hay ninguna.
- RF13/validación de carga masiva: falta evidencia de la validación por partición y de la segunda carga — listado como "pendiente de ejecutar" en la documentación.
- Los PDFs originales (`EVIDENCIA.pdf`, `Docuemntación & Justificación (1).pdf`) quedaron obsoletos frente a los docs nuevos; el README lo reconoce pero no los marca como descartados, lo que puede confundir al evaluador sobre cuál versión es la vigente.

**Evidencia faltante:**
- No hay ningún `.txt` con resultado de `prueba_rendimiento.py` (escrituras/seg).
- No hay evidencia de validación de conteos por partición tras la carga masiva ni de la segunda carga.
- `docs/evidencia/07_carga_copy_primera_vez.txt` muestra una corrida real con decenas de `WriteTimeout` en `comentarios_por_usuario`, sin que el mismo archivo documente si terminó con éxito ni cuántas filas quedaron afuera.

## Hito 7 — Redis (Caché de Usuarios y Sesiones)
**Estado:** Completo

**Cumple:** ambiente con healthcheck; 7 patrones de acceso documentados antes del modelo clave-valor; sesiones con TTL y renovación (ventana deslizante) evidenciadas; cache-aside con invalidación demostrada; operaciones atómicas (`ZINCRBY`/`INCRBY`) probadas con 8 procesos concurrentes mostrando contraste atómico vs. no atómico (pérdida real de datos documentada como ejemplo); ranking con ZSET y desempate por score compuesto; política de evicción `volatile-lru` justificada; carga idempotente; uso de `SCAN` en vez de `KEYS`; medición real de rendimiento y hit rate con método explícito.

**Falta o está mal:** limitaciones menores ya declaradas por el equipo (sin reconciliación de predicciones, tamaño de sesión estimado en vez de medido) — no son incumplimientos ocultos. No hay evidencia explícita de evicción forzada por presión de memoria, pero no es un requisito crítico.

**Evidencia faltante:** ninguna; las 10 evidencias tienen fecha, versión de Redis y datos concretos. Justo en este hito se completó lo que antes faltaba (se reemplazó una evidencia genérica por una real y se agregaron rendimiento y limpieza).

## Hito 8 — InfluxDB (Series Temporales)
**Estado:** Con observaciones (sin cambios respecto a `main`)

**Cumple:** ambiente funcional; patrones de acceso documentados antes del modelo; modelo multidimensional con tags/fields/time explícito; 5 fields con semántica de agregación justificada; carga reproducible vía API nativa con batching y reintentos; consultas de ventana, comparación y agregación por minuto; retención de 90 días aplicada; análisis de cardinalidad cuantificado (40.640 series máx.); medición real de throughput; evidencia en PDF con fecha, versión y resultados reales.

**Falta o está mal:**
- **Incumplimiento de imagen Docker**: usa `influxdb:3-core` en vez de `influxdb:latest`, que la consigna exige textualmente como restricción dura, sin justificación documentada.
- Inconsistencia menor: `puntos_usuarios` aparece en 960 en vez de los 480 esperados, sugiriendo una carga ejecutada dos veces sin limpieza entre corridas.

**Evidencia faltante:** ninguna crítica; único detalle es que los `.txt` generados por `capturar_evidencia.sh` están en `.gitignore`, quedando el PDF como única evidencia trazable versionada.

## Hito 9 — IRIS (Entidades Complejas)
**Nota:** esta revisión es sobre la implementación propia de `correcciones` (`Hito-9-fixture2030-iris/`). `main` sumó después su propia versión independiente (`Hito-9-fixture2030-iris-objetos/`, commit `8bb723a`) — no se revisó acá contra la consigna porque es contenido del otro grupo; la comparación entre ambas está en `COMPARACION_main_vs_correcciones.md`.

**Estado:** Completo funcionalmente, pero **sin commitear al repositorio**

**Cumple:** ambiente Docker con volumen durable; 7 clases con herencia correcta (Persona→Jugador/Arbitro/Tecnico); relación padre-hijo `Partido.Eventos`/`Evento.Partido` con índice del lado hijo; propiedades tipadas con validaciones; carga con guardado atómico; navegación por objetos sin SQL; consultas SQL proyectando herencia y relaciones; validación `%OnBeforeSave` rechazando datos inválidos (ejemplo literal de la consigna); borrado en cascada probado; documentación de diagrama de objetos y matriz de integridad.

**Falta o está mal:**
- **La consigna exige que el repo esté en GitHub (RNF5) y esta carpeta todavía no está commiteada** — aparece como untracked en `git status`. Hay que integrarla al historial antes de considerar el hito entregado.
- `ArbitroPrincipal` es referencia simple, no relación formal bidireccional (decisión documentada y justificada, pero sin integridad referencial garantizada por la base en ese caso particular).

**Evidencia faltante:** ninguna crítica (compilación, demos, consultas SQL y cascada de borrado documentados con salidas reales); falta solo evidencia dedicada de persistencia tras `docker compose down && up` (se menciona en prosa pero no hay `.txt` específico).

---

## Qué priorizaría para corregir antes de entregar

1. **Hito 5:** tomar las 4 capturas de Neo4j Browser pendientes (`docs/evidencia/CAPTURAS_PENDIENTES.md` tiene las instrucciones) — es lo más urgente porque es un TODO explícito y visible.
2. **Hito 9:** commitear la carpeta completa al repo.
3. **Hito 6:** correr `prueba_rendimiento.py` y `validar_carga_masiva.py`, guardar sus salidas en `docs/evidencia/`, y resolver/aclarar los `WriteTimeout` de la evidencia de carga masiva.
4. **Hitos 1, 2 y 3:** corregir nombres de archivo (`Grupo_16_Hito_N_...`), completar las entidades/necesidades de datos faltantes (Hito 1: Eventos/Comentarios/Auditoría; Hito 2: Equipos y jugadores + otras 3), y resolver el particionamiento de datos en Hito 3 (RF6).
5. **Hitos 5 y 8:** decidir si fijan la imagen Docker a `latest` como piden las consignas, o documentan explícitamente por qué no (ambas consignas lo tratan como restricción dura).
