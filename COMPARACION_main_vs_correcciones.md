# Comparación `main` vs `correcciones` — hito a hito

Generado el 2026-10-09 a partir de `git diff --stat main HEAD` (HEAD = `correcciones`, commit `aa6dd6f`).
No incluye los cambios aún sin commitear que hay actualmente en el working tree (ver sección final).

**Actualización (mismo día):** `main` recibió un commit nuevo (`8bb723a "hito 9"`) después de generado este documento, agregando `Hito-9-fixture2030-iris-objetos/`. Esa sección ya está actualizada abajo; el resto del documento sigue reflejando la comparación original.

## Resumen general

| Hito | ¿Alineado con main? | Tipo de cambio |
|---|---|---|
| Hito 1 - Análisis | Sí (solo suma) | Se agregó versión `.md` del entregable, el PDF original se mantiene |
| Hito 2 - Matriz de decisión | Sí (solo suma) | Se agregó versión `.md` del entregable, el PDF original se mantiene |
| Hito 3 - Arquitectura distribuida | Sí (solo suma) | Se agregó versión `.md` del entregable, el PDF original se mantiene |
| Hito 4 - MongoDB | **No** | Reestructuración completa de carpetas y scripts |
| Hito 5 - Neo4j | **No** | Reescritura de queries, docs y evidencias |
| Hito 6 - Cassandra | **No** | En `main` solo había 2 PDFs; en `correcciones` se agregó toda la implementación (docker-compose, scripts, docs, evidencias) |
| Hito 7 - Redis | **No** | Reestructuración completa de scripts y docs |
| Hito 8 - InfluxDB | Sí | Sin cambios entre ramas |
| Hito 9 - IRIS | **No** | `main` tiene su propia implementación (`Hito-9-fixture2030-iris-objetos/`, commit `8bb723a`, 2026-10-09), distinta e independiente de la de `correcciones` (`Hito-9-fixture2030-iris/`, aún sin commitear) — ver detalle abajo |

---

## Hito 1 — Análisis (`Hito-1-analisis`)
**Estado:** alineado, cambio aditivo.
- Se agregó `Hito_1_Analisis_Fixture2030.md`, la versión Markdown del PDF original (`Grupo_16_Hito_1_Analisis.pdf`), que se conserva sin tocar.
- No se borró ni modificó nada de lo que ya estaba en `main`.

## Hito 2 — Matriz de decisión (`Hito-2-matriz-decision`)
**Estado:** alineado, cambio aditivo.
- Mismo patrón que el Hito 1: se agregó `Hito_2_Matriz_Decision_Fixture2030.md` como versión Markdown, manteniendo el PDF (`Grupo_16_Hito_2_Matriz_Decision_Fixture2030.pdf`).

## Hito 3 — Arquitectura distribuida (`Hito-3-arquitectura-distribuida`)
**Estado:** alineado, cambio aditivo.
- Se agregó `Hito_3_Arquitectura_Distribuida_Fixture2030.md` como versión Markdown, manteniendo el PDF original.

## Hito 4 — MongoDB (`Hito-4-fixture2030-mongodb`)
**Estado:** no alineado — reestructuración completa.

En `main` la carpeta tenía una organización simple y plana:
- `carga/carga_equipos.mongodb.js`, `carga/carga_jugadores.mongodb.js`
- `agregacion/agregacion.mongodb.js`
- `indices y rendimiento/indices.mongodb.js`
- `queries/CRUD.mongodb.js`, `queries/busqueda_y_filtrado.mongodb.js`
- `validaciones/validaciones.mongodb.js`
- `documentacion/justificaciones.md`, `documentacion/Pruebas.pdf`
- `.env` (committeado, con credenciales)

En `correcciones` se reemplazó todo eso por una estructura más prolija y versionable:
- `init-scripts/01-create-collections.js`, `02-create-indexes.js`, `03-load-data.js`
- `queries/01-consultas-recuperacion.js`, `02-actualizaciones.js`, `03-analisis-indices.js`, `04-verificar-idempotencia.js`
- `scripts/cargar-datos.js`
- `schemas/modelo-documental.md`
- `docs/decisiones-de-diseno.md` + `docs/evidencia/01..06_*.txt` (evidencia de ejecución real, en texto en vez de PDF)
- `README.md` actualizado y ampliado
- Se reemplazó `.env` por `.env.example` (buena práctica: ya no se versionan credenciales)
- Se agregó `.gitignore`
- Se eliminó `.DS_Store` (archivo de macOS que no debería estar versionado)
- Se quitó el PDF `Pruebas.pdf` en favor de evidencias en texto plano dentro de `docs/evidencia/`

