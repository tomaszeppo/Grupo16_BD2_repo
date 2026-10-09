# Patrones de acceso — Caché de usuarios y sesiones (Hito 7)

Antes de definir una sola clave, esto es lo que el módulo tiene que resolver. Todo lo que sigue en `modelo_clave_valor.md` sale de acá.

## Problema de concurrencia

Durante los partidos, millones de usuarios navegan la plataforma en simultáneo: consultan equipos, ven el ranking, y sus sesiones quedan activas mientras dura la navegación. El caso que más nos preocupa, y el que motivó este módulo en particular, es el cierre del ranking público: cuando termina el último partido del torneo, muchísimos usuarios actualizan su puntaje casi al mismo tiempo, y varios pueden terminar empatados en puntos. Si el desempate no está resuelto de antemano en la propia estructura de datos, hay que recalcularlo aparte cada vez que alguien pide ver la tabla — lento, y con riesgo de mostrar un primer puesto que después cambia.

## Patrones de acceso

### 1. Crear sesión
- **Quién:** la aplicación, cuando un usuario inicia sesión.
- **Entrada:** `usuario_id`.
- **Respuesta:** un `sesion_id` nuevo, con la sesión marcada activa.
- **Frecuencia:** una vez por inicio de sesión; baja comparada con el resto.
- **Temporal:** sí, vive en Redis únicamente. No hay "fuente de verdad" de sesiones en otro módulo — es exactamente el tipo de estado que Redis existe para resolver.
- **Estructura:** hash (`sesion:{id}`) por los varios campos que describe una sesión, más una clave de puntero (`usuario:{id}:sesion_activa`) para encontrar la sesión de un usuario sin recorrer nada.

### 2. Validar / renovar sesión (en cada request del usuario)
- **Quién:** la aplicación, en cada acción del usuario ya logueado.
- **Entrada:** `sesion_id` (normalmente viajando en una cookie o un header).
- **Respuesta:** si la sesión existe, se renueva su vencimiento y se la trata como válida; si no existe (venció o nunca existió), se la trata como anónima.
- **Frecuencia:** la más alta de todo el módulo — se dispara en cada acción del usuario.
- **Temporal:** sí.
- **Estructura:** mismo hash de arriba, renovando su TTL con cada acceso (sesión de ventana deslizante).

### 3. Cerrar sesión
- **Quién:** la aplicación, cuando el usuario cierra sesión explícitamente.
- **Entrada:** `sesion_id`.
- **Respuesta:** confirmación de cierre.
- **Frecuencia:** baja.
- **Temporal:** sí, se borra directamente (no espera al TTL).

### 4. Consultar un dato de catálogo frecuente (caché)
- **Quién:** la aplicación, cada vez que alguien ve la info de un equipo.
- **Entrada:** `codigo` del equipo.
- **Respuesta:** los datos del equipo.
- **Frecuencia:** muy alta en lectura; el dato real casi no cambia (el catálogo de equipos es estable, según el Hito 1).
- **Fuente de verdad:** el módulo documental de MongoDB (Hito 4). Redis guarda una copia de acceso rápido, nunca el original.
- **Estructura:** string con el JSON del equipo (`cache:equipo:{codigo}`), TTL corto para no servir una copia vieja por mucho tiempo.

### 5. Actualizar puntaje de una predicción (operación concurrente crítica)
- **Quién:** la aplicación, cada vez que se confirma el resultado de un partido y se recalculan los puntos de las predicciones afectadas.
- **Entrada:** `usuario_id`, delta de puntos, delta de antelación (ver `ciclo_de_vida_e_invalidacion.md` para de dónde sale ese segundo valor).
- **Respuesta:** puntaje actualizado, reflejado al instante en el ranking.
- **Frecuencia:** en ráfaga justo después de que termina cada partido — y con muchísima concurrencia justo cuando termina el último partido del torneo, que es el escenario que más nos importa resolver bien.
- **Riesgo si no es atómico:** dos actualizaciones del mismo usuario que se pisen, o un cálculo de desempate que quede desactualizado un instante.
- **Estructura:** hash con los valores crudos del usuario + ZSET con el score combinado ya resuelto (ver abajo). Se actualizan juntos, en un solo paso atómico.

