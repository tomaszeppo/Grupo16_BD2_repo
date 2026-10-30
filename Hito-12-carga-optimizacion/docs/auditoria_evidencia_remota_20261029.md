# Auditoría de evidencia ya subida

Revisión: 29/10/2026, después de `git fetch --all`. Ramas remotas disponibles:
`origin/main@f0b228e` y `origin/correcciones@27f28e1`. La configuración de fetch incluye
todas las ramas del remoto. No se hizo checkout, merge, carga de datos ni borrado.

## Resultado

**Sí hay abundante evidencia empujada a GitHub, repartida entre ambas ramas.**
No corresponde interpretar «falta la captura en la carpeta indicada» como «la prueba no tiene evidencia».
En particular, el registro de H11 ya contiene caída, 503 y recuperación de Redis.

El inventario adjunto enumera 59 entradas bajo rutas de evidencia/documentación de pruebas:
21 en main y 38 en correcciones. Ese número incluye README, un .gitkeep, una nota de
capturas pendientes y archivos repetidos entre ramas; no significa 59 pruebas distintas.
Se registraron SHA-256 y tamaños a partir de los blobs remotos, no solo de archivos locales.

## Qué existe y para qué sirve

| Hito | Rama | Evidencia comprobada | Uso / límite |
|---|---|---|---|
| 4 MongoDB | correcciones | 01 a 06 en docs/evidencia: arranque, recarga, consultas, explain, cambios e idempotencia. La recarga conserva 64 equipos/1.536 jugadores y rechaza ARG duplicado con E11000 | Evidencia aprovechable de carga reproducible, unicidad e índices; no es carga concurrente H12 |
| 5 Neo4j | main y correcciones | main tiene Capturas Hito 5.pdf; correcciones tiene seis registros TXT de esquema, carga, recarga, CRUD y consultas | Hay evidencia textual en la rama corregida; CAPTURAS_PENDIENTES.md todavía pide screenshots de Browser |
| 6 Cassandra | correcciones | CRUD, muestra idempotente, dos generaciones con mismos hashes y log COPY de 1.199.770 filas por tabla grande, 0 omitidas | La carga masiva sí está registrada. El log tiene tasas COPY; el benchmark específico y la validación/recarga masiva siguen pendientes según docs/rendimiento.md |
| 7 Redis | correcciones | Concurrencia 8 procesos x 5.000: INCRBY conserva 40.000 visitas; GET+SET obtiene 7.996. Microprueba: 700 hits/300 misses. Medición: GET 1.742 ops/s y ZINCRBY 624 ops/s | Son pruebas reales del módulo Redis, con fecha y entorno en los archivos; no son una comparación del endpoint de partidos antes/después de agregar caché |
| 8 InfluxDB | ambas | PDF de nueve páginas con capturas de arranque, carga, conteos, consultas, agregaciones y medición. Mismo SHA-256 en ambas ramas | La evidencia está dentro del PDF aunque el README de evidencia parezca una reserva de carpeta; no debe tratarse como carpeta vacía |
| 9 IRIS | main y correcciones | main: PDF y logs de compilación/guardado/navegación/propiedad requerida; correcciones: compilación, consultas, demos y cascada de borrado | Hay pruebas históricas. No se localizó la demostración exacta de un hijo inválido que haga fallar el guardado y deje ausentes padre e hijo con conteos posteriores |
| 10 API | main | Endpoints, logs, dependencia Redis caída, latencias y Newman: 38 requests/95 aserciones, 0 fallos | La latencia se midió con 50 requests secuenciales por endpoint, 5 de calentamiento y un cliente; es referencia previa, no la comparación H12 planificada |
| 11 Conectividad | main | resultados_tcp.txt, resultados_clientes.txt y resultados_api.txt. Este último registra dos secuencias Redis detenido → /sesiones HTTP 503 → PONG → /health HTTP 200 | La prueba de falla y recuperación sí está empujada y vinculada a e5f3949. La observación sobre capturas_redactadas/ es de ubicación/formato de captura |

No se volvieron a ejecutar las pruebas: estos resultados son los contenidos de los archivos subidos.
Las cifras corresponden a sus corridas históricas y no se atribuyen al entorno actual.

