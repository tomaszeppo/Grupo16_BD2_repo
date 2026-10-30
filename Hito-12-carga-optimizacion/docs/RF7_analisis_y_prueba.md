# RF7 - Limitación posible, hipótesis y prueba propuesta

Fecha: 30/10/2026. Se incorpora también la sección 5.5: la hipótesis y el protocolo
se documentan **antes** de aplicar el cambio. No se ejecutó una nueva carga ni se
modificó el benchmark, el esquema o los datos para realizar este análisis.

La [evaluación previa ampliada](hipotesis_previa_optimizacion.md) revisa todas las
técnicas solicitadas, excepto Data Mart. Por indicación del usuario, los cambios futuros
se prepararán en otra versión: `versiones/v2.0_base/` queda histórica y la candidata
se creará después, sin sobrescribir código, configuración ni evidencia de referencia.

## 1. Revisión de las dos ramas

Se actualizó el remoto con `git fetch --all` y se revisaron `origin/main@f0b228e` y
`origin/correcciones@27f28e1`, incluyendo documentación, scripts y el mapa H12.

| Rama / archivo | Antecedente encontrado | Alcance |
|---|---|---|
| main / arquitectura-hito-12.html, sección «Qué medimos y dónde lo miramos» | Advierte que un generador saturado puede explicar un techo de rendimiento y propone observar los recursos del cliente | Es una recomendación de diseño; no analiza una corrida de comentarios |
| correcciones / Hito-6-fixture2030-cassandra/scripts/prueba_rendimiento.py, encabezado | Justifica varios procesos por un posible límite de CPU de un proceso Python | Es un antecedente técnico, no una demostración de nuestra hipótesis actual |
| correcciones / Hito-6-fixture2030-cassandra/docs/rendimiento.md | Enumera CPU del cliente, CPU del nodo y disco como posibles límites; describe problemas históricos de COPY bajo carga del entorno | Su tabla del benchmark específico sigue pendiente; COPY y nuestra escritura por driver son cargas diferentes |
| correcciones / Hito-7-fixture2030-redis/docs/rendimiento.md, limitaciones | Reconoce el costo de un cliente secuencial | Otro motor y patrón de acceso: contexto, no prueba del cuello actual |

**Resultado:** el posible límite del generador ya tiene antecedentes en las ramas, pero
no se encontró un análisis RF7 que relacione hipótesis, mediciones y prueba controlada
con la corrida actual. Por eso se completa aquí con los datos reales recopilados.

## 2. Evidencia de nuestra primera línea base

Corrida: `base-20261030-002022`, benchmark `2.0-instrumentado`, tabla
`fixture2030.comentarios_por_partido`, 50.000 intentos, un proceso, concurrencia máxima 100,
sin rampa. Las versiones y hashes reales están en `entorno_instrumentado.json` e
`escrituras.jsonl`. El código H12 no estaba versionado aún: el hash identifica la copia
local; el commit por sí solo no la identifica.

| Observación | Valor registrado | Interpretación permitida |
|---|---|---|
| Confirmadas / errores / inconclusas | 50.000 / 0 / 0 | La corrida completó los intentos sin errores de cliente |
| Persistencia | 50.000, coinciden las 13 particiones | El chequeo de cantidades coincide con las confirmaciones |
| Tiempo de carga / throughput | 7,985 s / 6.261,365 confirmadas/s | Resultado de una corrida corta, no capacidad máxima demostrada |
| Latencia promedio / p95 / p99 | 15,870 / 18,159 / 172,385 ms | Hay una cola de respuestas lentas; no se atribuye su causa solo por el percentil |
| Mínima / máxima | 3,042 / 438,623 ms | Existe variación entre operaciones |
| Muestras >100 ms | 900 de 50.000 (1,8%) | Las demoras no están únicamente al inicio: aparecen en los ocho intervalos de la carga |
| Pico lógico de concurrencia observado | 100 | El cliente alcanzó el límite configurado |
| CPU cliente, muestras útiles | 80,33%; 91,77%; 98,68%; 98,07% | En tres de cuatro muestras se acercó al uso de un núcleo |
| CPU Cassandra, máximo observado | 398,28% en escala Docker | Aproximadamente cuatro núcleos; no 398% del host completo |
| RAM cliente / Cassandra, máximos observados útiles | 299,9 MiB / 4,515 GiB | Memoria observada; por sí sola no demuestra presión, swapping ni pausas de GC |
| CPU host, máximo de esas muestras | 36,77% global | El host completo no figura al 100%; esto no descarta un recurso o hilo particular saturado |

