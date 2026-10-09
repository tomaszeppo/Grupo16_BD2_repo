# Rendimiento y carga masiva — Comentarios masivos (Hito 6)

Este documento separa lo que ya se ejecutó contra la base real de lo que falta ejecutar.
No hay ninguna cifra de escrituras por segundo cargada todavía: se completa con la
medición.

## Ambiente de la corrida

| Campo | Valor |
| :--- | :--- |
| Fecha | 09/10/2026 |
| Cassandra (`SHOW VERSION`) | 5.0.9, cqlsh 6.2.0, CQL 3.4.7, protocolo nativo v5 |
| Imagen | `cassandra:latest` |
| Recursos de Docker Desktop | 12 CPU, 15,5 GB de RAM (WSL2) |
| Topología | Un solo nodo, `SimpleStrategy`, factor de replicación 1 |
| Persistencia | `~/docker/data/cassandra` (en Windows, `C:\Users\<usuario>\docker\data\cassandra`) |

## Ya ejecutado

| Qué | Resultado | Evidencia |
| :--- | :--- | :--- |
| Esquema y `DESCRIBE KEYSPACE` | Keyspace y 3 tablas creados | `02_esquema.txt` |
| Carga de muestra dos veces | 40 / 40 / 5 filas las dos veces | `03_carga_muestra_idempotencia.txt` |
| Consultas de lectura | Las 4 consultas devuelven datos | `04_consultas.txt` |
| CRUD sobre las dos tablas, dos corridas sin editar | Alta, lectura, modificación y baja, con lectura antes y después | `05_crud.txt` |
| Generación de 1.199.770 comentarios con semilla fija | Dos generaciones independientes dan archivos idénticos (mismo MD5 en los 5 archivos) | `06_generacion.txt`, `06b_reproducibilidad_generador.txt` |
| `COPY` de las dos tablas grandes | 1.199.770 filas en `comentarios_por_partido` y 1.199.770 en `comentarios_por_usuario`, 0 omitidas, en unos 2 minutos cada una | `07_carga_copy_primera_vez.txt` |
| Persistencia en `~/docker/data/cassandra` | La carpeta se crea y se llena en Windows | `01_ambiente_y_version.txt` |

## Pendiente de ejecutar

1. **Validación por partición** después de la carga: `scripts/validar_carga_masiva.py` compara
   416 conteos por partido y bucket y 50.000 por usuario contra los esperados que escribe el
   generador, con un `COUNT(*)` por partición (nunca sobre la tabla entera).
2. **Segunda carga** de los mismos CSV y nueva validación: los conteos por partición no
   deben cambiar, porque los `comentario_id` son estables y `COPY` sobrescribe.
   Ambos pasos se corren con `bash scripts/cargar_y_validar.sh dos` (ver README).
3. **Medición de escrituras por segundo** (RF12) con `scripts/prueba_rendimiento.py` y, si se
   puede, con `cassandra-stress`. Completar la tabla de abajo con lo que salga.

Durante las pruebas de esta corrida, dos intentos de `COPY` se abortaron con
"No records inserted in 90 seconds" cerca de 1.065.000 filas, y otro se quedó sin avanzar,
con la máquina ocupada por otras tareas. Un reinicio del contenedor y volver a lanzar la
carga con la máquina libre alcanzó para completarla. Si vuelve a pasar, conviene bajar
`INGESTRATE` o `NUMPROCESSES` en `scripts/cargar_y_validar.sh`. Es una limitación del
ambiente (un nodo, disco montado desde Windows) y no del modelo.

## Medición (a completar)

| Campo | `prueba_rendimiento.py` | `cassandra-stress` |
| :--- | :--- | :--- |
| Fecha de ejecución | _pendiente_ | _pendiente_ |
| Filas / operaciones | _pendiente_ | _pendiente_ |
| Concurrencia y procesos | _pendiente_ | _pendiente_ |
| Tasa obtenida (escrituras/seg) | _pendiente_ | _pendiente_ |
| ¿Se alcanzó el objetivo de 10.000/seg? | _pendiente_ | _pendiente_ |

Si no se llega a 10.000 por segundo, se explica acá el cuello de botella observado
(CPU del cliente, CPU del nodo, disco). La cifra no se cambia.