## Rutas concretas para encontrarlo

En `origin/correcciones`:

- `Hito-4-fixture2030-mongodb/docs/evidencia/06_idempotencia_y_unicidad.txt`
- `Hito-4-fixture2030-mongodb/docs/evidencia/04_explain_collscan_vs_ixscan.txt`
- `Hito-5-fixture2030-neo4j/docs/evidencia/01_estructura_constraints_indices.txt` hasta `06_consultas_grafo.txt`
- `Hito-6-fixture2030-cassandra/docs/evidencia/06b_reproducibilidad_generador.txt`
- `Hito-6-fixture2030-cassandra/docs/evidencia/07_carga_copy_primera_vez.txt`
- `Hito-7-fixture2030-redis/docs/evidencia/07_prueba_concurrencia.txt`
- `Hito-7-fixture2030-redis/docs/evidencia/08_hit_rate.txt`
- `Hito-7-fixture2030-redis/docs/evidencia/09_rendimiento.txt`
- `Hito-9-fixture2030-iris/docs/evidencia/`

En `origin/main` (también presentes en el árbol local):

- `Hito-10-fixture2030-APIREST/docs/evidencia/20261016_135303_newman.txt`
- `Hito-10-fixture2030-APIREST/docs/evidencia/20261016_120557_latencia.txt`
- `Hito-10-fixture2030-APIREST/docs/evidencia/20261016_120557_dependencia_caida.txt`
- `Hito-10-fixture2030-APIREST/fixture2030-hito-11-conectividad/docs/evidencia/resultados_api.txt`
- `Hito-8-fixture2030-influxdb/docs/evidencia/evidencias-influxdb.pdf`

## Observaciones sobre archivos y documentación

- `capturas_redactadas/` de H11 solo contiene .gitkeep, pero la secuencia de falla/recuperación
  ya está en resultados_api.txt. No hace falta repetir una prueba solo por no verla en esa carpeta;
  primero ordenar referencias y verificar qué formato de captura pide la devolución.
- `Screenshots Hito 11.pdf` está subido (2.869.288 bytes, seis páginas), pero pypdf reportó
  errores de descompresión y pypdfium2 devolvió seis páginas en blanco. No se pudo validar
  su contenido visual con esos lectores. Conviene revisar/exportar ese PDF; los TXT sí son legibles.
- H8 tiene capturas dentro de un PDF: buscar solo TXT o PNG da un falso faltante.
- H5/correcciones conserva una nota explícita de screenshots pendientes, aun teniendo seis TXT.
- H6/correcciones declara pendientes en su propio documento de rendimiento. El COPY exitoso
  existe; no equivale por sí solo a toda la validación posterior que ese plan enumera.
- Tener un script de captura o un README que diga «ejecutar» no demuestra que se haya corrido.
  En esta auditoría se distinguieron esos archivos de logs y capturas con resultados.

## Qué cambia para el Hito 12

Podemos reutilizar la evidencia previa para justificar modelos, unicidad, reproducibilidad,
conectividad y diseño de métricas. No hay que reconstruir ni repetir indiscriminadamente los hitos anteriores.

En las dos ramas inspeccionadas no aparece todavía una comparación final del experimento H12:
escenario elegido, línea base y versión optimizada del mismo flujo, con configuración comparable,
resultados crudos, percentiles/throughput/errores/recursos e interpretación del cambio.
La prueba Redis de H7 y el explain Mongo de H4 son antecedentes útiles de concurrencia/optimización;
si se eligen como base del H12, habrá que explicitar su escenario y completar la comparación exigida.

La carpeta `Hito-12-carga-optimizacion/` que preparamos permanece solo en el árbol de trabajo local,
sin commit ni push. `arquitectura-hito-12.html`, ya en main, declara que caché y experimento son propuestas.
La búsqueda incluyó rutas e historial de ambas ramas, no solo nombres de carpetas H12.

El paso 1 sigue siendo cerrar el escenario y la versión de datos a consumir. La auditoría mejora
el inventario de evidencia reutilizable; no convierte automáticamente las corridas históricas en
una medición nueva del escenario propuesto.

Archivos de apoyo: `inventario_evidencia_remota_20261029.csv` y `.json`, con rutas y hashes.
