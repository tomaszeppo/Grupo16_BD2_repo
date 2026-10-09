import re
d = 'C:/Users/Galli/Desktop/personal/Hitos/Grupo16_BD2_repo/Grupo6-nuestro/redis/docs/'


def leer(n):
    return open(d + n, encoding='utf-8').read()


def escribir(n, t):
    open(d + n, 'w', encoding='utf-8').write(t)


def reemplazar(t, a, b):
    assert a in t, a[:60]
    return t.replace(a, b)


# ------------------------------------------------------------ modelo_clave_valor
t = leer('modelo_clave_valor.md')
t = reemplazar(t, '| Métricas / contadores | `metrica:{tipo}:{id}` |',
               '| Marcador en vivo | `marcador:{partido_codigo}` |\n'
               '| Likes de comentarios | `likes:comentario:{comentario_id}` y `likes:pendientes_sync` |\n'
               '| Límite de comentarios | `ratelimit:comentarios:{usuario_id}` |\n'
               '| Espectadores en vivo | `espectadores:{partido_codigo}` |')
a = t.index('### `metrica:reacciones')
b = t.index('## Por qué estas estructuras y no otras')
t = t[:a] + t[b:]
t = reemplazar(t, '- **Hash con HINCRBY para reacciones:** HINCRBY es atómico por diseño en Redis; no hace falta ni un script ni una transacción para un contador simple.',
               '- **String con INCR para los likes:** INCR es atómico por diseño en Redis; no hace falta ni un script ni una transacción para un contador simple.')
t = reemplazar(t, '### `espectadores:{partido_codigo}` — Sorted Set, sin TTL propio (se poda por score)',
               '### `espectadores:{partido_codigo}` — Sorted Set, TTL de respaldo de 6 horas (además se poda por score)')
t = reemplazar(t, 'sin necesitar que nadie lo borre explícitamente.',
               'sin necesitar que nadie lo borre explícitamente. Como la clave no tiene otro vencimiento, cada latido renueva con `EXPIRE` un TTL de respaldo de 6 horas (junto con el `ZADD`, dentro de `MULTI/EXEC`): si el partido termina y nadie vuelve a latir, la clave se libera sola en lugar de quedar ocupando memoria.')
escribir('modelo_clave_valor.md', t)

# ------------------------------------------------------------ patrones_de_acceso
t = leer('patrones_de_acceso.md')
a = t.index('### 7. Reacciones en vivo de un partido')
b = t.index('## Qué NO es parte de este módulo')
t = t[:a] + ('### 7. Reacciones de los usuarios\n'
             '- Se resuelven con los likes de comentarios (patrón 9). No hay un contador genérico de reacciones por partido: un único conjunto de claves cubre este caso.\n\n') + t[b:]
t = reemplazar(t, 'Los patrones 4 y 7 de arriba (caché de equipo, reacciones genéricas) se armaron al principio para mostrar el mecanismo de Redis, no porque sean el mejor uso real una vez que el sistema esté unificado. Se reemplazan por estos cuatro, que sí salen de necesidades ya identificadas en hitos anteriores:',
               'El patrón 4 de arriba (caché de equipo) se armó al principio para mostrar el mecanismo de Redis, no porque sea el mejor uso real una vez que el sistema esté unificado. Se complementa con estos casos, que sí salen de necesidades ya identificadas en hitos anteriores. Las reacciones genéricas por partido se reemplazaron por los likes del patrón 9:')
t = reemplazar(t, '### 9. Likes de un comentario (reemplaza el contador de reacciones genérico)', '### 9. Likes de un comentario (reemplaza el contador de reacciones genérico del patrón 7)')
t = reemplazar(t, '- **Estructura:** Sorted Set con latido (score = momento del último latido), contando miembros recientes.',
               '- **Estructura:** Sorted Set con latido (score = momento del último latido), contando miembros recientes. Cada latido renueva un TTL de respaldo de 6 horas.')
escribir('patrones_de_acceso.md', t)

# ------------------------------------------------------------ ciclo_de_vida
t = leer('ciclo_de_vida_e_invalidacion.md')
t = reemplazar(t, 'Si Redis se reinicia antes de sincronizar, se pierden los likes acumulados desde la última sincronización — es un costo aceptado y documentado, no un olvido: evitarlo del todo exigiría persistir cada incremento individual, lo cual anula la ventaja de usar un contador en memoria en primer lugar.',
               'Con `appendonly yes` (escritura al archivo de persistencia una vez por segundo), un reinicio del servidor pierde como mucho el último segundo de incrementos. Los likes solo se pierden por completo si se borra el volumen donde Redis guarda sus datos. Sigue siendo un costo aceptado: la fuente de verdad final es Cassandra, y evitar hasta esa pérdida mínima exigiría persistir cada incremento por separado, lo que anula la ventaja de un contador en memoria.')
