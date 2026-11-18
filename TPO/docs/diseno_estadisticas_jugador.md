# Estadísticas y jugadas de la simulación

Estado: versión 3 implementada para simulaciones nuevas. Las simulaciones de versiones anteriores conservan sus consultas. La integración real con InfluxDB y Neo4j requiere verificación con servicios activos.

## Grano de los eventos

`jugadas_partido` contiene una fila por jugada de un jugador en un partido. Los tags son `partido_id`, `equipo_id`, `jugador_id`, `categoria` y `corrida_id`; este último identifica un intento, evitando mezclar puntos al reiniciar. `evento_id`, `orden`, `minuto` y `resultado` son campos, no tags. Las categorías son `pase`, `tiro`, `gol`, `falta`, `amarilla`, `roja` y `cambio`. El guion actual registra pases exitosos y goles; para el resto usa `registrado`, sin inventar si un tiro fue al arco.

El simulador fija y guarda el instante UTC al iniciar. Cada minuto simulado equivale a un segundo; el timestamp de una jugada es inicio + minuto en segundos + orden en microsegundos. Los timestamps son estables para un reintento de la misma corrida y distintos entre jugadas. El minuto de fútbol se conserva como campo; el timestamp es el tiempo del laboratorio acelerado, no el de un encuentro real. El evento técnico `inicio` inicializa la medición en el minuto cero y se excluye del listado de jugadas.

Las consultas filtran por partido y corrida. La cardinalidad depende de combinaciones reales de partido, equipo, jugador, categoría y corrida; se necesita medirla bajo la carga esperada. No se crean tags por usuario ni ID de jugada. Los lotes por minuto reúnen muestras y eventos en una solicitud; un error marca las estadísticas incompletas.

## Posesión y agregaciones

`estadisticas_jugador_minuto` conserva una muestra por jugador y minuto con segundos sintéticos de posesión. El lote también contiene contadores del guion, pero para la versión 3 **las estadísticas de acciones se agregan desde `jugadas_partido`**. Se agrupa por selección, jugador y minuto; luego se suman los resultados por selección/minuto y jugador/partido. El total de un equipo es la suma de sus jugadores. El gol cuenta como un tiro al arco y un tiro; un tiro sin resultado explícito no se considera al arco. Un pase cuenta como intentado y exitoso según el resultado guardado. Faltas se cuentan por categoría; córners siguen en cero porque el guion no los genera.

La posesión se calcula como `100 × segundos del equipo / segundos de los dos equipos`. En la simulación se distribuyen exactamente 60 segundos por minuto entre ambos equipos; el minuto cero no contiene posesión. La precisión de pases es `100 × pases completados / pases intentados`; si no hay intentos, no hay porcentaje. Los valores son sintéticos, no mediciones reales.

La simulación toma los primeros 11 dorsales por selección y añade protagonistas del guion si hiciera falta. No representa cambios reales ni tiempo efectivo en cancha. Actualmente se usa una corrida por vez por partido; los resultados son de laboratorio.

## Archivo en Neo4j

Al terminar, se verifica que las muestras por jugador estén completas, que las jugadas de Influx coincidan en ID, categoría, jugador, equipo, minuto y orden con el guion, que los contadores sean coherentes y que los goles coincidan con el marcador. Los resúmenes por jugador y selección y las 182 muestras agregadas por selección/minuto se guardan en relaciones con claves estables. Los eventos se relacionan con el partido, el jugador y las jugadas previas; se conserva su categoría y timestamp. Solo después de guardar se marca el archivo completo. Si falta algo o hay una falla, queda pendiente; repetir el archivo no debe duplicar relaciones.

`GET /partidos/{id}/estadisticas` devuelve agregados por selección; `GET /partidos/{id}/estadisticas/jugadores`, totales por jugador; `GET /partidos/{id}/jugadas/temporales`, las jugadas de Influx. Tras archivar, las estadísticas se leen desde Neo4j. `GET /partidos/{id}/historico` consulta el grafo.

El inicio limpia el documento de estado de un intento fallido si el partido sigue programado; un intento activo o finalizado no se reemplaza. Los datos ya guardados en Cassandra e Influx no se borran. La nueva corrida aísla sus puntos de Influx; los comentarios anteriores pueden seguir visibles en la ventana de Cassandra. Si falla la simulación después de pasar el partido a En juego, no se reinicia automáticamente ni se cambia su estado para forzar una nueva corrida.

No hay afirmación de mejora de rendimiento sin medir. Consultas, cardinalidad, escritura, reintentos, archivo y comportamiento de arranque deben comprobarse con InfluxDB y Neo4j reales antes de considerar cerrada la integración.
