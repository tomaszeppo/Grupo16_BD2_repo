# Hipótesis y optimización

Texto organizado a partir de [Evidencia Hito 12.docx](evidencia/Evidencia%20Hito%2012.docx), conservado completo. Las aclaraciones de alcance separan propuestas y mediciones.

Se implementaron dos variantes de optimización sobre el flujo de inserción de comentarios en Cassandra. Ambas se vinculan con la posible limitación del cliente identificada en la línea base: consumo cercano a un núcleo y presencia de latencias elevadas en una parte de las operaciones.

| Mejora implementada | Descripción y justificación | Hipótesis de mejora |

| --- | --- | --- |

| Reducción de concurrencia — v2.1 | Se redujo de 100 a 50 la cantidad máxima de operaciones simultáneas, manteniendo un proceso y 50.000 escrituras. Busca disminuir la presión generada por las solicitudes en curso. | Una menor concurrencia podría reducir las latencias altas, especialmente el p99, sin perder una proporción importante de throughput. |

| Paralelismo controlado — v2.2 | Se distribuyeron las escrituras entre dos procesos con sesiones independientes y 50 operaciones concurrentes cada uno. Se conserva un máximo global de 100, igual al control de un proceso con concurrencia 100. | Repartir el envío y procesamiento de respuestas entre dos procesos podría aprovechar más núcleos y mejorar el throughput o las latencias si el cliente constituye una limitación. |

Para evaluar la segunda mejora, también se corrigió la generación de datos para que ambos perfiles produzcan los mismos valores por índice global y se incorporó una barrera de inicio, ubicada después de preparar las conexiones, las sentencias y los datos. Estos controles permiten comparar condiciones equivalentes. Se mantuvieron la consulta preparada, las 13 particiones, el esquema y el instrumento de medición.

a fin de resolver lo anterior, se implementaron las siguientes modificaciones

1) se agregó la selección de parámetros según el perfil:

```python
if args.concurrencia is None:
    args.concurrencia = 100 if args.perfil == "A" else 50

if args.procesos is None:
    args.procesos = 1 if args.perfil == "A" else 2

```

Así, --perfil B ejecuta dos trabajadores, cada uno encargado de 25.000 filas y con hasta 50 operaciones en curso. El máximo global continúa siendo 100.

2) Creación explícita de procesos y coordinación

En la función ejecutar(), del mismo archivo, cambiamos la creación del pool.

```python
contexto = multiprocessing.get_context('spawn')
barrera = contexto.Barrier(procesos)

with contexto.Pool(
    procesos,
    initializer=inicializar_worker,
    initargs=(barrera,)
) as pool:
    salidas = pool.map(trabajo, tareas)

```

spawn inicia trabajadores independientes. Cada trabajador conserva la creación de su propia conexión, sesión y sentencia preparada dentro de trabajo(). La barrera coordina el inicio de ambos trabajadores. No se supone que spawn sea más rápido: se utiliza para controlar cómo se crean los procesos.

3) Esperar a que ambos trabajadores estén preparados

En trabajo() incorporamos esta espera inmediatamente antes de comenzar a medir y enviar:

```python
medida = SesionMedida(session, indice, desde)
esperar_inicio()
inicio = time.perf_counter_ns()

resultados = execute_concurrent_with_args(
    medida, insert, params,
    concurrency=concurrencia,
    raise_on_first_error=False
)

```

Esto evita que un proceso empiece a enviar mientras el otro todavía prepara sus datos. También agregué abortar_inicio() para liberar la espera si falla la preparación de un trabajador.

Resultados hipótesis

Corrimos y obtuvimos lo siguiente:

![Captura del documento fuente, bloque 68](evidencia/capturas_redactadas/captura_docx_06.png)

![Captura del documento fuente, bloque 69](evidencia/capturas_redactadas/captura_docx_07.png)

Lo anterior al comparar con la línea base histórica:

| Métrica | Base: 1 proceso × 100 | Modificada: 2 procesos × 50 | Variación |

| --- | --- | --- | --- |

| Tiempo de carga | 7,985 s | 6,136 s | −23,2% |

| Throughput | 6.261 escrituras/s | 8.149 escrituras/s | +30,1% |

| Latencia promedio | 15,870 ms | 12,178 ms | −23,3% |

| p50 | 11,042 ms | 7,957 ms | −27,9% |

| p95 | 18,159 ms | 15,991 ms | −11,9% |

| p99 | 172,385 ms | 112,338 ms | −34,8% |

| Latencia máxima | 438,623 ms | 1.049,573 ms | +139,3%: regresión |

| Escrituras fallidas | 0 | 0 | Sin cambios |

| Registros persistidos | 50.000 | 50.000 | Integridad conservada |

La variante paralela mostró un incremento del throughput del 30,1% y una reducción del p99 del 34,8% respecto de la línea base histórica, manteniendo 50.000 escrituras confirmadas y persistidas sin errores. Sin embargo, la latencia máxima aumentó de 438,623 a 1.049,573 ms, por lo que también se identificó una regresión en el peor caso observado.

El monitor registró una muestra activa del cliente con 184,58% de CPU y 230,1 MiB de memoria, compatible con el uso de más de un núcleo. La cobertura de recursos fue limitada por la corta duración de la prueba y no permite establecer consumo sostenido.

Los resultados son favorables como comparación exploratoria. Para atribuir la mejora al paralelismo y evaluar su repetibilidad, queda pendiente ejecutar el control A con el mismo código v2.2 y repetir ambas condiciones.

Puesto de forma breve, obtuvimos:

30,1% más escrituras por segundo.

23,2% menos tiempo para cargar los 50.000 comentarios.

34,8% menos latencia p99.

Cero errores y todos los registros guardados.

## Registro, trade-off y decisión

La v2.1 reduce concurrencia total a 50: está implementada, pero no se utilizó para la comparación manual del documento. La v2.2 distribuye el presupuesto global 100 entre dos procesos; el soporte multiproceso ya existía y se corrigieron determinismo, coordinación y trazabilidad. Las hipótesis previas y los siete campos de cada modificación se conservan en [M01](../versiones/v2.1_candidata_c50/docs/registro_modificacion_M01.md) y [M02](../versiones/v2.2_candidata_paralelo/docs/registro_modificacion_M02.md).

Más procesos y sesiones agregan complejidad, conexiones y costo de preparación. El máximo de latencia empeoró pese a mejorar throughput y p99. La decisión es conservar la variante como candidata favorable para este laboratorio, sin afirmar causalidad ni escalabilidad de producción. Falta repetir manualmente A/B con el mismo código.

Las seis ejecuciones automáticas adicionales de `resultados/comparativas/` se conservan como evidencia suplementaria; no se sustituyen por la corrida manual ni se mezclan con los porcentajes del DOCX.
