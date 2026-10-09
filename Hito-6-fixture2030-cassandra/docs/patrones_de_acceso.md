# Patrones de acceso — Comentarios masivos (Hito 6)

Antes de diseñar una sola tabla, esto es lo que el módulo tiene que resolver bien. Todo lo que sigue en `modelo_tabular.md` y `decisiones_de_particionamiento.md` sale de acá.

## Problema de volumen

Durante un partido popular, miles de usuarios comentan al mismo tiempo, sobre todo en los minutos de un gol o una jugada polémica. Ya lo habíamos identificado en el Hito 1: 1M+ comentarios por partido en los casos extremos, con escritura muchísimo más frecuente que lectura puntual (la gente escribe rápido y de a poco, pero el feed se lee todo el tiempo, actualizándose solo).

## Consultas prioritarias (ordenadas por frecuencia esperada)

1. **Traer los últimos comentarios de un partido, para mostrar el feed en vivo.** Es la consulta que más se repite durante todo el partido, una y otra vez, mientras dura el encuentro. Tiene que resolverse tocando la menor cantidad de particiones posible.
2. **Insertar un comentario nuevo.** Escritura constante, en ráfaga durante los goles.
3. **Traer los comentarios de una ventana de tiempo específica de un partido** (por ejemplo, "lo que se dijo en el segundo tiempo"), para navegar hacia atrás en un partido que ya terminó.
4. **Moderar un comentario puntual** (cambiar su estado, por ejemplo a "oculto"), a partir de su identificador exacto.
5. **Borrar un comentario puntual** (por ejemplo, tras una denuncia confirmada), también por su identificador exacto.
6. **Ver el historial de comentarios de un usuario.** Mucho menos frecuente que las anteriores, pero necesaria para moderación o para el perfil del propio usuario.

## Qué NO es prioritario (y por qué importa)

- Buscar comentarios por palabra o texto libre — eso es un trabajo de motor de búsqueda, no de Cassandra, y no lo cubre este módulo.
- Reportes analíticos históricos ("cuántos comentarios hubo por confederación en toda la fase de grupos") — Cassandra no está pensado para ese tipo de consulta agregada y libre; si aparece esa necesidad, va a un motor analítico aparte, no a este módulo.

## Cómo esto condiciona el modelo

- La consulta 1 (feed en vivo) es la que manda: define la clave de partición y el orden de clustering de la tabla principal.
- La consulta 6 (historial por usuario) no se puede resolver con la misma partición que usa el feed — necesita su propia tabla, con su propia clave. Es el caso de duplicación controlada que menciona la consigna.
- Las consultas 4 y 5 necesitan que el identificador completo de un comentario (partición + clustering) sea conocido de antemano — nunca se moderan ni se borran comentarios "a ciegas" filtrando por otro campo.
