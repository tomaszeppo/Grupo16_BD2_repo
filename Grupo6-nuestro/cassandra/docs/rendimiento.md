# Rendimiento y distribución — Comentarios masivos (Hito 6)

Todo lo de este documento se corrió contra el contenedor real del
`docker-compose.yml` el 30/09/2026. Las salidas de consola completas están en
`docs/evidencia/`.

## Ambiente

| Campo | Valor |
| :--- | :--- |
| Versión de Cassandra (`SHOW VERSION` en cqlsh) | Cassandra 5.0.9, cqlsh 6.2.0, CQL spec 3.4.7, protocolo nativo v5 |
| Imagen | `cassandra:latest` (resolvió a 5.0.9 en esa fecha) |
| Recursos asignados a Docker Desktop | 6 CPU / 7,7 GB de RAM (backend WSL2) |
| Topología | Un solo nodo, `SimpleStrategy`, factor de replicación 1 |

## Generación de los datos (sin Cassandra de por medio)

`scripts/generar_carga_masiva.py --target-rows 1200000`:

| Parámetro | Valor |
| :--- | :--- |
| Filas objetivo | 1.200.000 |
| Filas generadas | 1.199.770 (el resto se pierde en la división entera por partido y bucket) |
| Usuarios distintos | 50.000 |
| Tiempo de generación | 29,8 s |
| Tasa de generación (CSV, no escritura a Cassandra) | ~40.200 filas/seg |
| Partición más cargada | 12.923 filas |

La primera vez que se corrió, antes de tener la base levantada, tardó 14,2 s.
Ahora tarda más por dos motivos: el script formatea las fechas y arma los
timeuuid a mano (ver "Qué se corrigió" más abajo), y además se corrió con
Cassandra ocupando la misma máquina. La cantidad de filas y la partición más
cargada dieron exactamente igual.

## Carga masiva con COPY (RF11)

Con los comandos que imprime el propio generador (`docs/evidencia/07c_copy_carga_masiva.txt`):

| Tabla | Filas | Tiempo | Filas/seg | Errores |
| :--- | ---: | ---: | ---: | ---: |
| `partidos_referencia` | 32 | 0,4 s | — | 0 |
| `comentarios_por_partido` | 1.199.770 | 82,3 s | ~14.600 | 0 |
| `comentarios_por_usuario` | 1.199.770 | 82,6 s | ~14.500 | 0 |

Esos ~14.500 por segundo no son el techo de la base: es el tope que se le
puso a propósito a COPY (`INGESTRATE=15000`). En el primer intento, con los
valores por defecto, la tabla principal entró a unas 37.000 filas por segundo
(1.199.770 en 32,2 s), pero la de usuarios se saturó y COPY abortó con 65.000
filas sin cargar (ver `docs/evidencia/07b_copy_primer_intento_timeouts.txt` y
la sección de cuello de botella).

La carga se verificó contra la base contando partición por partición (sin un
`COUNT(*)` sobre toda la tabla), en `docs/evidencia/07d_verificacion_carga_masiva.txt`:

- `comentarios_por_partido`: 1.199.810 filas en las 416 particiones (32 partidos × 13 buckets) = 1.199.770 de la carga masiva + 40 de la muestra.
- `comentarios_por_usuario`: 1.199.810 filas, igual que la otra tabla. La duplicación quedó pareja.
- Partición más cargada en la base: P-01 / bucket 0, con 12.927 filas (las 12.923 de la carga masiva más 4 de la muestra). La más chica tiene 1.025.
- El feed de una partición de 12.923 filas sale ordenado del más nuevo al más viejo sin `ORDER BY`, sin un solo par fuera de orden.

## Prueba de escritura (RF12)

Se corrieron las dos opciones.

### Opción A — `scripts/prueba_rendimiento.py`

El driver de Python no funciona con Python 3.12 o más nuevo en Windows (ver
README), así que se corrió desde un contenedor `python:3.11-slim` conectado a
la red del compose (`docs/evidencia/08_prueba_rendimiento.txt`).

### Opción B — `cassandra-stress`

Viene en la imagen, pero no está en el PATH: hay que llamarlo con la ruta
completa (`docs/evidencia/08b_cassandra_stress.txt`):

```
docker exec fixture2030-cassandra /opt/cassandra/tools/bin/cassandra-stress write n=100000 -rate threads=50
```

No usa el esquema del proyecto: arma su propia tabla de prueba en el keyspace
`keyspace1`.

### Resultado

