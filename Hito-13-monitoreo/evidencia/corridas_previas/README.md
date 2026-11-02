# Corridas previas

Se conservan tal como se generaron. No son la evidencia final, pero muestran cómo llegamos a ella.

## Primera corrida (21:59 a 22:04)

- Archivos: `pico_comentarios_20261030_215941*`, `estado_partido_20261030_220108.json` (partido `P-03`), `prueba_de_falla_20261030_220355.json` y `demo_20261030_2159_todo/`.
- **Resultado:** los tres momentos funcionaron (3.000 de 3.000 comentarios verificados, 409 al volver atrás, Redis caído y recuperado con la sesión intacta).
- **Por qué no es la final:** el colector de disponibilidad todavía esperaba a que respondieran todas las bases. Con Redis caído, la recolección de la API llegó a 3,99 s, contra un límite de 4 s ([`../recoleccion_api_falla_preliminar.json`](../recoleccion_api_falla_preliminar.json)). Lo corregimos y repetimos la prueba con el código final.
- De acá sale el p95 de Redis en condiciones normales que citamos (7,25 ms como máximo antes de la caída).

## Segunda corrida (22:19 a 22:24)

- Archivos: `pico_comentarios_20261030_221907*`, `estado_partido_20261030_222034.json` (partido `P-04`), `prueba_de_falla_20261030_222321.json` y `demo_20261030_222336_todo/`.
- **Por qué no es la final:**
  - Las sesiones sembradas a las 21:50 vencieron durante la prueba (TTL de 30 minutos): la sesión `U001` dio 404 después de la caída por vencimiento, no por la falla.
  - Además, la API recién reiniciada abrió sus conexiones en la primera recolección (más de 4 s y una recolección perdida a las 22:18:50), y en el primer minuto todas las bases marcaron unos 375 ms.
  - Repetimos con sesiones nuevas y la API ya en caliente.
