# Decisiones de diseño — Comentarios masivos (Hito 6)

## El problema real: el partido popular

Si particionáramos solo por `partido_codigo`, un partido con 1M+ comentarios sería una sola partición gigante. Eso es justo lo que la consigna advierte que hay que evitar: todas las escrituras y lecturas de ese partido caerían siempre sobre el mismo conjunto de réplicas, sin importar cuántos nodos tenga el clúster.

## La solución: bucket de tiempo

Se agregó `bucket` (ventana de 10 minutos desde el inicio del partido) como segunda parte de la clave de partición. Un partido de ~130 minutos (90 + descuento + entretiempo, con margen) queda repartido en 13 buckets.

**Los números no son un supuesto sin verificar** — se generó el volumen completo con `scripts/generar_carga_masiva.py` (1.199.770 comentarios, 5 partidos "populares" concentrando el 70%) y se midió: la partición más cargada de todas terminó con **12.923 filas**. Eso está lejos de ser un problema para Cassandra (las guías generales hablan de evitar particiones de cientos de miles de filas o de más de 100MB); da margen incluso para partidos bastante más comentados que los de esta muestra.

Después se cargó ese volumen en la Cassandra real y se contó partición por partición: la más grande quedó en 12.927 filas (las 12.923 de la carga masiva más 4 comentarios de la muestra que caen en el mismo partido y bucket) y la más chica en 1.025. Además, una partición completa de 12.923 filas se leyó ordenada de la más nueva a la más vieja sin `ORDER BY` (ver `docs/rendimiento.md` y `docs/evidencia/07d_verificacion_carga_masiva.txt`).

## Por qué 10 minutos y no otra ventana

- Una ventana más chica (por ejemplo, 1 minuto) multiplicaría la cantidad de particiones sin necesidad — la mayoría quedarían casi vacías fuera de los momentos de gol.
- Una ventana más grande (por ejemplo, 30 minutos) concentraría demasiado en los picos: un gol genera una ráfaga de comentarios en los 2-3 minutos siguientes, y si esa ráfaga cae dentro de una ventana de 30 minutos junto con tráfico normal, la partición del momento pico crece mucho más de lo necesario.
- 10 minutos es un punto intermedio razonable para un partido de fútbol: separa razonablemente los momentos de pico (entretiempo, cada gol) sin generar particiones triviales.

## Duplicación controlada: por qué una tabla y no un índice

Para el historial por usuario se evaluaron dos caminos:

1. **Índice secundario** (`CREATE INDEX ON comentarios_por_partido (usuario_id)`): Cassandra construye el índice de forma local a cada nodo, así que una consulta por `usuario_id` sin conocer `partido_codigo` igual termina consultando todos los nodos del clúster — es un anti-patrón conocido para columnas de alta cardinalidad como un identificador de usuario.
2. **Tabla adicional** (`comentarios_por_usuario`), duplicando el comentario con otra clave de partición.

Se eligió la tabla adicional. El costo que se acepta: cada comentario se escribe dos veces (una por tabla) y cada operación de moderación o borrado tiene que aplicarse en las dos tablas por separado, ya que Cassandra no tiene una transacción multi-tabla real (se documentó explícitamente en `crud.cql`). A cambio, la consulta por usuario queda tan directa como la del feed principal.

## Por qué no TTL en los comentarios

Se decidió no aplicarle TTL a los comentarios: son parte del archivo público del partido, no un dato efímero. Un TTL masivo sobre una tabla de este volumen generaría muchos tombstones (registros de borrado) que Cassandra tiene que procesar en cada compactación, con impacto en lectura y en el uso de disco — la consigna lo advierte explícitamente. Si en el futuro hiciera falta purgar comentarios viejos (por ejemplo, mucho después de terminado el torneo), es una decisión que habría que tomar con más cuidado, evaluando ese costo, y no quedó resuelta en este hito.

## Supuestos de volumen y crecimiento (declarados, no implícitos)

- Hasta 1.000.000+ de comentarios totales en la muestra de 32 partidos, con concentración desigual (algunos partidos muy comentados, la mayoría moderados).
- Máximo observado por partición: ~13.000 filas, con los supuestos de distribución de este hito. Si un partido superara ampliamente ese volumen, la ventana de bucket habría que achicarla (por ejemplo a 5 minutos) para mantener las particiones en un tamaño manejable.
- 50.000 usuarios distintos en la carga de prueba, repartidos de forma pareja — no se modeló el caso de un usuario "hipercomentador" que concentre una fracción desproporcionada de comentarios (posible desbalance en `comentarios_por_usuario`, no evaluado en este hito).

## Qué no llegamos a resolver

- La cola de comentarios reportados pendientes de revisión ("todos los comentarios en estado `reportado`, de cualquier partido") no tiene una tabla propia todavía — con el modelo actual, esa consulta necesitaría recorrer partido por partido. Si la moderación necesita ese panel global, hace falta una tercera tabla particionada por estado.
- No se probó qué pasa con un usuario que comenta muchísimo más que el resto (la partición de `comentarios_por_usuario` para ese caso podría crecer de forma desproporcionada).
