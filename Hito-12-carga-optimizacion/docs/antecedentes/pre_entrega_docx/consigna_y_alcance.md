# Consigna disponible y alcance de esta preparación

Fuente principal: `Clase_13_Teoria_Grandes_Volumenes_Data_Marts_Fixture_2030.html`,
sección «Hito 12 - Pruebas de carga y optimización» (archivo aportado en Descargas).
No se encontró una consigna independiente titulada Hito 12 en `main`,
`origin/correcciones` ni entre los archivos de Descargas examinados por nombre.
Esta preparación usa la sección disponible; no presume requisitos de un documento no aportado.

| Paso de la clase | Evidencia que habrá que producir | Estado actual |
|---|---|---|
| 1. Definir el escenario | Operaciones, proporciones, datos, concurrencia, duración, rampa, finalización | Borrador y datos preparados; falta fijar la versión de módulos que se reutilizará |
| 2. Establecer línea base | Versión inicial y entorno identificados, resultados reproducibles | Pendiente |
| 3. Observar las capas | API, NoSQL, host, red, errores, datos aceptados | Logs previos disponibles; captura correlacionada H12 pendiente |
| 4. Detectar el cuello | Causa explicada con evidencia | Pendiente de medición |
| 5. Optimizar | Cambio documentado, motivo y costo | Caché propuesta, no implementada |
| 6. Repetir y comparar | Percentiles, throughput, errores, recursos y límites | Pendiente |

La clase también trata integración en Data Marts y comparación con estructuras relacionales.
Se prepara un diseño y una comparación conceptual. La sección del hito disponible no obliga
a desplegar Hadoop, Spark o Kafka ni a insertar millones de registros. Los dos PDF de Clase 14
describen el ecosistema Big Data; no se toman sus ejemplos como nuevas obligaciones del hito.

La estructura de carpetas deriva del mapa propuesto en `arquitectura-hito-12.html` del repo.
Los niveles 5/15/30 usuarios, TTL de 15 segundos, distribución 80/20 y SQLite son decisiones
propuestas por el equipo en ese mapa, no valores impuestos por el profesor.

Al integrar al repo: guardar scripts/configuración, dataset o generador, resultados crudos,
gráficos/tablas y explicación de reproducción. No incorporar secretos ni atribuir resultados
históricos a esta nueva ejecución.

