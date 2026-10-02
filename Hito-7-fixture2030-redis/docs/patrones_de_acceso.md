# Patrones de acceso

El diseño se deriva de los accesos pedidos por el Hito 7 y de los volúmenes definidos en los hitos anteriores: 2–3 millones de usuarios/sesiones simultáneos, lecturas + escrituras de usuarios/sesiones y acceso repetido a datos del Fixture.

## Criterio de diseño

Primero se define la pregunta que debe responder Redis y luego se elige la estructura. No se agrega una estructura por comodidad. Cada clave del módulo tiene una lectura, escritura, actualización o vencimiento concreto.

## Frecuencia y escala

Los hitos anteriores contemplan 2–3 millones de usuarios y sesiones simultáneos y accesos de lectura/escritura; por eso la sesión se busca directamente por una clave estable y no mediante una búsqueda global. El ranking se consulta por partido y el contador se actualiza en el servidor con una operación atómica.

## Qué permanece fuera de Redis

Los datos de negocio persistentes y las relaciones de los módulos anteriores no se convierten en “la verdad” por copiarlos a Redis. En particular, `f2030:cache:partido:P001:resumen` es reconstruible y por eso se documenta como caché.