El monitor tiene cinco registros con estado cliente running, pero el último cruza su
salida y devuelve cliente con PIDs 0 y memoria 0. Se excluye de los máximos útiles del
cliente. Las cuatro ventanas restantes se superponen con la carga. Con muestreo de unos
dos segundos y solo ocho segundos de carga, la cobertura es limitada.

## 3. Limitación posible e hipótesis técnica (antes del cambio)

**Limitación posible:** el cliente Python de un proceso, con 100 escrituras en curso y
callbacks instrumentados, puede contribuir al límite de generación/procesamiento de
respuestas y a la cola de latencias observada. La instrumentación, el driver y la red
forman parte del camino medido, no solo Cassandra.

**Hipótesis H1:** reducir de 100 a 50 las operaciones concurrentes del mismo cliente
reducirá la presión de solicitudes/respuestas pendientes y el p99, manteniendo una
tasa de escritura similar y la integridad. Si el nivel 100 ya no produce un beneficio
material de throughput, sostener menos operaciones en vuelo podría resultar más conveniente.

La CPU cercana a un núcleo y la cola de latencias justifican investigar esta hipótesis;
**no permiten afirmar que el cliente sea el único cuello**, que el GIL sea la causa
demostrada, ni que Cassandra, disco, red o pausas del entorno estén descartados.
Los picos tardíos tampoco se explican automáticamente como calentamiento inicial.

## 4. Prueba controlada para relacionar la hipótesis con la evidencia

| Condición | A: referencia | B: cambio propuesto |
|---|---|---|
| Filas | 50.000 | 50.000 |
| Concurrencia por proceso | 100 | 50 |
| Procesos | 1 | 1 |
| Rampa / calentamiento separado | 0 / no | 0 / no |
| Datos y generación | Mismo código, semilla 2030, usuarios, campos y distribución | Iguales; cambia solamente el ID exclusivo de corrida |
| Driver / esquema / recursos | Misma versión, timeout, retry policy, tabla y asignación de recursos | Sin cambios |
| Instrumentación | 2.0, muestras individuales y monitor activo | Misma instrumentación y frecuencia |

La única modificación experimental es el parámetro `--concurrencia 50` del perfil B.
Se mantiene un proceso para conservar exactamente las reglas y el orden de generación.
No se cambian índices, consulta, particionado, pool, reintentos, timeout ni caché a la vez.

### Procedimiento propuesto, no ejecutado

1. Registrar esta hipótesis y `config/prueba_RF7_concurrencia.json` antes de aplicar B.
2. Conservar la corrida actual como evidencia exploratoria que originó H1.
3. Hacer una nueva pareja de referencia A/B bajo el mismo protocolo; para una conclusión
   más defendible, planificar tres repeticiones por condición en orden A1-B1-B2-A2-A3-B3.
   Son seis corridas nuevas (300.000 escrituras adicionales), no ejecutadas ni autorizadas
   automáticamente por la existencia de este documento.
4. Crear carpeta, nombre de contenedor e ID H12 nuevos para cada corrida, con identificadores
   de igual longitud. Nunca reutilizar las particiones de esta línea base ni borrar datos.
5. Generar datos por las mismas reglas, cambiando solo el namespace de corrida. Confirmar
   código/hash, 50.000 filas, 5.000 usuarios y distribución idéntica en cada ejecución.
6. Iniciar el monitor antes de cada carga. Mantener el resto del entorno lo más constante
   posible y registrar otros programas, recursos asignados y eventos del motor.
