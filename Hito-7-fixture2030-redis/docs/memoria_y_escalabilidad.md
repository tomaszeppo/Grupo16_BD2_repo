# Memoria y escalabilidad — Caché de usuarios y sesiones (Hito 7)

## Política elegida

```
maxmemory 256mb
maxmemory-policy volatile-lru
```

`volatile-lru` evicta, cuando hace falta liberar memoria, las claves que tienen TTL puesto, empezando por las usadas menos recientemente. Las claves sin TTL (el ranking) **nunca se evictan bajo presión de memoria** con esta política — si no hay más espacio y solo quedan claves sin TTL por liberar, Redis directamente rechaza la escritura en lugar de borrar algo que no debería perderse.

## Por qué esta política y no otra

- `allkeys-lru` quedó descartada: evictaría también las claves del ranking si hiciera falta espacio, y el ranking es justo el dato que no queremos perder así porque sí (aunque técnicamente sea reconstruible desde la fuente de verdad, reconstruirlo bajo presión en medio del cierre del torneo es el peor momento posible para tener que hacerlo).
- `noeviction` quedó descartada: con esa política, Redis simplemente rechaza cualquier escritura nueva una vez lleno, incluidas las de sesión — eso significaría usuarios que no pueden loguearse durante un pico de tráfico, que es peor que perder alguna caché vieja.
- `volatile-lru` separa el problema correctamente: las cosas genuinamente temporales (sesiones, caché) pueden sacrificarse bajo presión; el ranking, no.

## Qué claves tienen TTL y cuáles no

| Clave | TTL | ¿La desaloja `volatile-lru`? |
| :--- | :--- | :--- |
| `sesion:*` y `usuario:*:sesion_activa` | 30 minutos, renovado en cada acceso | Sí |
| `cache:equipo:*` | 5 minutos | Sí |
| `cache:partido:*:resumen` | 30 segundos | Sí |
| `contador:partido:*` | 1 hora | Sí |
| `ranking:publico` | ninguno | No |

El ranking no tiene TTL y por eso `volatile-lru` no lo desaloja. Si la memoria se llena y no quedan claves con TTL para liberar, Redis rechaza las escrituras nuevas con un error en lugar de borrar algo. Por eso todo lo demás lleva TTL.

## TTL vencido vs. evicción por memoria: la diferencia

- **TTL vencido:** Redis sabe exactamente cuándo expira cada clave con TTL puesto, y la elimina en cuanto se cumple el plazo (de forma perezosa, al accederla, o en un barrido en segundo plano) — es un vencimiento previsto, documentado, parte del diseño.
- **Evicción por memoria:** pasa antes de que se cumpla el TTL, si el servidor se queda sin espacio. Es una consecuencia de que el servidor está bajo presión, no una decisión del diseño del dato en sí. Con `volatile-lru`, solo le puede pasar a sesiones o caché — nunca al ranking.

**Efecto sobre cada tipo de dato si se queda sin memoria:**
- Sesiones: alguna sesión poco usada se evicta antes de su TTL natural — el usuario queda deslogueado antes de lo esperado, pero no es un error de datos, solo una sesión que termina antes.
- Caché de equipo: se evicta y listo — el siguiente `GET` es un miss común, se reconstruye desde Mongo sin que nadie note la diferencia salvo una lectura más lenta esa vez.
- Ranking: no se evicta (no tiene TTL). Si no queda memoria libre, lo que falla es la escritura nueva.

## Por qué 256MB para este laboratorio

No es un número arbitrario: es una cota chica a propósito, para forzar que la política de evicción realmente se ponga a prueba con el volumen de datos de muestra de este hito, en vez de quedar como una configuración que nunca se usa. Para producción, el cálculo sería otro — una estimación aproximada:

| Dato | Tamaño aprox. por entrada | Cantidad en pico (según Hito 1 y 3) | Total aproximado |
| :--- | :--- | :--- | :--- |
| Sesión (hash + puntero) | ~250 bytes | 2.000.000 a 3.000.000 de usuarios simultáneos | ~500-750 MB |
| Caché de equipo | ~300 bytes | 64 equipos (todo el catálogo cabe fácil) | ~20 KB |
| Ranking público (ZSET) | ~80 bytes por usuario | Varios millones de participantes | Cientos de MB, según cuántos usuarios predicen |

Solo las sesiones en el pico de un partido popular ya superan ampliamente los 256MB de este laboratorio — es exactamente la evidencia de que **un solo nodo local no alcanza para producción**, y de que esto necesitaría Redis Cluster (particionado horizontal entre varios nodos) o, como mínimo, réplicas de lectura con Sentinel para alta disponibilidad. Este ambiente es de aprendizaje; no se presenta en ningún momento como una topología productiva.

## Pendiente

- Medir el tamaño real de una sesión serializada contra el supuesto de 250 bytes de la tabla de arriba, en vez de estimarlo.
