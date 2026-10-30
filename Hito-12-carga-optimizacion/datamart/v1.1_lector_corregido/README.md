# v1.1 - Correccion de lectura SQL

El lector v1 separaba texto por cada punto y coma, incluidos los que aparecen dentro
de comentarios SQL. Un fragmento sin resultados producia cursor.description=None.
La v1.1 usa sqlite3.complete_statement para reconocer las sentencias completas y
omite cursores sin columnas. Conserva la verificacion del hash y la apertura SQLite
en modo solo lectura. No vuelve a extraer ni modifica datos o la version v1.

Desde la raiz H12, consultar una carpeta ya validada:

```powershell
python .\datamart\v1.1_lector_corregido\consultar_proyeccion.py .\resultados\datamart\CARPETA_VALIDADA
```

Pruebas de regresion: cuatro casos de SQLite en memoria, incluido el SQL original
que disparo el error. No requieren Cassandra, Docker ni archivos de datos.

```powershell
python -B -m unittest discover -s .\datamart\v1.1_lector_corregido -p test_lector.py -v
```

El script historico demostrar_data_mart.ps1 sigue apuntando a v1. Para una extraccion
que ya termino, ejecutar directamente este lector corregido y conservar tanto la
transcripcion original del fallo como la nueva salida de consulta.
