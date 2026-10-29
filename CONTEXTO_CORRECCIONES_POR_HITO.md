# Correcciones por hito

Revisión: 29/10/2026. `main@de379cc`; `origin/correcciones@27f28e1` sin integrar. `[x] (irrelevante)` indica que no se exige para el Hito 12, no que la devolución histórica esté corregida. No hay cambios del Hito 12 verificados para marcar `(arreglado en hito 12)`. La relevancia de MongoDB, Neo4j, Cassandra, caché, InfluxDB e IRIS depende del flujo elegido.

## Hito 1 — Análisis de Requisitos del Fixture 2030

### Comentario original del profesor

> Deben ajustar el análisis al contenido visto: aparecen sharding, TTL, sorted sets, actualizaciones atómicas y detalles específicos de Cassandra/Redis que aún no fueron desarrollados. Además, conviene revisar la idea de que ACID es “un costo innecesario” para datos estáticos: deben justificar SQL vs NoSQL por volumen, velocidad, acceso, flexibilidad y escalabilidad, sin simplificar las garantías transaccionales.

### Estado y tareas

**Parcial en `origin/correcciones`; no incorporado en `main`.**

- [x] En la versión revisada, reconocer el valor de ACID y organizar la comparación por volumen, velocidad, acceso, flexibilidad y escalabilidad.
- [x] (irrelevante) Eliminar detalles por anticipar contenidos de clase, como `sortedset`: esa restricción de etapa ya no aplica al Hito 12.
- [x] (irrelevante) Incorporar la versión revisada del documento del Hito 1 como requisito para realizar el Hito 12.

## Hito 2 — Matriz de Decisión del Fixture 2030

### Comentario original del profesor

> Deben completar una matriz real de comparación de los seis modelos por cada necesidad, ya que la planilla final evalúa una sola alternativa por caso. Además, anticipan implementación con caché, Pub/Sub/Streams, TTL, particionado, sharding y transferencia Redis→MongoDB. Para el próximo hito conviene dejar esos mecanismos fuera y sostener la decisión solo con criterios, ponderaciones, alternativas y trade-offs.

### Estado y tareas

**Parcial en `origin/correcciones`; no incorporado en `main`.**

- [x] Agregar tablas que puntúan los seis motores por necesidad, con criterios, pesos y totales.
- [x] (irrelevante) Retirar mecanismos por anticipar contenidos de clase: en el Hito 12 pueden usarse si están justificados.
- [ ] Revisar que las elecciones y sus excepciones al resultado ponderado estén justificadas sin afirmaciones de rendimiento no medidas.
- [x] (irrelevante) Incorporar la revisión de la matriz anterior como requisito para realizar el Hito 12.

## Hito 3 — Arquitectura Distribuida del Fixture 2030

### Comentario original del profesor

> Deben corregir el análisis CAP de Redis: ante una partición no pueden priorizar simultáneamente consistencia y disponibilidad; deben explicitar qué propiedad sacrifican y qué impacto aceptan. También conviene reflejar esa decisión en los escenarios de falla y en el diagrama para mantener trazabilidad entre CAP, replicación y comportamiento esperado.

### Estado y tareas

**Observación resuelta en `origin/correcciones`; falta incorporarla en `main`.**

- [x] Explicitar que la propuesta prioriza consistencia y sacrifica disponibilidad ante una partición.
- [x] Describir limitación o rechazo de operaciones en la región que no confirma el estado actual.
- [x] Reflejar esa decisión en escenarios de falla y en el diagrama Mermaid.
- [x] (irrelevante) Integrar el documento y actualizar el PDF del Hito 3 como requisito para realizar el Hito 12.

## Hito 4 — Módulo Documental

### Comentario original del profesor

> Deben corregir la carga reproducible e idempotente: la evidencia muestra que Argentina quedó duplicada y debieron eliminarla manualmente, lo que contradice el requisito de reejecutar la carga sin generar inconsistencias. Para el próximo hito deben resolver la unicidad desde el script/upsert y demostrar una segunda ejecución con los mismos totales, sin correcciones manuales.

### Estado y tareas

**Observación resuelta con evidencia versionada en `origin/correcciones`; falta incorporarla en `main`.**

