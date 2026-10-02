# Fixture 2030 — Neo4j

Este proyecto carga el subgrafo deportivo original del Hito 5 y lo amplía con usuarios, grupos y predicciones. La unión entre ambos modelos es `(:Prediccion)-[:SOBRE]->(:Partido)`, por lo que desde una predicción se puede recorrer hacia equipos, jugadores, estadio y eventos del encuentro.

## Requisitos

- Docker Desktop en ejecución.
- Un navegador web.

No se requiere Neo4j Desktop ni una API REST: las cargas, el CRUD y las consultas se ejecutan con Cypher desde Neo4j Browser.

## Estructura

```text
fixture2030-neo4j/
├── docker-compose.yml
├── .env
├── queries/
│   ├── estructura.cypher
│   ├── carga.cypher
│   ├── carga_partidos.cypher
│   ├── carga_resultados_partidos.cypher
│   ├── carga_usuarios_predicciones.cypher
│   ├── crud.cypher
│   ├── consultas_grafo.cypher
│   ├── consultas_predicciones.cypher
│   └── flujo_visual_completo.cypher
├── docs/
│   ├── modelo_grafo.md
│   ├── decisiones.md
│   ├── fixture2030.grass
│   ├── evidencia/
│   └── referencia/
│       ├── Hito5_Grupo16_Neo4j_original.zip
│       └── PROMPT_CODEX_HITO5.md
└── import/
```

El ZIP y el documento de contexto originales se conservan en `docs/referencia/` para diferenciar el material de partida de la ampliación ejecutable.

## Iniciar Neo4j y abrir el Browser

Desde esta carpeta, iniciar el contenedor:

```bash
docker compose up -d
```

Abrir [Neo4j Browser](http://localhost:7474). La configuración inicial usa el usuario `neo4j` y la contraseña definida por `NEO4J_AUTH` en `.env` (por defecto, `fixture2030`). Seleccionar la base de datos `neo4j` al ingresar.

Para detenerlo sin borrar los datos:

```bash
docker compose down
```

## Carga inicial desde Neo4j Browser

Abrir cada archivo de `queries/` y ejecutar sus bloques de Cypher en este orden exacto. En Browser se pueden copiar y ejecutar los bloques separados por punto y coma.

1. `queries/estructura.cypher`
2. `queries/carga.cypher`
3. `queries/carga_partidos.cypher`
4. `queries/carga_resultados_partidos.cypher`
5. `queries/carga_usuarios_predicciones.cypher`
6. `queries/crud.cypher`
7. `queries/consultas_grafo.cypher`
8. `queries/consultas_predicciones.cypher`

La cuarta carga completa los 32 `Partido` con `equipoGanador`, `equipoPerdedor`, `golesGanador` y `golesPerdedor`. Son marcadores de demostración, no resultados oficiales: cada uno queda identificado con `origenResultado: "SIMULADO"`. La quinta carga crea 5 `Usuario`, 3 `Grupo` y 7 `Prediccion` de prueba. Sus predicciones se vinculan solamente a `P001`, `P002` y `P003`, que ya existen tras ejecutar `carga_partidos.cypher`.

Las predicciones siguen siendo independientes del marcador de `Partido`. Para compararlas sin guardar datos redundantes, ejecutar la consulta 12 de `queries/consultas_predicciones.cypher`.

`crud.cypher` crea y elimina nodos de demostración con identificadores `9001`; no elimina los datos principales cargados.

## Comprobaciones rápidas

Después de la carga, estas consultas deben devolver datos:

```cypher
MATCH (u:Usuario)-[:PERTENECE_A]->(g:Grupo)
RETURN u, g;

MATCH (u:Usuario)-[:REALIZA]->(pr:Prediccion)-[:SOBRE]->(p:Partido)
RETURN u, pr, p;
```

`queries/consultas_predicciones.cypher` contiene consultas de grupos, pronósticos por usuario o partido, conteos y recorridos integrados hacia equipos, estadios y eventos.

## Flujo visual legible

No conviene renderizar a la vez todos los nodos del proyecto: la carga completa contiene 1.281 nodos. Para una vista que conserva las ocho etiquetas y todos los tipos de relación, ejecutar `queries/flujo_visual_completo.cypher`.

Para que Browser muestre nombres en lugar de valores automáticos como `TRUE` o fechas:

1. Ejecutar `:style` en el editor de Neo4j Browser.
2. En el resultado, usar **Upload** e importar `docs/fixture2030.grass`.
3. Ejecutar `queries/flujo_visual_completo.cypher`.

El estilo usa `nombre` para `Usuario`, `nombreGrupo` para `Grupo`, y muestra en `Partido` el ID junto al marcador simulado. Usa propiedades equivalentes para las demás etiquetas.

## Reinicio limpio opcional

Neo4j conserva sus datos en volúmenes Docker. Si se necesita borrar por completo la base local y repetir toda la carga desde cero, ejecutar:

```bash
docker compose down -v
docker compose up -d
```

Este reinicio elimina todos los datos locales de Neo4j. Después, volver a ejecutar los archivos en el orden indicado.

## Alcance temporal

Las relaciones `REALIZA` incluyen `fechaPrediccion` con precisión `DateTime`. Los eventos originales sólo conservan su minuto relativo y los partidos no tienen hora de inicio; por ello el proyecto puede relacionar una predicción con los eventos de su partido, pero no decidir cronológicamente si fue antes o después de un evento específico.
