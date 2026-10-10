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
- **Frecuencia:** en ráfaga justo después de que termina cada partido, y con muchísima concurrencia cuando termina el último del torneo, que es el escenario que más importa resolver bien.
- **Riesgo si no es atómico:** dos actualizaciones del mismo usuario que se pisen y se pierda una.
- **Estructura:** Sorted Set actualizado con `ZINCRBY`, que suma el delta al score de forma atómica.

### 6. Ver el ranking público
- **Quién:** cualquier usuario, en cualquier momento, muy frecuentemente durante y después del torneo.
- **Entrada:** ninguna (o un rango, para paginar).
- **Respuesta:** la tabla ordenada, de primero a último.
- **Frecuencia:** altísima en lectura.
- **Temporal:** es una proyección calculada a partir de las predicciones (cuya fuente de verdad, a futuro, será el módulo documental). Si se pierde, se puede reconstruir recalculando desde ahí — por eso es caché en sentido amplio, aunque no tenga TTL (ver `memoria_y_escalabilidad.md`).
- **Estructura:** Sorted Set (ZSET). Es la estructura de Redis pensada exactamente para esto: mantiene el orden siempre actualizado en O(log N) por escritura, sin tener que ordenar nada al leer.

### 7. Contar visitas de un partido (concurrencia simple)
- **Quién:** la aplicación, cada vez que un usuario abre un partido.
- **Entrada:** `partido_codigo`. **Respuesta:** contador actualizado.
- **Frecuencia:** muy alta durante los partidos populares.
- **Estructura:** string con `INCRBY`, atómico sin necesidad de otro mecanismo; si hay que actualizar también un dato de apoyo, se agrupa en `MULTI/EXEC`.

## Qué NO es parte de este módulo

- Los datos completos de equipos, jugadores, partidos y predicciones — viven en Mongo, Neo4j o Cassandra según corresponda. Redis nunca es la fuente de verdad de nada acá.
- Autenticación o verificación de contraseña — este módulo asume que el usuario ya fue autenticado por otro componente; Redis solo administra la sesión una vez que eso ya pasó.
