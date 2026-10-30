# Capturas para la primera corrida de escritura

Las mediciones y capturas están pendientes. No se ejecutó el benchmark ni se cargó el
esquema en esta preparación. La inspección de solo lectura encontró el Cassandra de H6
activo, sin tablas en el keyspace previsto; el esquema queda preparado para cargarlo juntos.

Guardar cada ejecución en un directorio nuevo `resultados/base/<corrida>/`, con:

- `escenario.json`: copia de la configuración simple.
- `consola.txt`: transcripción de PowerShell.
- `escrituras.jsonl`: configuración y resultado real del benchmark.
- `verificacion.json`: conteos reales por partición.
- `capturas/00_entorno.png`: fecha, versiones y código/hash del script.
- `capturas/01_esquema.png`: PRIMARY KEY y columnas de comentarios_por_partido.
- `capturas/02_escenario.png`: 50.000 filas, concurrencia 100, un proceso, sin rampa.
- `capturas/03_resultado.png`: exitosas/fallidas, segundos, escrituras/s e ID de corrida.
- `capturas/04_recursos.png`: recursos observados durante la ejecución (no después).
- `capturas/05_persistencia.png`: trece particiones, total esperado/guardado y resultado.

Las imágenes se toman manualmente durante la sesión. No se generan pantallas de resultados
ficticios ni se reemplazan capturas de corridas anteriores. No confundir capturas históricas
con esta corrida. Si hay errores, conservar también sus pantallas y archivos.

El entorno físico y los puertos efectivos se documentan en la evidencia de la ejecución,
sin llevar la configuración personal al README general. El cliente y la verificación
corren como contenedores separados con las dependencias del proyecto. Se conservan
esos contenedores y los registros; no hay instrucciones de limpieza automática.

Esta lista cubre la definición y primera medición del escenario. El Hito 12 completo
todavía necesita observación de las capas, diagnóstico, mejora y comparación reproducible.