7. Conservar todos los resultados, incluidos errores y corridas parciales. Verificar las
   trece particiones tras cada corrida. No seleccionar únicamente la mejor ejecución.
8. Comparar por corrida throughput, p50/p95/p99, máximos, errores, CPU/RAM cliente y motor,
   picos en curso y las series temporales. No promediar percentiles para simular un
   percentil global: informar mediana y rango de los percentiles por corrida.
9. Evaluar si la caída de p99 aparece de forma consistente sin una pérdida significativa
   de throughput. Correlacionar con los recursos; una mejora no aísla por sí sola si el
   costo estaba en el cliente o en otro componente del recorrido.

El orden alternado reduce el sesgo temporal, pero no restaura un estado idéntico de disco,
memtables, cachés o compactaciones. Como conservamos todos los datos, la tabla crecerá;
registrar ese crecimiento y los procesos de fondo como límites de la comparación. No
vaciar tablas ni reiniciar motores solo para fabricar una comparación aparentemente limpia.

### Criterios previos de decisión propuestos por el equipo

- Integridad obligatoria: todas las corridas consideradas deben conservar cantidades
  correctas y tener cero errores/inconclusas/fallos de fase. Si aparecen, analizarlos;
  no ocultarlos ni declararlos equivalentes.
- Aceptación inicial del cambio: mediana del p99 de B al menos 20% menor que la de A,
  mediana del throughput de B al menos 95% de A y mejora de p99 en al menos dos de las
  tres parejas. Los porcentajes son una tolerancia propuesta, **no una exigencia del profesor**.
- Si B reduce mucho el throughput, no mejora el p99 o los resultados son inconsistentes,
  rechazar H1 en esos términos o declararla no concluyente; conservar la configuración A
  como referencia hasta revisar otra hipótesis.
- Si la variación entre repeticiones es comparable a la diferencia A/B, no atribuir causalidad;
  ampliar la observación y analizar cliente, servidor, instrumentación y entorno por separado.

## 5. Registro de modificación según la sección 5.5

| Campo exigido | Registro actual |
|---|---|
| Problema / hipótesis | H1: presión de concurrencia del cliente de un proceso y cola de latencias |
| Cambio implementado | **Ninguno aplicado al benchmark ni a la línea base**. B propone concurrencia 50 |
| Archivos / configuración afectados | Nuevo protocolo `config/prueba_RF7_concurrencia.json`; al ejecutar B cambiará el argumento de concurrencia, no el esquema ni el código medidor |
| Costo o riesgo | Menor throughput, más tiempo por lote; seis repeticiones agregan datos, muestras y costo de ejecución; cambios del entorno pueden sesgar la comparación |
| Prueba posterior ejecutada | Pendiente; se propone el protocolo A/B anterior |
| Resultado medido | Solo A exploratoria: 6.261,365 escrituras/s y p99 172,385 ms, integridad cumplida. No hay resultado B |
| Decisión final | Pendiente de medición y comparación; no se declara una mejora demostrada |

La lista de técnicas de 5.5 no obliga a aplicar todas. Se elige concurrencia por su relación
con esta evidencia. No se agrega una caché a un flujo de escritura sin una necesidad justificada.

## 6. Evidencia y trazabilidad

Fuentes de esta corrida, relativas a la raíz H12:

- `resultados/base/base-20261030-002022/entorno_instrumentado.json`.
- `resultados/base/base-20261030-002022/escrituras.jsonl`.
- `resultados/base/base-20261030-002022/escrituras.operaciones.p00.jsonl`.
- `resultados/base/base-20261030-002022/recursos.jsonl`.
- `resultados/base/base-20261030-002022/verificacion.json`.

El resumen derivado `resultados/base/base-20261030-002022/analisis_RF7.json` registra
hashes y cálculos de esta lectura. No modifica los datos crudos. La verificación por
conteos no certifica todo el contenido semántico ni el comportamiento de la plataforma completa.
