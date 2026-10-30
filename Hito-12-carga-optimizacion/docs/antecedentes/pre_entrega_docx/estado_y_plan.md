# Estado y orden de avance

Fecha: 30/10/2026. Base revisada: `main@f0b228e`.

**Estado vigente:** primera línea base `base-20261030-002022` ejecutada por el usuario,
50.000 confirmadas y persistidas, cero errores y coincidencia de las 13 particiones.
RF7 queda documentado en [análisis e hipótesis](RF7_analisis_y_prueba.md), con antecedentes
en ambas ramas y una prueba de concurrencia 100 vs 50 propuesta, todavía sin ejecutar.
Se incorporó el registro previo de cambios requerido por la sección 5.5.

**RF8 / M02:** `versiones/v2.2_candidata_paralelo/` agrega control A 1x100 y candidata
B 2x50, mismos datos por índice global, spawn, sesiones propias y barrera previa a la
medición. Pasó nueve pruebas offline, sin conexiones ni cargas. Ver
[registro M02](../versiones/v2.2_candidata_paralelo/docs/registro_modificacion_M02.md).
Comparación de rendimiento A/B y decisión final pendientes; hipótesis H2 previa preservada.

**RF8 / M01:** la candidata `versiones/v2.1_candidata_c50/` ya implementa concurrencia 50,
validación del perfil y trazabilidad. Pasó seis verificaciones aisladas, sin usar Cassandra.
Las nuevas mediciones de carga y la decisión sobre la mejora están pendientes. La copia
histórica `versiones/v2.0_base/` y la corrida original siguen intactas.

Actualización vigente: se simplificó el escenario a **50.000 inserciones directas en
Cassandra, concurrencia 100, un proceso, sin rampa**, reutilizando el benchmark H6.
Ver `config/escenario_escritura_simple.json`, el README y la lista de capturas.
Este escenario no exige combinar GET/POST por API. Las propuestas anteriores se
conservan como antecedentes. Esquema y verificador de conteos preparados, sin ejecución.

Actualización de alcance: el usuario eligió publicar y consultar comentarios. Se incorporaron
generador masivo H6, benchmark Cassandra y medidor GET HTTP, con procedencia y adaptaciones
documentadas en el README H12. Ninguno de estos tres scripts se ejecutó en esta preparación.
La configuración vigente es `config/escenario_comentarios.json` (relativa a la raíz H12).

**Paso 1 definido y primera línea base completada para la prueba simple.** La inspección
anterior había encontrado las tablas ausentes; posteriormente el usuario creó el esquema
y ejecutó la corrida junto con la verificación. Esas notas de preparación se conservan
como antecedentes y no describen el estado actual de ejecución.

La [auditoría de evidencia remota](auditoria_evidencia_remota_20261029.md) confirma evidencia
histórica ya subida en main y correcciones, incluida la caída/503/recuperación Redis del H11.
Reutilizarla donde corresponda; un faltante de capturas en una carpeta no implica que la prueba
no esté registrada en otro archivo. La comparación del escenario final H12 sigue pendiente.

| Estado | Trabajo |
|---|---|
| Hecho | Clon y pull; seis motores y API activos; inventario de solo lectura |
| Preparado, sin ejecución | Carpetas, escenario, lotes sintéticos, manifiesto, correspondencias, colección GET, modelo analítico |
| Hecho para el escenario simple | Módulo H6, esquema, volumen y concurrencia definidos; primera línea base y persistencia verificadas |
| RF7 documentado | Posible presión del cliente de un proceso, hipótesis y prueba controlada propuestas; causalidad todavía no confirmada |
| Pendiente pasos 5-6 | Ejecutar la comparación propuesta con repeticiones, evaluar el costo y los errores, decidir sobre el cambio y concluir |

## Plan anterior de consultas de partidos, conservado como antecedente

La lista siguiente corresponde al diseño previo. Para comentarios, primero resolver el
esquema Cassandra elegido y su integración con la API, cerrar proporciones/frecuencia y
condiciones, y después medir y comparar. Ver el README actualizado para las herramientas.

1. Elegir si el experimento final reutiliza H5 de `main` o el modelo corregido. Registrar
   commit y esquema. La propuesta recomienda reutilizar módulos previos; el laboratorio H10
   sirve para explorar conectividad, pero reproduce la observación del profesor sobre IDs
   e instancias nuevos. No confundirlo con integración final corregida.
2. Validar correspondencias por equipos, fecha, sede y significado. `P001` y `P-01` coinciden
   documentalmente en ocho casos de `main`; eso no autoriza usarlos como equivalentes en
   `correcciones`, Cassandra H6, Influx H8 o IRIS H9. H6 sigue sin mapear en este lote.
3. Adaptar validación, adaptador y contratos al modelo elegido: la API actual solo acepta
   `^P-\d{2,3}$`; `P001` hoy es inválido. El esquema corregido de H5 usa `Sede`, mientras
   el adaptador actual consulta `Estadio`. Resolver antes de importar o medir.
4. Revisar posibles colisiones del destino y los datos existentes. Si ya existen partidos
   nativos válidos, consumirlos: no es necesario reinsertarlos. Los comentarios preparados
   quedan detenidos hasta identificar sus particiones de destino.
5. Cerrar el escenario, registrar versiones reales/digests, CPU/RAM asignadas y contenedores
   ajenos que compiten por recursos. Fijar configuración y dataset por hash.
6. Implementar generador/captura con rampa, calentamiento separado de medición, repeticiones,
   exportación de errores y monitoreo de todas las capas. Medir la versión inicial antes
   de introducir la caché. Tres niveles y tres repeticiones por versión dan 18 corridas
   planificadas (54 minutos nominales, sin preparación ni pausas); no se ejecutaron.
7. Diagnosticar y recién entonces evaluar caché Redis: Neo4j autoridad, TTL 15 s propuesto,
   namespace propio, fallback acotado, hits/misses y trazabilidad. Verificar igualdad del
   contenido y límites de frescura. No precargar respuestas falsas como si vinieran de la fuente.
8. Repetir condiciones, comparar p50/p95/p99, RPS, errores y recursos; guardar costos,
   dispersión, límites y conclusiones. Documentar alternativa SQL equivalente.
9. Para la parte analítica, completar correspondencias Neo4j-Cassandra, ETL idempotente por
   partido/país/ventana, procedencia y checkpoint transaccional; contrastar conteos y repetir
   lote. El SQL preparado no crea todavía un Data Mart funcional.
10. Revisar entrega: README reproducible, commit y cambios locales identificados, datos,
    resultados crudos, tablas/gráficos, conclusiones y ausencia de secretos. Commit/push pendientes.

## Actualización del repo

`git pull --ff-only`: Already up to date. `origin/main` coincide con `main@f0b228e`.
`origin/correcciones@27f28e1` diverge: 25 commits exclusivos de main y 2 exclusivos de
correcciones al revisar. No se integró. Su árbol reemplaza/elimina material, incluidos
Hitos 10/11 y cambios de nombres/esquemas: una incorporación selectiva requiere revisión
preservando los originales. No usar un reemplazo completo de rama.

## Qué se preservó

La preparación agrega una carpeta nueva. No se borraron archivos, volúmenes, tablas,
colecciones ni claves. No se ejecutaron loaders, seeders, escrituras Postman ni pruebas
de falla/carga. Las consultas de inventario son de lectura. Los materiales personales
para Juani se guardan fuera del repositorio.