### 6. Ver el ranking público
- **Quién:** cualquier usuario, en cualquier momento, muy frecuentemente durante y después del torneo.
- **Entrada:** ninguna (o un rango, para paginar).
- **Respuesta:** la tabla ordenada, de primero a último.
- **Frecuencia:** altísima en lectura.
- **Temporal:** es una proyección calculada a partir de las predicciones (cuya fuente de verdad, a futuro, será el módulo documental). Si se pierde, se puede reconstruir recalculando desde ahí — por eso es caché en sentido amplio, aunque no tenga TTL (ver `memoria_y_escalabilidad.md`).
- **Estructura:** Sorted Set (ZSET). Es la estructura de Redis pensada exactamente para esto: mantiene el orden siempre actualizado en O(log N) por escritura, sin tener que ordenar nada al leer.

### 7. Reacciones de los usuarios
- Se resuelven con los likes de comentarios (patrón 9). No hay un contador genérico de reacciones por partido: un único conjunto de claves cubre este caso.

## Qué NO es parte de este módulo

- Los datos completos de equipos, jugadores, partidos y predicciones — viven en Mongo, Neo4j o Cassandra según corresponda. Redis nunca es la fuente de verdad de nada acá.
- Autenticación o verificación de contraseña — este módulo asume que el usuario ya fue autenticado por otro componente; Redis solo administra la sesión una vez que eso ya pasó.

---

## Revisión: de demos a casos reales

El patrón 4 de arriba (caché de equipo) se armó al principio para mostrar el mecanismo de Redis, no porque sea el mejor uso real una vez que el sistema esté unificado. Se complementa con estos casos, que sí salen de necesidades ya identificadas en hitos anteriores. Las reacciones genéricas por partido se reemplazaron por los likes del patrón 9:

### 4′. Marcador en vivo de un partido (reemplaza la caché de equipo como ejemplo principal de RF6/RF7)
- **Por qué esto y no el catálogo de equipos:** 64 equipos que casi no cambian apenas se benefician de caché — Mongo ya responde rápido ahí. El marcador en vivo sí lo justifica: en Neo4j (Hito 5) el resultado de un partido no es un campo guardado, es un cálculo (contar nodos `Evento` de tipo `Gol` conectados al partido, por equipo) — carísimo de recalcular en cada request de millones de usuarios mirando el mismo partido.
- **Entrada:** `partido_codigo`. **Respuesta:** goles por equipo, minuto, último evento.
- **Frecuencia:** lectura altísima durante el partido; escritura rara (solo cuando hay un evento nuevo).
- **Fuente de verdad:** Neo4j (`Partido`, `Evento`, Hito 5).
- **Estructura:** hash, actualizado por escritura (no por TTL) — ver `ciclo_de_vida_e_invalidacion.md`.

### 9. Likes de un comentario (reemplaza el contador de reacciones genérico del patrón 7)
- **De dónde sale:** en el Hito 6 (Cassandra) quedó documentado como limitación que `likes` era un int plano sin atomicidad real, porque Cassandra no deja mezclar counters con otros campos en la misma tabla.
- **Quién:** cualquier usuario, al reaccionar a un comentario.
- **Frecuencia:** muy alta en los comentarios de un gol.
- **Fuente de verdad final:** Cassandra (`comentarios_por_partido.likes`), pero el conteo en caliente vive en Redis y se sincroniza después — Cassandra no es buena recibiendo escrituras de +1 constantes sobre la misma fila.
- **Estructura:** contador simple (`INCR`) + un set de comentarios con cambios pendientes de sincronizar.

### 10. Límite de comentarios por usuario (rate limiting) — nuevo, no existía en ningún hito
- **Por qué hace falta:** nada en el módulo de Cassandra frena a un usuario (o un bot) mandando cientos de comentarios por segundo durante un partido viral.
- **Quién:** la aplicación, antes de aceptar un comentario nuevo.
- **Estructura:** contador con ventana fija (`INCR` + `EXPIRE NX`).

### 11. Espectadores en vivo de un partido — nuevo, estaba en el diagnóstico del Hito 1 y se había perdido
- **De dónde sale:** el Hito 1 pedía "cantidad de gente en vivo" como parte de Interacciones; terminó absorbido por Cassandra junto con Comentarios, pero un conteo de presencia instantánea es puramente efímero — no tiene sentido como historial en una tabla.
- **Quién:** la aplicación, con un latido periódico mientras el usuario tiene el partido abierto.
- **Estructura:** Sorted Set con latido (score = momento del último latido), contando miembros recientes. Cada latido renueva un TTL de respaldo de 6 horas.
