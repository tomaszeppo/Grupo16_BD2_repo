# Comparación exploratoria del documento

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

Valores exactos y variaciones recalculadas: [CSV](tablas_o_graficos.csv). Fuente: resúmenes y verificaciones de las dos corridas identificadas; no se mezclan con las seis corridas automáticas suplementarias.
