# Data Mart propuesto, sin ejecutar

Pregunta: ¿qué partido concentra más comentarios y de qué países provienen?
Fuentes: Neo4j para identidad/etiquetas del partido; Cassandra para comentarios.
Grano: una fila por partido, país y ventana UTC de 30 minutos.

El SQL diseña SQLite como destino local de ejemplo. No se creó ni llenó una base SQLite.
La dimensión conserva IDs y procedencia por fuente. La tabla de hechos almacena totales
recalculados por partición: nunca sumar el mismo lote de nuevo. Registrar cambios del lote
y checkpoint en una transacción, conservando el último lote exitoso si la extracción falla.

Reprocesar las dos ventanas recientes cada minuto es una política propuesta, no implementada.
Para las muestras históricas/sintéticas de 2030 habrá que fijar explícitamente las ventanas;
un job basado únicamente en la fecha real del equipo no las encontrará.

Los 128 totales preparados son expectativas sobre los 1.920 comentarios de archivo;
no son evidencia de ETL ejecutado. Antes de implementar: verificar correspondencias,
particiones, conteos y una segunda corrida sin duplicaciones.

