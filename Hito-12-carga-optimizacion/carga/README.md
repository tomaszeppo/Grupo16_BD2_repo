# Preparación del generador

## Herramientas actuales para el flujo de comentarios

- `../scripts/generar_carga_masiva.py`: genera CSV, sin conexiones ni inserciones.
- `prueba_rendimiento.py`: benchmark directo Cassandra, con escrituras explícitas,
  particiones exclusivas y conservación de datos; sin limpieza automática.
- `medir_latencia.py`: GET de comentarios por API, secuencial, sin escrituras de dominio.
- `requirements.txt`: dependencias de las herramientas de medición.

Ver el [README del Hito 12](../README.md) para parámetros, salidas y compatibilidad.
Los tres scripts se prepararon y no se ejecutaron: las pruebas se harán con el usuario.
La configuración vigente del flujo es `../config/escenario_comentarios.json`.

## Antecedente conservado: consultas de partidos

La colección `h12_solo_lectura.postman_collection.json` se derivó de la colección original
del Hito 10. Contiene únicamente GET de health y partidos del perfil de laboratorio.
Se preparó y validó su formato, pero no se ejecutó Newman ni Postman en esta tarea.
La colección original conserva sus 38 requests, incluidos POST y DELETE.

El generador concurrente combinado por API aún debe implementarse. Debe tomar la
configuración final de comentarios, conservar proporciones/semilla, validar cuerpo y estado,
registrar errores, separar rampa y calentamiento de la medición y exportar resultados.
No basta lanzar una corrida de 180 segundos y etiquetarla como 120 segundos medidos.

No ejecutar el perfil final antes de adaptar y validar la API. La distribución 80/20 del
escenario previo se conserva como propuesta histórica de consultas de partidos; no es
la distribución del generador H6 incorporado (70% entre cinco populares). Las reglas de
corte requieren ventanas temporales reales y todavía no existe un monitor que las aplique.

