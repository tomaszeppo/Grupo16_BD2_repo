# Fixture 2030 — Hito 5 (módulo de grafos Neo4j)

Contexto para retomar este proyecto en Claude Code, viniendo de una conversación
larga en claude.ai donde se armó y depuró todo esto de forma interactiva.

## Qué es esto

TP de Ingeniería de Datos II, Grupo 6, caso de estudio "Fixture 2030"
(plataforma para un Mundial 2030 hipotético). Este hito (5 de varios) es el
módulo de grafos en Neo4j. Los hitos anteriores (1 a 4) ya están entregados;
Hito 4 fue un módulo documental en MongoDB (carpeta hermana
`fixture2030-mongodb/`, no incluida acá).

La consigna completa está en
`Hito_5_Requisitos_Tecnicos_Modulo_de_Grafos_del_Fixture_2030.pdf` (si no
está en esta carpeta, pedirla).

## Estado actual (al momento del traspaso)

Todo el contenido funcional ya se probó en la instancia real de Neo4j del
usuario (Docker Desktop, Windows) y dio los resultados esperados:

- Constraints: 5 restricciones de unicidad, confirmadas `ONLINE` con `SHOW CONSTRAINTS`.
- Índices: 9 en total (5 de los constraints + `evento_tipo_idx` +
  `partido_fecha_idx` + 2 de lookup automáticos de Neo4j), confirmados con `SHOW INDEXES`.
- Carga (`carga.cypher`): confirmada dos veces con el mismo resultado
  (idempotencia probada) — 64 equipos, 1536 jugadores, 12 sedes, 32 partidos, 10 eventos.
- CRUD (`crud.cypher`): confirmado — el partido P-01 pasó a fase "Octavos de
  final", el evento P-01-EV1 quedó en minuto 25, y el evento de prueba
  P-01-EV3 se creó y se borró correctamente (confirmado que queda `null`).
- Consultas de patrones (RF8) y de camino (RF9): el usuario confirmó haberlas
  corrido; la de camino (ARG-GAL, 4 saltos vía sede compartida) tiene captura.

## Bug importante que se encontró y corrigió

El `docker-compose.yml` original del usuario tenía la contraseña de
`NEO4J_AUTH` pegada por error con la ruta de un archivo de Windows (una
captura de pantalla), en vez de una contraseña real. Eso explicaba el
"Connection to instance failed" que tuvo al principio. Se corrigió para usar
`${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-fixture2030}` leyendo de un `.env`
(no incluido en el repo, el usuario lo arma localmente), en línea con RNF8
(credenciales por variable de entorno, no hardcodeadas).

## Decisiones de modelo (ya cerradas, no re-discutir salvo pedido explícito)

- Los nodos quedaron con las propiedades mínimas que participan de alguna
  relación (se sacó todo lo puramente descriptivo — nombre, fecha de
  nacimiento, capacidad de estadio, etc. — porque ese detalle ya vive en el
  módulo de Mongo del Hito 4). El detalle completo está en
  `docs/modelo_grafo.md`.
- Nombres y direcciones de relación (`PERTENECE_A`, `DISPUTA`) copian
  exactamente los de la práctica guiada de la Clase 5 de la materia, no son
  invención propia. `OCURRE_EN` y `PROTAGONISTA_DE` sí son propios (la clase
  no llega a modelar eventos).
- La consulta de análisis (RF9) usa un patrón de camino simple
  (`-[*1..4]-`), no algoritmos de Graph Data Science — la clase no llega a
  instalar el plugin GDS en la práctica, así que se evitó a propósito para
  no salirse del contenido visto.
- No hay carpeta `import/` ni CSVs: toda la carga es Cypher puro (`UNWIND` +
  generación programática de jugadores), decisión tomada para mantenerlo
  simple y sin pasos extra de copiar archivos al contenedor.

## Preferencias del usuario para este proyecto

- Prefiere que le pasen comandos Cypher directos para correr él mismo en
  Neo4j Browser, en vez de que se le entreguen solo archivos que no puede
  ejecutar in-situ (aunque los archivos también se arman al final, para el
  repositorio).
- Para los documentos del TP en general: redacción natural y suelta, como si
  la hubiera escrito el propio grupo — evitar anglicismos y jerga tipo
  "trade-off", "ad-hoc", "stack"; evitar tono genérico de IA.

## Qué falta para cerrar el hito

1. Confirmar el `.env` con una contraseña real (no la ruta de archivo por
   error) y volver a levantar el contenedor limpio si hace falta
   (`docker compose down -v && docker compose up -d`).
2. Sacar la única captura que faltaba: vista general del subgrafo
   (`MATCH (n) RETURN n LIMIT 100`, pestaña Graph).
3. Guardar las ~8 capturas ya generadas dentro de `docs/evidencia/`
   (reemplazando el archivo `PONER_CAPTURAS_ACA.txt`, que lista cuáles son).
4. Revisar que el `docker-compose.yml` real del usuario (Windows, con red y
   plugins APOC/GDS agregados por el usuario) sea el que quedó corregido acá,
   no una versión vieja con la contraseña rota.

## Regla de negocio pendiente (para un hito futuro, no este)

Para cuando se implemente el módulo de Predicciones: cada predicción guarda
la fecha de última actualización; en caso de empate en puntos, desempata
quien cargó/actualizó resultados con más antelación (sumatoria de la
antelación de todas las predicciones del usuario, no solo la última). No es
parte de este hito, solo dejarlo anotado.