- [x] Implementar carga con upsert y restricciones de unicidad.
- [x] Registrar segunda ejecución: 0 equipos nuevos y 0 jugadores nuevos; totales de 64 equipos y 1536 jugadores.
- [x] Registrar recarga con totales iguales y rechazo de un segundo `ARG` por índice único (`E11000`); queda un solo `ARG`.
- [ ] Incorporar los scripts y la evidencia a la versión que se utilizará, si el flujo del Hito 12 usa MongoDB.

## Hito 5 — Módulo de Grafos del Fixture 2030

### Comentario original del profesor

> Deben ajustar el alcance: incorporan Usuario, Grupo y Prediccion y recorridos sociales, cuando el Hito 5 se concentra en fixture, partidos, eventos y entidades deportivas. La carga con MERGE sí corrige el problema de idempotencia observado en el Hito 4. Para el próximo hito conviene implementar solo el módulo solicitado y reservar esas entidades para su etapa correspondiente.

### Estado y tareas

**Corrección del alcance resuelta en `origin/correcciones`; falta incorporarla en `main`.**

- [x] Acotar el esquema revisado a Equipo, Jugador, Partido, Sede y Evento.
- [x] Retirar de la versión revisada los scripts específicos de usuarios y predicciones.
- [ ] Incorporar el modelo y las consultas corregidos, si el flujo del Hito 12 usa Neo4j.

## Hito 6 — Comentarios Masivos en Cassandra

### Comentario original del profesor

> Deben completar la entrega técnica y la evidencia: el particionamiento, clustering y acceso secundario están bien justificados, pero solo muestran inserciones y consultas; falta demostrar CRUD completo, carga reproducible de más de 1.000.000 de comentarios y una medición real de escrituras/s con ambiente y limitaciones. Para el próximo hito deben acompañar el análisis con scripts y resultados verificables.

### Estado y tareas

**Parcial en `origin/correcciones`; en `main` la carpeta del hito solo tiene PDFs.**

- [x] Incorporar en la rama de correcciones ambiente, esquema y scripts de CRUD.
- [x] Conservar evidencia de CRUD en `docs/evidencia/05_crud.txt`.
- [x] Preparar generador reproducible de 1.199.770 comentarios, con evidencia de reproducibilidad.
- [x] Conservar registro de importación masiva: `07_carga_copy_primera_vez.txt` informa 1.199.770 filas importadas y 0 omitidas.
- [ ] Ejecutar y conservar validación de conteos por partición tras la carga masiva, si se reutiliza esa carga.
- [ ] Repetir carga y validación para demostrar que los totales no cambian.
- [ ] Completar medición de escrituras/s con método, concurrencia, ambiente y limitaciones, si el flujo incluye escrituras.
- [ ] Incorporar la solución a la versión de trabajo, si el flujo del Hito 12 usa Cassandra.
- [x] (irrelevante) Exigir más de 1.000.000 de comentarios como mínimo obligatorio del Hito 12: el volumen se justifica según el escenario y el equipo.

## Hito 7 — Caché de Usuarios y Sesiones

### Comentario original del profesor

> Corrigieron la principal debilidad del Hito 6: ahora hay scripts, pruebas y evidencia real. Para mejorar, deben precisar la fuente de verdad del dato cacheado: el partido P001 se vincula al modelo de Neo4j, pero la caché se reconstruye desde una respuesta simulada de MongoDB. En el próximo hito conviene que cada caché apunte claramente al módulo autoritativo correcto y justificar esa elección.

### Estado y tareas

**Pendiente en `main`; avance parcial en `origin/correcciones`.**

- [x] La rama de correcciones diferencia caché de equipo y resumen de partido, y declara fuente, TTL e invalidación.
- [ ] Definir la autoridad concreta del resumen de partido: Neo4j u otra fuente que realmente contenga y gobierne ese dato.
- [ ] Justificar cualquier copia derivada en MongoDB y su procedencia, si se decide conservarla.
- [ ] Alinear scripts, documentación y evidencia con la autoridad elegida.
- [ ] Demostrar reconstrucción e invalidación de la caché de forma coherente con esa fuente.

## Hito 8 — Series Temporales de Estadísticas en Vivo

### Comentario original del profesor

