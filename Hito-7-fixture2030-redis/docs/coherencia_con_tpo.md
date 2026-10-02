# Coherencia con TPO e hitos anteriores

## Relación con la arquitectura definida

Los trabajos anteriores establecieron una arquitectura políglota para el Fixture 2030. Redis ya había sido seleccionado para valores/estado en tiempo real por su baja latencia; MongoDB conserva información estática/finalizada; Neo4j representa relaciones entre usuarios, grupos, predicciones y partidos.

Este Hito 7 **no reemplaza** esos módulos. Agrega una capa específica para:

- sesiones de navegación;
- actividad temporal;
- caché de lecturas repetidas;
- ranking temporal;
- operación concurrente y métricas.

## Usuarios y sesiones

El análisis inicial del grupo contempló 2–3 millones de usuarios simultáneos y un volumen de sesiones del mismo orden. Eso justifica un acceso directo por clave en Redis en lugar de resolver la sesión mediante búsquedas complejas.

## Cacheado del partido

El ejemplo `P001` se relaciona con los datos de prueba utilizados en Hito 5, donde aparecen usuarios U001/U002 y predicciones sobre P001. Para el Hito 7 se cachea solamente un **resumen reconstruible** del partido. La fuente autoritativa permanece fuera de Redis.

El archivo `datos/demo_mongo_response_P001.json` no es una segunda base de datos: representa de manera reproducible la respuesta que la aplicación podría obtener desde MongoDB antes de llenar la caché.

## Concurrencia

Los problemas de SQL documentados por el grupo incluían múltiples usuarios actualizando información al mismo tiempo y riesgos de contención. En el módulo Redis esto se demuestra con un contador por partido y `INCRBY`, que mantiene el incremento dentro del servidor.

## TPO y rendimiento

Los trabajos anteriores plantearon picos muy elevados de tráfico y una prioridad de baja latencia para datos en tiempo real. Este laboratorio no pretende reproducir esos valores; demuestra las decisiones de modelado y las operaciones Redis con un conjunto pequeño y repetible.
