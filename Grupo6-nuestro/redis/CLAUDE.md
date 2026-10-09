# Fixture 2030 — Hito 7 (caché de usuarios y sesiones en Redis)

Contexto para retomar este proyecto en Claude Code. Viene de una conversación
larga en claude.ai donde se diseñó y se armó todo esto. A diferencia de los
Hitos 4 y 6, acá **sí se pudo probar la lógica de verdad** (con `fakeredis`,
un Redis en memoria simulado en Python, no el Redis real): el script de
actualización del ranking, el patrón de caché, y las sesiones con TTL se
ejecutaron y se confirmó que el comportamiento es el esperado. Lo que falta
es validarlo contra el Redis real del `docker-compose.yml` (versión real,
persistencia en disco, memoria real).

## Qué es esto

TP de Ingeniería de Datos II, Grupo 6, caso de estudio "Fixture 2030". Este
es el Hito 7: módulo de sesiones y caché sobre Redis. La consigna completa
debería estar como PDF en el repositorio; si no está, pedirla.

## El problema central que resuelve este módulo

Cuando termina el último partido del torneo, muchos usuarios quedan
empatados en puntos en el ranking público. La regla de desempate es: gana
quien cargó sus pronósticos con más antelación respecto de cada partido,
sumando la antelación de **todas** sus predicciones (acumulativo, no solo
la última actualización). Esto se resuelve con un Sorted Set cuyo score
combina puntos (parte entera) y antelación normalizada (parte decimal), así
`ZREVRANGE` devuelve la tabla ya ordenada y desempatada sin ningún paso de
recálculo. El detalle completo, con el caso de prueba usado, está en
`docs/ciclo_de_vida_e_invalidacion.md`.

## Ya validado (con fakeredis, no con Redis real)

- El script de actualización atómica del ranking
  (`scripts/actualizar_ranking.lua`, y su versión de una sola línea en
  `concurrencia.redis`): probado con el caso exacto de tres usuarios
  empatados en 300 puntos y distinta antelación acumulada — el orden
  resultante es el correcto.
- `carga_muestra.redis` completo: se ejecutó línea por línea contra
  fakeredis y da 42 claves (10 sesiones × 2 + 6 cachés de equipo + 15
  usuarios en el ranking), con el ranking en el orden documentado en el
  README.
- El patrón de sesión (crear, renovar TTL, cerrar) y el patrón de caché
  (miss, hit, invalidación) con comandos básicos de Redis — sin
  complicaciones, son comandos estándar.

## Tarea principal: validar contra Redis real

1. Levantar el ambiente: `docker compose up -d` (requiere que exista
   `~/docker/data/redis` en el host — el usuario trabaja en Windows, ver
   README para la nota de WSL2).
2. Correr `scripts/inicializacion.redis` y confirmar la versión real de
   Redis (`INFO server`) y que `maxmemory`/`maxmemory-policy` quedaron
   como se configuraron en `docker-compose.yml`.
3. Correr `scripts/carga_muestra.redis` y confirmar con `ZREVRANGE
   ranking:publico 0 -1 WITHSCORES` que el orden coincide con lo que dice
   el README (ya validado en fakeredis, debería ser idéntico).
4. Correr `scripts/sesiones.redis`, `scripts/cache.redis`,
   `scripts/concurrencia.redis` y `scripts/metricas.redis`, confirmando
   que cada uno da lo que describe su propio archivo.
5. Correr `scripts/prueba_rendimiento.py --operaciones 10000` (requiere
   `pip install redis`) contra el contenedor real, y completar la
   plantilla de `docs/rendimiento.md` con el resultado real — ese archivo
   ya existe con la plantilla lista, solo falta llenarla con una medición
   real (RF12/RF13).
6. Sacar las capturas de `docs/evidencia/CAPTURAS_PENDIENTES.md` y
   guardarlas ahí, reemplazando ese archivo de texto.

## Decisiones de modelo (ya cerradas, no re-discutir salvo pedido explícito)

- `maxmemory-policy volatile-lru`: protege el ranking (sin TTL) de
  eviction bajo presión de memoria; sacrifica sesiones y caché (con TTL)
  primero. Está justificado en `docs/memoria_y_escalabilidad.md`.
- TTL de sesión: 30 minutos, ventana deslizante (se renueva en cada
  acción del usuario), usando el `EXPIRE` nativo de Redis — nunca un
  barrido manual.
- TTL de caché de equipo: 5 minutos, con invalidación explícita (`DEL`) en
  el momento en que cambia la fuente de verdad en Mongo, no solo
  esperando al TTL.
- El ranking usa un Sorted Set con score combinado (puntos + antelación
  normalizada), actualizado con un script Lua atómico vía `EVAL`/`EVALSHA`
  — no dos comandos sueltos, porque es un patrón de lectura-modificación-
  escritura que necesita atomicidad real.
- Divisor de normalización de antelación: 10.000.000 (cota muy por encima
  de cualquier antelación acumulada real en minutos). Si se cambia la
  unidad de antelación (por ejemplo, a días en vez de minutos), hay que
  revisar que este divisor siga siendo suficientemente grande.

## Preferencias del usuario para este proyecto

- Redacción natural y suelta en toda la documentación, como si la hubiera
  escrito el propio grupo — evitar anglicismos y jerga tipo "trade-off",
  "ad-hoc", "stack"; evitar tono genérico de IA.
- Prefiere validar con evidencia real antes de dar algo por entregado.
- Antes de la entrega final, este `CLAUDE.md` (y cualquier carpeta
  `.claude/` de la sesión de trabajo) se borra — no son parte de lo que se
  entrega al profesor. Los hitos anteriores (4, 5, 6) siguieron ese mismo
  patrón.

## Regla de negocio pendiente (para el futuro módulo de Predicciones)

Este hito ya implementa la mecánica del desempate (antelación acumulada),
pero la fuente de verdad real de las predicciones y sus puntajes —el
módulo documental que las calcula y dispara las actualizaciones hacia este
ranking de Redis— todavía no existe como tal. Cuando se construya ese
módulo, el delta de puntos y antelación que hoy se pasa a mano al script
de `concurrencia.redis` va a salir de ahí.