> La entrega está bien enfocada y mejora claramente la ejecución respecto de hitos anteriores. Para mejorar, deben corregir el análisis de cardinalidad: al incluir sede y fase como tags dependientes de partido_id, estiman combinaciones que en realidad no se materializan. Conviene calcular series con las combinaciones reales del generador y mantener como tags solo dimensiones respaldadas por patrones de consulta concretos.

### Estado y tareas

**Pendiente en ambas ramas revisadas.**

- [ ] Calcular cardinalidad contando tuplas distintas de tags realmente producidas por el generador.
- [ ] Corregir la multiplicación por sedes y fases que dependen del partido, sin tratarlas como dimensiones independientes.
- [ ] Justificar cada tag con consultas concretas; modificar el modelo solo si ese análisis lo requiere.
- [ ] Actualizar documentación, ejemplos y evidencia afectados.

## Hito 9 — Entidades Complejas del Fixture 2030

### Comentario original del profesor

> La entrega está bien resuelta y evidencia herencia, guardado único, navegación, SQL y validaciones. Para mejorar, deben probar realmente la atomicidad ante una falla del árbol: demuestran que un %Save() exitoso persiste Partido y Evento, pero no muestran un hijo inválido que haga fallar el guardado y verifique que tampoco quede persistido el padre. Esa evidencia cerraría mejor RF6 e integridad.

### Estado y tareas

**Pendiente en `main`; no se verificó cierre en la implementación alternativa de `origin/correcciones`.**

- [ ] Crear un Partido nuevo con un Evento hijo inválido.
- [ ] Intentar guardar el árbol desde el padre y registrar el error.
- [ ] Consultar luego la persistencia y comprobar que no quedaron ni el padre ni el hijo de esa operación.
- [ ] Registrar identificadores, estado previo y posterior, comando reproducible y resultado.
- [ ] Guardar evidencia y actualizar la matriz de integridad.

## Hito 10 — API REST Integrada

### Comentario original del profesor

> La entrega está muy completa y bien evidenciada, pero deben reducir la reingeniería de los datos previos: para integrar la API crean instancias nuevas de las seis bases, cambian identificadores de partido y agregan una tabla Cassandra de idempotencia. Eso dificulta demostrar integración real de los hitos existentes. Conviene consumir los modelos previos tal como fueron entregados y limitar los cambios al mínimo necesario para exponerlos por API.

### Estado y tareas

**Pendiente. La devolución está documentada, pero los tres puntos siguen en la implementación de `main`.**

- [ ] Identificar qué versión de cada hito se integrará y registrar su rama/commit.
- [ ] Definir el entorno que consumirá la API, priorizando la reutilización de los módulos anteriores y justificando cualquier instancia de laboratorio adicional.
- [ ] Preservar modelos e identificadores anteriores; resolver correspondencias en la API cuando sea necesario y verificar que correspondan al mismo partido.
- [ ] Retirar la dependencia de `comentarios_idempotencia` y documentar las garantías y limitaciones de reintentos usando las tablas previas, según `docs/correcciones.md`.
- [ ] Ajustar adaptadores, validaciones, scripts y configuración a los modelos elegidos.
- [ ] Actualizar OpenAPI, Postman, pruebas y README, y conservar nueva evidencia de integración real.
- [x] (irrelevante) Exigir levantar los seis motores y cargar todos los datos para el Hito 12: alcanza con los servicios y datos del flujo elegido.

## Hito 11 — Evaluación de la Conectividad

### Comentario original del profesor

> La entrega está muy completa y demuestra conectividad real de los seis motores, API y recuperación de Redis. Deben cerrar la evidencia de la falla controlada: la documentación indica conservar la captura redactada de esa prueba, pero docs/evidencia/capturas_redactadas/ está vacío salvo .gitkeep. Incorporen allí la evidencia ejecutada de caída→503→recuperación, vinculada al commit e5f3949.

### Estado y tareas

**Pendiente. La carpeta señalada sigue conteniendo solamente `.gitkeep`.**

- [x] (irrelevante) Completar la captura histórica del Hito 11 como requisito previo del Hito 12; sigue pendiente para cerrar el Hito 11.
- [x] (irrelevante) Vincular las corridas nuevas del Hito 12 al commit `e5f3949`: deben registrar el commit real utilizado.
