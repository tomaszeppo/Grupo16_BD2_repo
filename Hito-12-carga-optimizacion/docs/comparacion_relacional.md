# Comparación con una alternativa relacional

Texto organizado a partir de [Evidencia Hito 12.docx](evidencia/Evidencia%20Hito%2012.docx), conservado completo. Las aclaraciones de alcance separan propuestas y mediciones.

Se compara el flujo de inserción de comentarios del Fixture 2030 en Cassandra con una alternativa relacional en PostgreSQL. La comparación considera el acceso a los datos, las operaciones, las garantías y las condiciones de conveniencia de cada modelo.

| Aspecto solicitado | Cassandra: implementación analizada | PostgreSQL: alternativa relacional |

| --- | --- | --- |

| Estructura de datos | Tabla comentarios_por_partido, particionada por partido y bucket, con comentarios ordenados por comentario_id. | Tabla comentarios, con clave primaria e índice compuesto por partido, bucket y fecha; posibles claves foráneas a partidos y usuarios. |

| Patrón de acceso | Inserciones frecuentes y consultas dirigidas a un partido y bucket determinados. | Inserciones y consultas por partido; posibilidad de relacionar comentarios con usuarios y partidos mediante JOIN. |

| Operaciones involucradas | 50.000 INSERT individuales mediante sentencia preparada y ejecución concurrente. SELECT COUNT por partición para verificar persistencia. | INSERT parametrizados y concurrentes, SELECT COUNT para verificar registros y SELECT con filtros e índices para recuperar comentarios. |

| Garantías esperadas | Confirmaciones según la consistencia configurada. La prueba contrastó confirmaciones con registros persistidos; las relaciones entre entidades se validan desde la aplicación. | Transacciones ACID, unicidad, claves foráneas y restricciones para mantener integridad; posibilidad de operaciones atómicas entre varias tablas. |

| Condiciones de conveniencia | Cuando predominan escrituras distribuidas y consultas conocidas por clave de partición, sin necesidad de JOIN. | Cuando se necesitan relaciones, consultas variadas y transacciones que involucren comentarios, usuarios y partidos. |

## Alcance de la comparación

La unidad relacional sería un comentario, relacionado por claves foráneas con usuario y partido. Los JOIN se necesitan para enriquecer el reporte, no para cada INSERT. El índice por partido, bucket y fecha ayuda a recuperar comentarios y tiene costo de mantenimiento en escritura. Al crecer volumen/concurrencia deben evaluarse índices, conexiones, almacenamiento y posible particionamiento. El modelo relacional simplifica restricciones y transacciones entre entidades; Cassandra exige modelar por acceso y mantener relaciones desde la aplicación.

No se ejecutó PostgreSQL ni una carga relacional equivalente: no se comparan velocidades entre motores. La proyección SQLite del Data Mart es un resumen analítico y no equivale al benchmark de escrituras.