**Motivo aparente:** pasar de scripts sueltos sin evidencia reproducible a un flujo documentado con decisiones de diseño explícitas y evidencia de ejecución versionada como texto.

## Hito 5 — Neo4j (`Hito-5-fixture2030-neo4j`)
**Estado:** no alineado — reescritura de queries y docs.

Cambios principales:
- `docker-compose.yml` modificado (33 líneas de diff).
- `README.md` ampliado considerablemente (186 líneas).
- Se agregó `docs/decisiones.md` (nuevo).
- Se agregó `docs/evidencia/` con archivos de texto reales: `01_estructura_constraints_indices.txt`, `02_carga_primera_vez.txt`, `03_carga_segunda_vez_idempotencia.txt`, `04_crud.txt`, `05_recarga_no_pisa_crud.txt`, `06_consultas_grafo.txt` — reemplazando el PDF único `Capturas Hito 5.pdf` que había en `main`.
- `docs/modelo_grafo.md` se redujo y simplificó (de 211 líneas largas a una versión más acotada).
- Los scripts Cypher se consolidaron y redujeron: se eliminaron `carga_partidos.cypher`, `carga_resultados_partidos.cypher`, `carga_usuarios_predicciones.cypher`, `consultas_predicciones.cypher`, `flujo_visual_completo.cypher`, y se agregó `verificar_carga.cypher`. `carga.cypher`, `consultas_grafo.cypher`, `crud.cypher` y `estructura.cypher` se reescribieron con menos contenido pero más enfocado.

**Motivo aparente:** simplificar y consolidar los scripts de carga (antes repartidos en varios archivos por entidad) en uno central, y reemplazar un PDF de capturas por evidencia en texto plano e idempotencia verificable.

## Hito 6 — Cassandra (`Hito-6-fixture2030-cassandra`)
**Estado:** no alineado — en `main` casi no tenía implementación.

En `main` esta carpeta solo contenía:
- `EVIDENCIA.pdf`
- `Docuemntación & Justificación (1).pdf`

En `correcciones` se construyó toda la implementación desde cero, manteniendo esos dos PDFs:
- `docker-compose.yml`, `.gitignore`
- `README.md`
- `data/partidos_referencia.csv`
- `docs/decisiones_de_particionamiento.md`, `docs/modelo_tabular.md`, `docs/patrones_de_acceso.md`, `docs/rendimiento.md`
- `docs/evidencia/01..07_*.txt` (ambiente, esquema, carga/idempotencia, consultas, CRUD, generación y reproducibilidad del generador, carga masiva con COPY)
- `scripts/esquema.cql`, `carga_muestra.cql`, `consultas.cql`, `crud.cql`, `cargar_y_validar.sh`, `generar_carga_masiva.py`, `prueba_rendimiento.py`, `validar_carga_masiva.py`

**Motivo aparente:** este hito estaba prácticamente sin implementar en `main` (solo los documentos entregados), y en `correcciones` se desarrolló el ambiente completo con esquema, carga, consultas, CRUD y pruebas de rendimiento con evidencia real.

## Hito 7 — Redis (`Hito-7-fixture2030-redis`)
**Estado:** no alineado — reestructuración completa.

En `main` había un enfoque basado en Makefile y shell scripts:
- `Makefile`, `scripts/run_all.sh`, `scripts/medir.sh`, `scripts/limpieza.sh`, `scripts/capturar_evidencia.sh`, `scripts/prueba_concurrencia.sh`
- `docs/coherencia_con_tpo.md`, `docs/pruebas_y_evidencia.md`, `docs/evidencia/README.md`
- Evidencia en un único PDF (`Evidencia - Screenshots.pdf`)
- `datos/demo_mongo_response_P001.json`

En `correcciones`:
- Se eliminó el `Makefile` y los scripts `.sh` auxiliares (`run_all.sh`, `medir.sh`, `limpieza.sh`, `capturar_evidencia.sh`, `prueba_concurrencia.sh`), reemplazados por scripts Python directos: `scripts/prueba_concurrencia.py`, `scripts/prueba_rendimiento.py`, `scripts/hit_rate.py`.
- Se eliminaron `docs/coherencia_con_tpo.md`, `docs/pruebas_y_evidencia.md`, `docs/evidencia/README.md` y se agregó `docs/rendimiento.md`.
- Se reemplazó el PDF único de evidencia por archivos de texto reales en `docs/evidencia/`: `01_arranque.txt`, `02_carga_muestra_repetida.txt`, `03_sesiones.txt`, `04_cache.txt`, `05_concurrencia_y_espectadores.txt`, `06_metricas.txt`, `07_prueba_concurrencia.txt`, `08_hit_rate.txt`.
- Se agregó `scripts/actualizar_ranking.lua` y `scripts/espectadores.redis` para el patrón de ranking en vivo / espectadores (este es justo el contenido que en el working tree actual estás volviendo a borrar, ver abajo).
- `README.md`, `docs/ciclo_de_vida_e_invalidacion.md`, `docs/memoria_y_escalabilidad.md`, `docs/modelo_clave_valor.md`, `docs/patrones_de_acceso.md` reescritos y ampliados.
- Scripts `.redis` (`cache.redis`, `carga_muestra.redis`, `concurrencia.redis`, `metricas.redis`, `sesiones.redis`, `inicializacion.redis`) reescritos con comandos más completos.
- Se eliminó `datos/demo_mongo_response_P001.json` (dato de ejemplo que ya no se usa).

