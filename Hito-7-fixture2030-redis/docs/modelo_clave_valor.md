# Modelo clave/valor y nomenclatura

## Namespace

Se usa el prefijo `f2030:` para reconocer que la clave pertenece al Fixture 2030. Los niveles siguientes expresan dominio y alcance.

- `f2030:sesion:{usuario_id}` → sesión activa del usuario.
- `f2030:cache:partido:{partido_id}:resumen` → copia temporal de una consulta frecuente.
- `f2030:ranking:partido:{partido_id}:figura` → ranking temporal por partido.
- `f2030:contador:partido:{partido_id}:visitas` → contador temporal por partido.
- `f2030:contador:partido:{partido_id}:meta` → metadatos de la operación concurrente.
- `f2030:demo:usuario:{id}` → datos sintéticos de apoyo al laboratorio.

Se usa `:` como separador legible. Los identificadores son estables y no dependen de nombres descriptivos que puedan cambiar.

## Sesión como Hash

La sesión no se guarda como JSON completo porque las operaciones frecuentes son parciales: cambiar `ultimo_acceso`, incrementar `acciones` y mantener el resto intacto. La clase utiliza Hash para este patrón y aclara que el TTL pertenece a la clave completa.

## Caché como String

Una respuesta serializada se recupera directamente con `GET`. El módulo no necesita modificar campos internos del JSON en Redis; si cambia la fuente de verdad, se invalida la copia completa y se reconstruye.

## Ranking como Sorted Set

El Sorted Set asocia cada miembro a un score y permite pedir el Top N con `ZREVRANGE ... WITHSCORES` sin traer todos los candidatos a la aplicación para ordenarlos.

## Concurrencia

El contador se diseña con `INCRBY`. Esto evita la secuencia insegura `GET → sumar en código → SET`. Para la renovación de sesión se utiliza `MULTI/EXEC` porque intervienen varias operaciones que deben quedar juntas: actualización del campo, contador y renovación del TTL.

## Inspección

No se usa `KEYS *`. El script de métricas utiliza `SCAN 0 MATCH f2030:* COUNT 100`, coherente con la inspección segura enseñada en clase.
