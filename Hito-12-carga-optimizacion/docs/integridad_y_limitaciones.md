# Integridad y limitaciones

Texto organizado a partir de [Evidencia Hito 12.docx](evidencia/Evidencia%20Hito%2012.docx), conservado completo. Las aclaraciones de alcance separan propuestas y mediciones.

## Datos y representatividad

Seleccionamos un conjunto sintético y controlado para obtener una primera medición reproducible del módulo de comentarios. Su tamaño permite ejecutar y verificar la prueba, pero los resultados se limitan a este volumen y distribución; no permiten afirmar que el sistema soporte automáticamente la carga total proyectada del Fixture 2030.Los datos a cargar tienen las siguientes características:

| Punto  | definición |

| --- | --- |

| Origen | Datos ficticios generados por el benchmark del Hito 6, adaptado para el Hito 12. No contienen información de usuarios reales. |

| Método de generación | El script construye identificadores, usuarios, contenido, fechas, estado de moderación y likes mediante reglas deterministas y semilla fija. |

| Distribución | 50.000 comentarios repartidos entre 13 particiones: dos reciben 3.847 registros y las otras once, 3.846. Se utilizan 5.000 identificadores de usuario, con diez comentarios por usuario. |

| Representatividad | Permite estudiar escrituras simultáneas sobre el modelo de comentarios y comprobar su persistencia. |

| Limitaciones | El contenido es repetitivo, los usuarios tienen una distribución uniforme y los buckets se asignan cíclicamente. No reproduce fielmente ráfagas por goles, horarios reales, partidos con distinta popularidad ni todo el volumen proyectado del TPO. |

## Persistencia

Las verificaciones de la línea base y de la corrida B registran 50.000 confirmadas y 50.000 guardadas; cero fallidas, inconclusas, no intentadas o errores de fase; 13 conteos correctos. Dos buckets tienen 3.847 y once tienen 3.846. La igualdad de conteos no prueba por sí sola igualdad de todo el contenido. La demo del Data Mart además comprueba unicidad del identificador de comentario, campos requeridos y total de agregados.

## Límites de la comparación

La variante paralela mostró un incremento del throughput del 30,1% y una reducción del p99 del 34,8% respecto de la línea base histórica, manteniendo 50.000 escrituras confirmadas y persistidas sin errores. Sin embargo, la latencia máxima aumentó de 438,623 a 1.049,573 ms, por lo que también se identificó una regresión en el peor caso observado.

El monitor registró una muestra activa del cliente con 184,58% de CPU y 230,1 MiB de memoria, compatible con el uso de más de un núcleo. La cobertura de recursos fue limitada por la corta duración de la prueba y no permite establecer consumo sostenido.

Los resultados son favorables como comparación exploratoria. Para atribuir la mejora al paralelismo y evaluar su repetibilidad, queda pendiente ejecutar el control A con el mismo código v2.2 y repetir ambas condiciones.

## Límites analíticos

Para el laboratorio preparamos una proyección local en SQLite. Los identificadores H12 representan pruebas, no partidos reales. Como nuestros datos sintéticos abarcan un único minuto, la demostración permite comprobar la extracción, los agregados y su procedencia, pero no demostrar picos reales entre minutos ni comparar popularidad entre partidos. La propuesta cubre el diseño solicitado.

Ejecutamos una extracción de los comentarios de la corrida terminada en Cassandra y generamos una proyección local en SQLite. Se integraron las 13 particiones y se comprobó que sus conteos coincidieran con los esperados.

La consulta SQL devolvió una fila correspondiente al partido de prueba y al minuto 2030-06-08T18:00:00+00:00: 50.000 comentarios, 5.000 usuarios distintos, 50.000 comentarios visibles, cero en otros estados y 249.661 likes acumulados. Una segunda consulta confirmó que la suma de comentarios de la proyección coincide con los 50.000 registros extraídos.

Esto valida la extracción y los conteos del resumen para este conjunto de datos. No demuestra diferencias de actividad entre partidos o minutos, porque la prueba contiene un único partido sintético y un solo minuto. La actualización periódica, el tratamiento de datos tardíos y la recuperación ante fallas parciales quedan como políticas propuestas, todavía no probadas de extremo a extremo.

No hubo prueba del recorrido HTTP completo, carga equivalente PostgreSQL, fallas distribuidas ni garantía de producción. Un timeout no implica ausencia de escritura. Se conservaron las muestras y se excluye del análisis útil el registro de recursos del cliente con memoria/PIDs en cero al salir. No se borraron datos para repetir.
