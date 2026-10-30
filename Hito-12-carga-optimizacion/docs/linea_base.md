# Línea base

Texto organizado a partir de [Evidencia Hito 12.docx](evidencia/Evidencia%20Hito%2012.docx), conservado completo. Las aclaraciones de alcance separan propuestas y mediciones.

Referencia: `base-20261030-002022`, código congelado en `versiones/v2.0_base/`. La comparación usa esta línea base histórica; no es un control contemporáneo repetido manualmente.

Vamos a probar la escritura de comentarios del Fixture 2030 en el módulo Cassandra. Un proceso de prueba generará 50.000 comentarios sintéticos y los enviará con hasta 100 escrituras simultáneas, utilizando un proceso. La prueba finalizará cuando se hayan intentado todas las inserciones. Registraremos escrituras exitosas, fallidas, duración y comentarios escritos por segundo, y después verificaremos los datos guardados.

El entorno y linea base es el siguiente es el siguiente:

| Aspecto | Definición reproducible |

| --- | --- |

| Qué probamos | Inserción de comentarios sintéticos del Fixture 2030 en el módulo Cassandra del Hito 6. |

| Consumidor | Un proceso de benchmark que representa publicaciones de comentarios. |

| Recorrido | Cliente Python → driver Cassandra → tabla comentarios_por_partido. La API y Neo4j no intervienen. |

| Volumen | 50.000 comentarios, generados por el propio benchmark. |

| Datos | 5.000 usuarios ficticios, diez comentarios por usuario, contenido fijo y valores generados de manera determinista con semilla 2030. |

| Distribución | 13 particiones: dos reciben 3.847 registros y once reciben 3.846. Cada corrida utiliza un identificador H12 exclusivo. |

| Concurrencia | Hasta 100 operaciones en curso, con un proceso. Se registra también el pico observado. |

| Rampa y sostenimiento | Sin rampa. El cliente repone operaciones mientras quedan pendientes; la concurrencia disminuye al terminar el lote. |

| Duración | Hasta completar los intentos, sufrir un fallo fatal o recibir una interrupción. Los errores individuales se registran sin detenerse en el primero. |

| Latencia por operación | Desde que el cliente inicia el envío hasta recibir confirmación o error. Incluye driver, red y posibles reintentos; no es tiempo puro del servidor. |

| Estadísticos | Mínima, promedio, p50, p95, p99 y máxima. Se separan operaciones confirmadas y errores, y se conservan las muestras individuales. |

| Throughput | Escrituras confirmadas por segundo durante la carga. El tiempo total del cliente se informa por separado. |

| Errores | Cantidad, porcentaje y clase de excepción. Se distinguen errores, operaciones inconclusas y operaciones no intentadas. |

| Recursos y estabilidad | CPU/RAM del host y contenedores, red y BlockIO mediante muestreo; resultados por segundo para observar pausas, variaciones y errores. |

| Criterio de éxito | 50.000 confirmaciones, cero errores o inconclusas y conteos persistidos iguales a los esperados en las 13 particiones. |

| Reproducción | Misma versión instrumentada, hashes, parámetros, reglas de generación y condiciones del entorno; nueva carpeta e ID por corrida, conservando los anteriores. |

| Limitaciones | Una tabla y datos controlados. No reproduce todo el tráfico del TPO, la popularidad entre partidos ni el recorrido HTTP completo. |

Ejecución inicial

Ejecutamos y obtuvimos el siguiente resultado

![Captura del documento fuente, bloque 42](evidencia/capturas_redactadas/captura_docx_03.png)

![Captura del documento fuente, bloque 43](evidencia/capturas_redactadas/captura_docx_04.png)

En cuanto al hardware, monitoreando obtuvimos los siguientes resultados :

![Captura del documento fuente, bloque 45](evidencia/capturas_redactadas/captura_docx_05.png)

| Recurso | Máximo observado |

| --- | --- |

| CPU del host | 36,77 % |

| CPU de Cassandra | 398,28 % |

| RAM de Cassandra | 4,515 GiB |

| CPU del cliente | 98,68 % |

| RAM del cliente | 299,9 MiB |

Los resúmenes verificables están en [resultados de base](evidencia/resultados_linea_base.json); las muestras por operación se conservan comprimidas en la carpeta de la corrida. Docker interpreta 100% de CPU como aproximadamente un núcleo, no como toda la máquina. El detalle del entorno pertenece a la evidencia, no a los requisitos generales.
