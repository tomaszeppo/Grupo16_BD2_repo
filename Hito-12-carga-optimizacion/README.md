# Hito 12 - Carga, optimización e integración analítica

Entrega organizada a partir del texto y las capturas de **Evidencia Hito 12.docx**, conservado completo en [docs/evidencia](docs/evidencia/README.md). La estructura sigue la consigna técnica del profesor. El HTML de arquitectura no se utiliza como fuente.

## Resultado y alcance

Se midieron **50.000 INSERT individuales en Cassandra H6**, mediante cliente Python y driver. La API HTTP, Neo4j y PostgreSQL no participaron en esta medición. La descripción funcional por API del DOCX se conserva como antecedente y se distingue del escenario efectivamente ejecutado.

La variante manual B reparte el trabajo en dos procesos con concurrencia 50 por proceso, conservando el máximo global 100 del control. Frente a la base histórica: **+30,1% throughput**, **−23,2% tiempo de carga**, **−34,8% p99**. El máximo de latencia empeoró **139,3%**. Ambas corridas confirmaron y persistieron 50.000 filas sin errores. Es una comparación exploratoria; no demuestra por sí sola causalidad, repetibilidad ni capacidad de producción.

La demostración del Data Mart se ejecutó: una fila por partido/minuto, 50.000 comentarios, 5.000 usuarios distintos, 50.000 visibles, cero otros estados y 249.661 likes. La extracción validó los conteos de las 13 particiones. La consulta SQL final se realizó con el lector corregido v1.1. Refresco periódico, datos tardíos y recuperación integral siguen siendo políticas propuestas.

## Documentación de la entrega

| Apartado | Documento |
|---|---|
| Preparación y requisitos del entorno | [Entorno](compose-o-instrucciones-del-entorno.md) |
| Flujo, escenario y datos | [Flujo y escenario](docs/flujo_y_escenario_de_carga.md) |
| Base, versiones, entorno y recursos | [Línea base](docs/linea_base.md) |
| Hipótesis, cambios, trade-offs y resultados | [Hipótesis y optimización](docs/hipotesis_y_optimizacion.md) |
| Pregunta, grano, ETL, frecuencia y procedencia | [Data Mart](docs/integracion_data_mart.md) |
| Alternativa PostgreSQL, análisis conceptual | [Comparación relacional](docs/comparacion_relacional.md) |
| Validaciones, errores y límites | [Integridad y limitaciones](docs/integridad_y_limitaciones.md) |
| Original completo, capturas, tablas y resultados | [Evidencia](docs/evidencia/README.md) |
| Datos y generadores utilizados | [Datos o generadores](datos-o-generadores/README.md) |

## Estructura

```text
README.md
compose-o-instrucciones-del-entorno.md
scripts/                         entradas de preparación, carga, validación y lectura
config/                          ejemplo sin secretos, .gitignore y entorno mínimo
docs/
  flujo_y_escenario_de_carga.md
  linea_base.md
  hipotesis_y_optimizacion.md
  integracion_data_mart.md
  comparacion_relacional.md
  integridad_y_limitaciones.md
  evidencia/
    Evidencia Hito 12.docx
    documento_completo.md
    resultados_linea_base.json
    resultados_optimizados.json
    tablas_o_graficos.csv
    tablas_o_graficos.md
    capturas_redactadas/
datos-o-generadores/README.md
resultados/                      registros crudos, entorno, verificación y proyección
versiones/                       fuentes y configuraciones históricas
carga/                           herramientas originales adaptadas
analitica/                       propuestas previas conservadas
datamart/                        extractor v1 y lector corregido v1.1
```

## Reproducir manualmente

Desde esta carpeta, con Python en el host y Docker activo. Primero verificar el [entorno](compose-o-instrucciones-del-entorno.md); no levantar otro servicio sobre uno existente. Los scripts de preparación no ejecutan cargas automáticamente.

```powershell
# Preparar control A de v2.2 (1 proceso x 100), no reemplaza la base histórica:
& .\scripts\ejecutar_linea_base.ps1

# O preparar candidata B (2 procesos x 50):
& .\scripts\ejecutar_prueba_optimizada.ps1
```

Cada comando imprime tres líneas completas e independientes. Ejecutar `01_MONITOREAR.ps1` en la segunda consola; con el monitor activo ejecutar `02_CARGAR.ps1` en la primera; al terminar capturar el resumen y ejecutar `03_VERIFICAR.ps1`. Cada carga inserta 50.000 comentarios nuevos. No reutilizar IDs, salidas ni nombres de contenedores. Se pueden usar también `ejecutar_carga.ps1 -CarpetaCorrida RUTA` y `validar_integridad.ps1 -CarpetaCorrida RUTA` sobre la carpeta preparada.

El benchmark genera sus datos; no importa los CSV de preparación offline. `scripts/preparar_datos.py` y el generador masivo son herramientas complementarias, no prerrequisitos de esta carga.

### Mostrar el Data Mart ya generado

No requiere Docker ni una nueva extracción; usa SQLite incluido en Python:

```powershell
& .\scripts\mostrar_data_mart.ps1
```

Para una nueva extracción opcional de la corrida manual verificada, una vez terminadas las pruebas de rendimiento:

```powershell
& .\scripts\demostrar_data_mart_v1_1.ps1
```

Solo lee Cassandra y escribe una carpeta local nueva. El script original `demostrar_data_mart.ps1` se conserva como histórico del fallo de lectura; el nuevo utiliza el lector v1.1. La proyección no convierte IDs H12 en partidos reales ni integra datos inexistentes de país/Neo4j.

## Evidencia y versiones

- Base del informe: `resultados/base/base-20261030-002022/`, código `versiones/v2.0_base/`.
- Variante del informe: `resultados/optimizado/manual-B-20261030-025822-9dff16/`, código `versiones/v2.2_candidata_paralelo/`.
- Proyección validada: `resultados/datamart/dm-20261030-032514-c7dd32/`.
- v2.1: reducción de concurrencia a 50 con un proceso, implementada pero no medida en la comparación manual.
- `resultados/comparativas/m02-20261030-025057/`: seis corridas automáticas adicionales preservadas como evidencia suplementaria. No forman los porcentajes del DOCX ni sustituyen la comparación manual relatada.

Los snapshots y manifiestos antiguos describen el momento de su creación y pueden decir “pendiente” o “no ejecutado”. No se reescribieron como si fueran posteriores a las pruebas. La documentación previa queda conservada en `docs/antecedentes/pre_entrega_docx/`; los seis documentos temáticos y este README describen la entrega vigente. En particular, el hash del documento analítico anterior del manifiesto Data Mart v1 corresponde ahora a la copia histórica de esa carpeta.

Las muestras individuales se publican comprimidas en `.jsonl.gz`; los originales locales no se borraron. [El manifiesto de compresión](docs/evidencia/muestras_comprimidas.json) permite verificar sus bytes originales. Los hashes de código y versiones evitan depender únicamente del commit anterior, cuando H12 todavía estaba sin versionar.

## Pruebas y conservación

Las verificaciones offline cubren instrumentación, perfiles, determinismo, coordinación, transformación y lectura SQL. No son mediciones de carga ni se presentan como tales. Los resultados de validación de la entrega se conservan en `docs/evidencia/verificacion_entrega.json`.

`limpiar_datos_de_prueba.ps1` solo informa la política: **no se eliminan datos, tablas, contenedores, volúmenes ni versiones**. No se publican .env ni credenciales. Los detalles de la máquina de la ejecución están en la evidencia, no en los requisitos generales del README.