**Motivo aparente:** pasar de un flujo basado en Makefile/shell a uno basado en scripts Python + Redis CLI, con evidencia en texto y documentación de modelo clave-valor más detallada.

## Hito 8 — InfluxDB (`Hito-8-fixture2030-influxdb`)
**Estado:** alineado — sin diferencias entre `main` y `correcciones`. No requiere acción.

## Hito 9 — IRIS
**Estado:** no alineado — son dos implementaciones distintas e independientes, en carpetas con nombre distinto.

`main` recibió un commit nuevo (`8bb723a "hito 9"`, 2026-10-09) con una carpeta **`Hito-9-fixture2030-iris-objetos/`** (con sufijo `-objetos`), construida con otro criterio que la de `correcciones` (`Hito-9-fixture2030-iris/`, sin sufijo, todavía sin commitear). No es la misma implementación corregida ni se tocan entre sí — conviven dos versiones paralelas del mismo hito:

| | `main` (`...iris-objetos`) | `correcciones` (`...iris`) |
| :--- | :--- | :--- |
| Namespace de clases | `Fixture.*` | `Fixture2030.*` |
| Código de partido | Generado al vuelo (`H9-M-<horolog>`, ej. `H9-M-67852-73429`) | Mismo código `P-NN` que Neo4j/Cassandra/Redis/InfluxDB |
| Jugador → Equipo | Sin ningún campo que lo vincule a un equipo | `EquipoCodigo` referencia al mismo código que usa Mongo |
| Validación de estado | Máquina de estados explícita (`CambiarEstado()`: Programado → En juego → Finalizado) | Validación puntual en `%OnBeforeSave` (rechaza evento en minuto 0 de partido Finalizado) |
| Entidades | Persona, Jugador, Arbitro, Tecnico, Partido, Evento (sin relación formal Partido↔Árbitro) | Las mismas 6, más una referencia `ArbitroPrincipal` en Partido |
| Evidencia | `docs/evidencia/` con una corrida real (`demo_20261009_172348.txt`) + PDF | `docs/evidencia/` con corridas de compilación, demo, consultas SQL y cascada de borrado |
| Docker | mismo `container_name: fixture2030-iris` y mismo bind `~/docker/data/iris` que `correcciones` | ídem |

**Lo más importante para la integración futura:** igual que pasó con InfluxDB, el código de partido de `main` (`H9-M-...`) no sigue la convención `P-NN` del resto de los módulos — no se puede cruzar directamente con Neo4j, Cassandra, Redis ni InfluxDB. Ver `CHANGELOG.md` para el detalle.

No se modificó el contenido de `main` — solo se documentó la comparación, porque es el TP del otro grupo y las correcciones van únicamente sobre `correcciones`.

---

## Cambios pendientes sin commitear (no reflejados arriba)

Además de lo ya commiteado en `aa6dd6f`, hay trabajo en curso en el working tree de `correcciones` que iría a profundizar aún más las diferencias con `main`:

- **Staged:** borrado de `Hito-7-fixture2030-redis/scripts/actualizar_ranking.lua` y `espectadores.redis` (revirtiendo lo agregado en el commit anterior).
- **Modified:** ajustes en Hito-4 (README, decisiones de diseño, evidencias, scripts de carga/queries) y Hito-7 (README, docs, evidencias, scripts `.redis`/`.py`), más un detalle en el README de Hito-5 y en el README raíz.
- **Untracked:** nuevas evidencias de Redis (`05_concurrencia_comandos.txt`, `09_rendimiento.txt`, `10_limpieza.txt`, `limpieza.redis`), un documento nuevo de decisiones en Hito-4, un recordatorio de capturas pendientes en Hito-5, scripts auxiliares en `Grupo6-nuestro/scratch_tools/`, y el directorio completo de `Hito-9-fixture2030-iris`.

**Recomendación:** antes de abrir un PR de `correcciones` → `main`, conviene decidir si Hito-9 y `Grupo6-nuestro/scratch_tools` se incluyen o se dejan para otra rama, ya que no forman parte de los hitos entregables numerados.
