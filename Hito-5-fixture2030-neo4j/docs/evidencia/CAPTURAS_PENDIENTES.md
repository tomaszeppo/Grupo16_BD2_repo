# Capturas de pantalla a sacar en Neo4j Browser

Las salidas de consola de cada prueba ya estan en esta carpeta (archivos .txt). Faltan las
capturas de pantalla del Browser (http://localhost:7474). Guardarlas aca como PNG y borrar
este archivo. Orden sugerido: primero lo que modifica datos, la idempotencia al final.

1. **Resultado del CRUD.** Pegar `queries/crud.cypher` por partes y capturar las lecturas de
   antes y despues de cada operacion (fase de P-01 y minuto de P-01-EV1).
2. **Consulta de camino (RF9).** Pegar la consulta final de `queries/consultas_grafo.cypher`
   y capturar el camino ARG - SCO (4 saltos) en la vista de grafo.
3. **Subgrafo.** `MATCH (n) RETURN n LIMIT 100`, pestana Graph.
4. **Idempotencia.** Correr `queries/verificar_carga.cypher`, luego `queries/carga.cypher` otra
   vez, y volver a correr `verificar_carga.cypher`: los conteos tienen que ser iguales
   (64 / 1536 / 10 / 32 / 10).
