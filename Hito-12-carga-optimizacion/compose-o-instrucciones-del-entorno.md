# Entorno del experimento

El benchmark usa Docker Desktop con contenedores Linux, Cassandra 5.0.9 observado,
Python 3.12.16 y cassandra-driver 3.30.1. Se conecta a `fixture2030-cassandra:9042`
en `fixture2030-cassandra_default`, no al Cassandra 4.1 del compose de la API H10.
La API y Neo4j no participan en el recorrido medido. Recursos/versiones/IDs observados
están en los JSON de entorno de cada corrida, sin imponer la configuración personal
del equipo como requisito general.

## Si ya existe el laboratorio

Desde la raíz H12, verificar, sin crear ni reemplazar servicios:

```powershell
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker exec fixture2030-cassandra cqlsh -e "SHOW VERSION; DESCRIBE TABLE fixture2030.comentarios_por_partido;"
```

Los preparadores usan la imagen por ID registrada en el manifiesto v2.2; debe existir
localmente. No sustituir una imagen silenciosamente ni comparar entornos diferentes
como si fueran idénticos. No ejecutar limpieza para recuperar un entorno.

## Laboratorio nuevo (no ejecutar sobre uno ya existente)

Se incluye un compose mínimo independiente para instalar la misma familia de Cassandra.
Las etiquetas de imágenes son mutables: una construcción nueva no garantiza los mismos
bytes del laboratorio original. Registrar versiones y volver a medir A/B en ese entorno.

```powershell
docker compose -p h12 -f .\config\compose.cassandra.yml up -d
docker exec fixture2030-cassandra cqlsh -e 'SHOW VERSION;'
Get-Content -Raw .\scripts\esquema_comentarios_h6.cql | docker exec -i fixture2030-cassandra cqlsh
docker build -t h12-cliente:local -f .\config\Dockerfile.cliente .
```

Esperar a que Cassandra esté saludable antes de crear el esquema. El CQL usa IF NOT
EXISTS y no elimina tablas. No publicar puertos ni secretos para esta prueba interna.
La receta nueva es material de reproducción, no una instalación ejecutada para esta
entrega. No modifica el manifiesto histórico: para una imagen nueva crear otra versión
del experimento con su ID, o ejecutar el CLI del benchmark pasando explícitamente los
parámetros y conservando nueva evidencia. No usar la referencia antigua de imagen si
no está disponible.

## Orden de ejecución manual

1. Preparar A o B con `scripts/ejecutar_linea_base.ps1` o `ejecutar_prueba_optimizada.ps1`.
2. Ejecutar el `01_MONITOREAR.ps1` impreso en otra consola.
3. Ejecutar el `02_CARGAR.ps1` impreso en la primera consola; inserta 50.000 comentarios.
4. Capturar el resumen y ejecutar `03_VERIFICAR.ps1`; conservar todo aunque falle.
5. Repetir en carpetas/IDs nuevos, sin cargas simultáneas. La prueba analítica se hace después.

Los preparadores deliberadamente separan preparación de carga para permitir capturas
y control manual. `preparar_datos.py` genera archivos offline opcionales: el benchmark
genera su propio dataset y no importa esos CSV. `limpiar_datos_de_prueba.ps1` informa
la política de conservación; no realiza borrados.
