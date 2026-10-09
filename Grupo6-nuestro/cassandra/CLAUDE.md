# Fixture 2030 — Hito 6 (comentarios masivos en Cassandra)

Contexto para retomar este proyecto en Claude Code. Viene de una conversación
larga en claude.ai donde se diseñó y se armó todo esto sin acceso a Docker ni
a un Cassandra real en ese ambiente — a diferencia del Hito 5 (Neo4j), este
módulo todavía no tiene ninguna evidencia de ejecución real.

## Qué es esto

TP de Ingeniería de Datos II, Grupo 6, caso de estudio "Fixture 2030". Este
es el Hito 6: módulo de comentarios masivos sobre Apache Cassandra, diseñado
por patrones de acceso (no por traducción de un modelo relacional). La
consigna completa debería estar como PDF en el repositorio; si no está,
pedirla.

## Lo único que sí se validó fuera de una Cassandra real

`scripts/generar_carga_masiva.py` se corrió (sin Cassandra, solo genera
CSV): con 1.200.000 filas objetivo, generó 1.199.770 en 14,2 segundos, con
un máximo de 12.923 filas en la partición más cargada. Esos números ya están
volcados en `docs/rendimiento.md` y `docs/decisiones_de_particionamiento.md`
— no hace falta repetir esa corrida salvo que se cambie el generador.

## Tarea principal: validar contra Cassandra real

1. Levantar el ambiente: `docker compose up -d` (requiere que exista
   `~/docker/data/cassandra` en el host — ver README para la nota de
   Windows/WSL2, el usuario trabaja en Windows).
2. Correr `scripts/esquema.cql` y confirmar con `DESCRIBE KEYSPACE
   fixture2030;` que las 3 tablas quedaron creadas.
3. Correr `scripts/carga_muestra.cql` y confirmar
   `SELECT COUNT(*) FROM comentarios_por_partido;` = 40.
4. Correr al menos dos consultas de `scripts/consultas.cql` y confirmar que
   los resultados tienen sentido.
5. Correr `scripts/crud.cql` a mano (tiene un placeholder `<comentario_id>`
   que hay que reemplazar por un valor real leído del propio contenedor).
6. Generar el volumen masivo real (`generar_carga_masiva.py --target-rows
   1200000`) y cargarlo con los comandos `COPY` que el script imprime al
   final. Confirmar que la carga terminó sin error.
7. Correr la prueba de rendimiento (`prueba_rendimiento.py`, requiere
   `pip install cassandra-driver`) o `cassandra-stress` como alternativa, y
   completar la plantilla de `docs/rendimiento.md` con el resultado real
   (no dejar los "_completar_" sin llenar).
8. Sacar las capturas de `docs/evidencia/CAPTURAS_PENDIENTES.md` y
   guardarlas ahí, reemplazando ese archivo de texto.

## Decisiones de modelo (ya cerradas, no re-discutir salvo pedido explícito)

- Clave de partición `(partido_codigo, bucket)`, con `bucket` = ventana de
  10 minutos desde el inicio del partido, para evitar que un partido muy
  comentado concentre todo en una sola partición.
- Clustering por `comentario_id` (timeuuid) DESC, para leer lo más reciente
  primero sin ordenar en la aplicación.
- Tabla separada `comentarios_por_usuario` (duplicación controlada) en vez
  de un índice secundario, porque un índice sobre una columna de alta
  cardinalidad como `usuario_id` es un anti-patrón conocido en Cassandra.
- Sin TTL en los comentarios (se conservan como archivo del partido; TTL
  masivo generaría muchos tombstones).
- Los códigos de partido (`P-01` a `P-32`) y sus fechas son los mismos que
  usa el módulo de grafos del Hito 5, para mantener coherencia entre hitos.
- `SimpleStrategy` con factor de replicación 1: es un nodo único de
  laboratorio, no una topología de alta disponibilidad. Documentado así a
  propósito, no es un olvido.

## Preferencias del usuario para este proyecto

- Redacción natural y suelta en toda la documentación, como si la hubiera
  escrito el propio grupo — evitar anglicismos y jerga tipo "trade-off",
  "ad-hoc", "stack"; evitar tono genérico de IA.
- Prefiere validar con evidencia real antes de dar algo por entregado.
- Antes de la entrega final, este `CLAUDE.md` (y cualquier carpeta
  `.claude/` de la sesión de trabajo) se borra — no son parte de lo que se
  entrega al profesor. Los pasos anteriores en este mismo TP (Hitos 4 y 5)
  siguieron ese mismo patrón.

## Qué falta para cerrar el hito

Todo lo de "Tarea principal" de arriba. Una vez confirmado con evidencia
real, avisar con un resumen de: qué se corrió, qué se verificó contra la
base real (conteos, explain si aplica, tasa de escritura medida), qué se
modificó del diseño original y por qué, y qué capturas quedaron guardadas.
