# Datos preparados, no insertados

Lote inicial: `preparados/lote_20261029_01/`. Ver `manifiesto.json` para cantidades y SHA-256.

| Archivo | Perfil / propósito | Condición antes de usarlo |
|---|---|---|
| partidos_h5_main.csv; neo4j_parametros.json | 32 partidos y 10 estadios originales de main H5 | Confirmar destino, coincidencias y existencia; reutilizar datos existentes cuando sea posible |
| correspondencias_documentales.csv | 8 coincidencias H5-main/H10-laboratorio | No trasladar a otras ramas ni motores sin comprobación |
| comentarios_propuestos.jsonl | 1.920 comentarios, UUID5 reproducibles, 128 particiones propuestas | `partido_id_cassandra` es null intencional; completar solo tras validar correspondencia H6 |
| datamart_conteos_esperados.csv | 15 comentarios por partido/país/ventana del lote | Expectativas de los archivos, no conteos de una base cargada |
| mongo_*_h10.jsonl; iris_partidos_h10.json | Datos de apoyo del laboratorio ya activo | No resolver la integración histórica reemplazando los modelos previos por estas copias |
| influx_muestra_h10.lp | 4.800 puntos, precisión segundos | Fechas sintéticas de 2030; no asumir datos actuales ni multiplicar cardinalidades dependientes |
| redis_politica_propuesta.json | Namespace/TTL/fallback del diseño | La caché real debe reconstruirse desde Neo4j; este archivo no contiene respuestas a insertar |

Los comentarios utilizan el país de la audiencia, no el país de los equipos del partido.
Su horario 18:30/19:00 UTC es sintético: H5 solo informa la fecha, sin hora de inicio.
Los IDs se conservan por fuente. No se atribuye a H6 una correspondencia no verificada.

`plantillas/` contiene consultas para revisión. No hay script que las ejecute.
No existe un proceso automático de limpieza o borrado.