| Campo | Opción A (driver Python) | Opción B (`cassandra-stress`) |
| :--- | :--- | :--- |
| Fecha de ejecución | 30/09/2026 | 30/09/2026 |
| Versión de Cassandra | 5.0.9 | 5.0.9 |
| Recursos de Docker Desktop | 6 CPU / 7,7 GB | 6 CPU / 7,7 GB |
| Filas insertadas | 50.000 (0 fallidas) | 100.000 (0 errores) |
| Concurrencia | 100 escrituras en vuelo | 50 hilos |
| Tiempo total | 14,65 s | 7 s |
| Tasa obtenida (escrituras/seg) | **3.412** | **13.007** |
| Latencia | no la mide | media 3,8 ms, p99 19,8 ms, máx 62,6 ms |
| ¿Se alcanzó el objetivo de 10.000/seg? | No | Sí |

### Qué se observó como cuello de botella

- **La base no es el límite.** Con `cassandra-stress` el mismo nodo pasó las
  13.000 escrituras por segundo, y eso que el generador de carga corría dentro
  del mismo contenedor y le sacaba CPU. COPY sin limitar llegó a unas 37.000
  filas por segundo en la tabla principal, aunque ahí ayudan los batches.
- **El límite de la opción A está en el cliente.** Midiendo con `docker
  stats` durante una corrida, el contenedor de Python estaba clavado en ~90%
  de CPU, o sea un núcleo entero, que es todo lo que puede usar un solo
  proceso de Python. Cassandra, en cambio, se movía entre 75% y 350% (de 600%
  posibles con 6 CPU): le sobraba lugar. El script manda todo desde ese único
  proceso, y no da para generar más pedidos. Se probó cambiar a un prepared
  statement y no mejoró. Al subir la concurrencia a 300, el driver cortó la
  conexión con un error de `CRC mismatch`, un problema del driver de Python
  con el protocolo v5 cuando hay mucha carga.
- **La cifra de la opción A varía bastante entre corridas.** La que quedó en
  la tabla es la primera (3.412/seg). Repitiendo la misma prueba un rato
  después dio entre 2.086 y 2.153/seg. No llegamos a aislar por qué bajó. En
  todos los casos quedó lejos de 10.000, y siempre con el cliente como límite.
- **En la carga masiva, el problema fue la memoria del nodo y el disco.** La
  tabla por usuario se carga desde un CSV que no está ordenado por
  `usuario_id`, así que cada batch de COPY toca 20 particiones distintas (el
  propio Cassandra lo advierte en el log: `Unlogged batch covering 20
  partitions`). Con eso aparecieron pausas del recolector de basura de Java de
  hasta 3,6 s y sincronizaciones del commit log de hasta 10 s. En ese rato el
  nodo descartó escrituras (67.066 `MUTATION_REQ` en `nodetool tpstats`) y
  COPY terminó abortando. La carpeta de datos es un montaje de Windows hacia
  WSL2, que es bastante más lento que un disco nativo de Linux, y eso
  seguramente pesa en los tiempos del commit log.

### Qué cambiaríamos para acercarnos más al objetivo

- Del lado del cliente: repartir la prueba en varios procesos (o varias
  máquinas) en vez de uno solo, o usar un cliente más liviano. Para cargas
  grandes, usar una herramienta pensada para eso, como DSBulk.
- Ordenar el CSV de `comentarios_por_usuario` por `usuario_id` antes del COPY,
  así cada batch cae en una sola partición, como pasa con la tabla principal.
- Guardar los datos en un volumen que esté adentro de WSL2 y no en una carpeta
  de Windows. La consigna pide `~/docker/data/cassandra`, por eso no se cambió.
- Con más de un nodo, las escrituras se reparten entre nodos y la tasa total
  crece. Con un solo nodo de laboratorio, lo medido alcanza para ver que el
  modelo se banca el volumen.

## Qué se corrigió al probar contra la base real

1. **Las fechas se cargaban sin hora.** El generador escribía los timestamps
   en formato ISO (`2030-06-08T18:00:41.896710`), y COPY en Cassandra 5 los
   aceptaba sin dar error pero guardaba solo la fecha, con la hora en
   00:00:00. Pasaba con `creado_en` y con `fecha_inicio`. Ahora se escriben
   como `2030-06-08 18:00:41.896+0000`, que COPY sí toma bien.
2. **El orden del feed no coincidía con la hora del comentario.** El
   `comentario_id` se generaba con la hora de la corrida del script y no con
   `creado_en`. Como la tabla ordena por `comentario_id` DESC, en la carga
   masiva los comentarios de un bucket salían en el orden en que se generaron
   y no en el que se "escribieron". Ahora el timeuuid se arma con la misma
   hora que `creado_en`. En la base se verificó que coinciden en las 12.923
   filas de una partición.
3. **COPY con un ritmo moderado.** Los comandos que imprime el generador
   ahora llevan `INGESTRATE=15000 AND MAXBATCHSIZE=10 AND NUMPROCESSES=3 AND
   MAXATTEMPTS=10`. Así la carga terminó completa y sin un solo timeout.