t = t.rstrip('\n') + '''

## Consistencia por tipo de dato (qué se sacrifica ante una partición)

Ante una partición de red no se pueden garantizar a la vez consistencia y disponibilidad. Para cada tipo de dato de este módulo se eligió qué propiedad se sacrifica y qué impacto se acepta:

| Dato | Se prioriza | Se sacrifica | Impacto que se acepta |
| :--- | :--- | :--- | :--- |
| Sesiones | Disponibilidad | Consistencia inmediata | Un nodo aislado puede seguir aceptando y renovando sesiones. Si dos lados de la partición modifican la misma sesión, al unirse se queda con una sola versión, y un cierre de sesión puede tardar en verse en el otro lado. Es preferible a impedir que los usuarios naveguen. |
| Likes | Disponibilidad | Consistencia inmediata | Los contadores de cada lado pueden diverger un rato, y el valor que se sincroniza a Cassandra puede quedar levemente atrasado. El usuario ve su like al instante. Un conteo apenas desactualizado no afecta a nadie. |
| Espectadores en vivo | Disponibilidad | Consistencia inmediata | El conteo puede ser aproximado mientras dure la partición. Es un dato efímero que se corrige solo con los latidos siguientes. |
| Ranking público | Consistencia dentro de un nodo | Disponibilidad entre nodos | La actualización de puntos, antelación y posición es atómica porque corre en un solo script dentro de un único nodo; no hay estados intermedios visibles. Con una partición, un nodo sin acceso a quien lleva la escritura puede no aceptar actualizaciones del ranking en lugar de aceptar valores que luego haya que reconciliar. |

**Qué es este laboratorio y qué cambia con réplicas.** El ambiente es un único nodo de Redis, así que no hay partición posible entre nodos y la tabla describe el comportamiento que se espera del diseño, no algo que se haya probado. Con réplicas, la replicación de Redis es asincrónica: una réplica puede ir atrasada respecto de quien lleva la escritura, y si este falla y se promueve una réplica, se pierden las escrituras que todavía no habían llegado. Eso es consistente con lo elegido para sesiones, likes y espectadores (se acepta perder o ver con atraso lo último que se escribió a cambio de seguir respondiendo). Para el ranking, donde sí importa no perder ni duplicar una actualización, la escritura seguiría yendo a un único nodo principal.
'''
escribir('ciclo_de_vida_e_invalidacion.md', t)

# ------------------------------------------------------------ memoria_y_escalabilidad
t = leer('memoria_y_escalabilidad.md')
t = reemplazar(t, '## TTL vencido vs. evicción por memoria: la diferencia',
'''## Qué claves tienen TTL y cuáles no

| Clave | TTL | ¿La desaloja `volatile-lru`? |
| :--- | :--- | :--- |
| `sesion:*` y `usuario:*:sesion_activa` | 30 minutos, renovado en cada acceso | Sí |
| `cache:equipo:*` | 5 minutos | Sí |
| `ratelimit:comentarios:*` | 10 segundos | Sí |
| `espectadores:{partido}` | 6 horas de respaldo, renovado en cada latido | Sí |
| `ranking:publico` y `ranking:publico:usuario:*` | ninguno | No |
| `marcador:*` | ninguno | No |
| `likes:comentario:*` y `likes:pendientes_sync` | ninguno | No |

El ranking, el marcador, los likes, `likes:pendientes_sync` y los espectadores (antes del TTL de respaldo) no tienen TTL, y por eso `volatile-lru` no los desaloja. Si la memoria se llena y no quedan claves con TTL para liberar, Redis rechaza las escrituras nuevas con un error en lugar de borrar algo. Por eso `espectadores:{partido}` lleva un TTL de respaldo de 6 horas, renovado con `EXPIRE` en cada latido junto al `ZADD`: sin él, las claves de partidos ya terminados quedarían ocupando memoria que `volatile-lru` no podría recuperar.

## TTL vencido vs. evicción por memoria: la diferencia''')
t = reemplazar(t, '- Ranking: protegido, no se evicta.', '- Ranking, marcador y likes: no se evictan (no tienen TTL). Si no queda memoria libre, lo que falla es la escritura nueva.')
escribir('memoria_y_escalabilidad.md', t)
print('docs ok')
