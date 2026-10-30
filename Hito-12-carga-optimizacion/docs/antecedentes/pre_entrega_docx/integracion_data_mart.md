# Data Mart de actividad de comentarios - RF12, RF13, RNF12 y 5.7

Propuesta v1. Fuente normativa: Hito 12 - Requisitos Tecnicos, secciones 5.7 y 6,
RF12/RF13 y RNF12. La consigna exige una propuesta coherente documentada, no un BI
completo. Diseno documentado y demostracion preparada; extraccion real NO ejecutada
por el asistente. No se alteran versiones del benchmark ni datos operacionales.

## Pregunta y valor

**Que partidos y minutos concentran mas comentarios y usuarios activos, y que
volumen de comentarios visibles o de otros estados presentan?**

Ayuda a identificar picos de participacion y orientar capacidad y trabajo de moderacion.
Los otros estados no se interpretan automaticamente como pendientes: pueden incluir
rechazados, desconocidos u otros valores. No mide sentimientos ni popularidad causal.

## Contrato de la vista y procedencia

Grano: una fila por `(partido_codigo, minuto_utc)` dentro de una extraccion identificada.
El ID de partido funciona como dimension degenerada; el minuto es la dimension temporal.
Una version de extraccion no se suma con otra: son fotos alternativas de la misma fuente.

| Dato analitico | Procedencia exacta | Transformacion |
|---|---|---|
| partido_codigo | Cassandra `fixture2030.comentarios_por_partido.partido_codigo` | Conservar clave de negocio sin transformar H12 en partido real |
| minuto_utc | `creado_en` | Normalizar a UTC y truncar segundos/microsegundos |
| comentarios | `comentario_id`, `bucket`, clave del partido | Contar comentarios unicos del partido, integrando todos sus buckets |
| usuarios_activos | `usuario_id` | COUNT DISTINCT dentro del partido y minuto; no sumar usuarios entre minutos |
| comentarios_visibles | `estado_moderacion` | Contar exactamente estado `visible` |
| comentarios_otro_estado | `estado_moderacion` | Total menos visibles; no equiparar a cola pendiente |
| likes_total | `likes` | Sumar valores vigentes observados; no significa likes nuevos del minuto |
| procedencia y frescura | Registro del benchmark y metadatos de extraccion | Guardar hash del registro/script, fuente, partido, inicio/fin, conteos y hash de salida |

No se requiere consultar todas las bases: para esta pregunta basta Cassandra. Una
ampliacion podria enriquecer el ID con equipos/estadio desde Neo4j mediante una
correspondencia validada de codigo de partido. Eso no esta implementado ni es necesario
para responder la pregunta elegida. Los IDs H12 no tienen esa correspondencia: no se
inventan equipos ni se asignan sus comentarios a partidos reales.

## Extraccion, transformacion y publicacion propuestas

1. Mantener un catalogo explicito de partidos y sus particiones; evitar escaneos globales.
   En la demo el registro de una corrida cerrada proporciona host, keyspace e ID H12,
   y se leen sus 13 buckets mediante SELECT preparado y paginas de 1.000 filas.
2. Leer solamente los campos necesarios, sin contenido del comentario. La agregacion
   se realiza fuera de la fase medida del benchmark y sin agregar trabajo al request de
   publicacion. En produccion se limitarian recursos, volumen y duracion del extractor.
3. Agrupar por fecha de evento UTC, no por la hora del benchmark ni por el numero de
   bucket. El benchmark reparte buckets ciclicamente: no son minutos de un partido.
4. Validar unicidad `(partido, comentario_id)` al integrar buckets, valores requeridos,
   conteos por particion, total, suma de grupos y descomposicion visibles/otros.
   Un duplicado o dato invalido detiene la publicacion y conserva evidencia del fallo.
5. Escribir una nueva version de la proyeccion en staging; validar y publicar solo al
   completar el lote. La demo usa un archivo SQLite nuevo y `validacion.json` como
   marca de version utilizable. La escritura SQL usa una transaccion; archivos parciales
   se conservan y no se consumen. No se ejecuta INSERT, UPDATE ni DELETE en Cassandra.
