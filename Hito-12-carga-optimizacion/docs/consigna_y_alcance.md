# Consigna y alcance vigente

Fuente principal: Hito 12 — Requisitos Técnicos: Pruebas de Carga y Optimización del Fixture 2030, PDF suministrado por el equipo. Su sección 9 propone la estructura de carpetas adoptada. Las secciones 5.6 y 5.7 piden comparar la alternativa relacional y documentar la integración analítica; no obligan a construir un BI completo.

La fuente de redacción y capturas de los documentos finales es [Evidencia Hito 12.docx](evidencia/Evidencia%20Hito%2012.docx), no el HTML de arquitectura. La versión anterior de esta nota se conserva como antecedente.

La prueba cerrada es cliente Python y Cassandra H6: 50.000 escrituras individuales. API/Neo4j se conservan como contexto funcional del documento, sin atribuirles las métricas observadas. Ver [flujo y escenario](flujo_y_escenario_de_carga.md).

Se conservan preparación offline, propuestas iniciales y herramientas de otros escenarios. No se presentan esos materiales como pruebas ejecutadas. La documentación vigente es la lista de seis documentos temáticos del README.
