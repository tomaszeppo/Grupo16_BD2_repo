# Evidencia de ejecución — Hito 6

Salidas de consola guardadas tal cual, de las corridas contra el contenedor
`fixture2030-cassandra` (Cassandra 5.0.9) el 30/09/2026. Cada archivo arranca
con el comando que se corrió.

| # | Archivo | Qué muestra |
| :--- | :--- | :--- |
| 1-2 | `01_02_ambiente_y_version.txt` | `docker compose up -d`, `docker ps` con el contenedor healthy sobre `cassandra:latest`, `SHOW VERSION` (5.0.9), fecha de la corrida y recursos de Docker Desktop |
| 3 | `03_esquema_describe_keyspace.txt` | `esquema.cql` sin errores y `DESCRIBE KEYSPACE fixture2030` con las 3 tablas |
| 4 | `04_carga_muestra_conteos.txt` | `carga_muestra.cql` y los conteos: 40 en `comentarios_por_partido`, 40 en `comentarios_por_usuario`, 5 en `partidos_referencia` |
| 5 | `05_consultas.txt` | Las 4 consultas de `consultas.cql` con sus resultados |
| 5 | `05b_tracing_consultas.txt` | `TRACING ON` para el feed y el historial por usuario: en los dos casos aparece "Executing single-partition query" |
| 6 | `06_crud.txt` | El CRUD paso por paso: INSERT, lectura, UPDATE (`visible` → `oculto`) y DELETE, con el estado antes y después |
| 7 | `07_generar_carga_masiva.txt` | Salida de `generar_carga_masiva.py --target-rows 1200000` (1.199.770 filas, partición máxima 12.923) |
| 7 | `07b_copy_primer_intento_timeouts.txt` | Primer intento de carga, que falló por WriteTimeout en la tabla por usuario. Se deja como registro del problema |
| 7 | `07c_copy_carga_masiva.txt` | Carga definitiva con los COPY que imprime el generador: las 3 tablas completas, sin errores |
| 7 | `07d_verificacion_carga_masiva.txt` | Verificación contra la base: 1.199.810 filas en cada tabla, partición máxima, orden del feed y timestamps |
| 8 | `08_prueba_rendimiento.txt` | Opción A (`prueba_rendimiento.py`): 3.412 escrituras/seg |
| 8 | `08b_cassandra_stress.txt` | Opción B (`cassandra-stress`): 13.007 escrituras/seg |
| 9 | `09_idempotencia_carga_muestra.txt` | Segunda corrida de `carga_muestra.cql`: los conteos no cambian |

El análisis de los números de rendimiento está en `docs/rendimiento.md`.
