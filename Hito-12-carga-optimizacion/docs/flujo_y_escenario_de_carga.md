# Flujo y escenario de carga

Texto organizado a partir de [Evidencia Hito 12.docx](evidencia/Evidencia%20Hito%2012.docx), conservado completo. Las aclaraciones de alcance separan propuestas y mediciones.

## Alcance efectivamente medido

La prueba ejecutada utiliza cliente Python → driver Cassandra → `comentarios_por_partido` del Hito 6. No mide API HTTP ni Neo4j. La descripción funcional inicial del documento se conserva como contexto, no como recorrido probado. El millón de comentarios y la tasa proyectada no son mediciones del laboratorio.

## Flujo funcional inicialmente seleccionado

Elegimos el flujo de publicar y consultar comentarios de los partidos del fixture 2030 dado que el comportamiento de los comentarios implica gran cantidad de operaciones simultaneas y picos concentrados en determinados partidos, lo cual nos permite estudiar qué ocurre en el recorrido completo (aplicación → API → bases) para poder encontrar un cuello de botella y encontrar una posible solución

Para lo anterior, vamos a utilizar los endpoints de comentarios definidos en hitos anteriores

¿Quién genera la operación?

Un hincha desde la aplicación. Durante las pruebas, un generador de carga simulará esas consultas y publicaciones.

¿Qué datos recibe?

Para publicar, recibe el identificador del partido, país del hincha, identificador y nombre del usuario, contenido del comentario y una clave para identificar los reintentos. Para consultar, recibe partido, país, ventana de tiempo y parámetros de paginación.

¿Qué fuentes utiliza?

Al publicar, primero consulta Neo4j para comprobar que el partido exista y después guarda el comentario en Cassandra. La consulta de comentarios se resuelve en Cassandra, por partido, país y ventana de 30 minutos.

¿Qué tipo de operación es?

Se realizan operación de lectura (recuperar paginas de comentarios recientes en tiempo real) y escritura (Publicar comentarios)

¿Qué respuesta esperamos?

Esperamos una respuesta 201 si es nuevo, 200 si es un reintento reconocido. Al consultar, esperamos HTTP 200 con los comentarios mas recientes y un cursos para continuar

¿Qué volumen y frecuencia proyectamos?

Se plantean más de un millón de comentarios por partido, con especial intensidad en goles/jugadas importantes. Alrededor de 185 comentarios por segundo

¿Cuándo consideramos que fue exitosa?

Cuando el comentario aceptado fue guardado y puede recuperarse en su particion correspondiente

¿Qué errores registramos?

Datos inválidos (422), partido inexistente al publicar (404), conflictos con la clave de reintento (409), dependencia no disponible (503), timeout (504) y errores inesperados (500). También registraremos demoras, operaciones fallidas y posibles inconsistencias, usando el request_id para seguir cada pedido.

## Escenario cerrado para el experimento

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

![Captura del documento fuente, bloque 28](evidencia/capturas_redactadas/captura_docx_01.png)

![Captura del documento fuente, bloque 29](evidencia/capturas_redactadas/captura_docx_02.png)

Vamos a cargar datos para la prueba con la siguiente configuración

| Elemento  | Definición  |

| --- | --- |

| Volumen de datos | 50.000 comentarios sintéticos |

| Cantidad o tasa de operaciones | 50.000 inserciones; la tasa obtenida se medirá |

| Concurrencia | Hasta 100 escrituras en curso, con un proceso |

| Duración | Variable: hasta completar los 50.000 intentos; se registra el tiempo real |

| Ramp-up | Sin rampa: se utiliza directamente la concurrencia configurada |

| Sostenimiento | Se mantiene el límite de 100 operaciones en curso mientras quedan escrituras por enviar; disminuye al terminar el lote |

| Finalización | Se completan los intentos o la ejecución termina por error o interrupción |

El script se encuentra dentro de los archivos del hito 12.

Seleccionamos un conjunto sintético y controlado para obtener una primera medición reproducible del módulo de comentarios. Su tamaño permite ejecutar y verificar la prueba, pero los resultados se limitan a este volumen y distribución; no permiten afirmar que el sistema soporte automáticamente la carga total proyectada del Fixture 2030.Los datos a cargar tienen las siguientes características:

| Punto  | definición |

| --- | --- |

| Origen | Datos ficticios generados por el benchmark del Hito 6, adaptado para el Hito 12. No contienen información de usuarios reales. |

| Método de generación | El script construye identificadores, usuarios, contenido, fechas, estado de moderación y likes mediante reglas deterministas y semilla fija. |

| Distribución | 50.000 comentarios repartidos entre 13 particiones: dos reciben 3.847 registros y las otras once, 3.846. Se utilizan 5.000 identificadores de usuario, con diez comentarios por usuario. |

| Representatividad | Permite estudiar escrituras simultáneas sobre el modelo de comentarios y comprobar su persistencia. |

| Limitaciones | El contenido es repetitivo, los usuarios tienen una distribución uniforme y los buckets se asignan cíclicamente. No reproduce fielmente ráfagas por goles, horarios reales, partidos con distinta popularidad ni todo el volumen proyectado del TPO. |