6. En un destino de produccion, publicar una version completa validada cambiando la
   referencia a la version vigente transaccionalmente. Conservar la anterior. No acumular
   nuevamente los mismos conteos al repetir un lote.

## Frecuencia, retraso y recuperacion (propuesta, no servicio desplegado)

| Aspecto | Politica |
|---|---|
| Frecuencia | Cada cinco minutos, fuera del camino de escritura; la demo se ejecuta manualmente sobre una corrida cerrada |
| Retraso aceptable | Objetivo de hasta diez minutos desde disponibilidad del dato en origen; no es una garantia medida. Mostrar fecha de extraccion y alertar al excederlo |
| Datos tardios y cambios | Recalcular partidos activos y una ventana de revision de treinta minutos; cambios mas antiguos requieren backfill explicitamente solicitado. Releer particiones completas necesarias: no asumir que el bucket sintetico permite filtrar por minuto |
| Duplicados/reintento | Clave natural del agregado partido/minuto; reemplazo por nueva version completa, no incremento ciego. Duplicados de comentario en origen provocan rechazo de publicacion |
| Faltantes | Fecha, usuario o likes invalidos impiden publicar la demo; registrar causa y mantener ultima version valida. Enriquecimientos opcionales faltantes permanecen sin correspondencia |
| Falla parcial | Conservar version anterior y evidencia del lote fallido; reintentar a una carpeta/version nueva y publicar solamente cuando se validen todos los grupos |
| Consistencia | Eventual respecto de Cassandra. Una lectura de varias particiones con escrituras concurrentes no es un snapshot atomico; el laboratorio exige corrida cerrada sin modificaciones. En produccion se necesita reconciliacion posterior y una politica de corte explicita |

La frecuencia de cinco minutos, ventana de treinta y objetivo de diez minutos son
decisiones del equipo, no valores impuestos por el profesor. No hay un scheduler
configurado ni se implemento el refresco incremental de produccion.

## Diferencia entre operacional y analitico

| Consulta operacional | Consulta de la proyeccion |
|---|---|
| Lee comentarios individuales en particiones Cassandra; ideal para recuperar comentarios por partido/bucket | Lee filas ya agregadas por partido/minuto mediante SQL |
| Contiene el detalle actual disponible en origen | Contiene una fotografia validada, con posible retraso |
| Un reporte exige recorrer y agregar comentarios | El reporte reutiliza los agregados sin repetir lecturas sobre Cassandra |
| No duplica el resumen analitico | Duplica medidas y agrega costo de ETL, almacenamiento, validacion y mantenimiento |

No se midio una mejora de latencia analitica. La lectura/agregacion de la demo no debe
compararse con la duracion de las escrituras: son operaciones diferentes.

## Demostracion y limites de los datos existentes

Archivos: `datamart/v1_actividad_comentarios/`. El script extrae de Cassandra real,
no reconstruye filas a partir del generador ni trata confirmaciones como contenido.
SQLite es una demostracion local de proyeccion relacional, no un servidor BI instalado.

Para la corrida manual B de 50.000 comentarios se espera, antes de ejecutar:

- 50.000 comentarios integrados, distribucion fuente 3.847 en buckets 0/1 y 3.846 en los demas.
- Una fila analitica: partido H12 de la corrida y minuto `2030-06-08T18:00:00+00:00`.
- 5.000 usuarios distintos, todos visibles; suma de likes a obtener de la fuente.

Son expectativas derivadas del generador, no resultados observados del Data Mart.
El generador cubre cincuenta segundos del mismo minuto y usa estado visible constante.
La demo valida ETL/procedencia e integridad, pero no demuestra variacion temporal,
ranking real entre partidos, efectividad de moderacion ni rendimiento a escala.
No mezclar corridas H12 como si fueran partidos reales: cada ID representa un experimento.

Para evidenciarlo, el usuario puede ejecutar la extraccion opcional y guardar consola,
`validacion.json` y consulta SQL. La consigna permite completar el diseno sin ejecutar
esta demo. Los comandos se encuentran en el README del directorio de la demostracion.
