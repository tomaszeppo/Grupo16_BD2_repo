# Correcciones del Hito 11

## Devolución del profesor

> La entrega está muy completa y demuestra conectividad real de los seis motores, API y recuperación de Redis. Deben cerrar la evidencia de la falla controlada: la documentación indica conservar la captura redactada de esa prueba, pero docs/evidencia/capturas_redactadas/ está vacío salvo .gitkeep. Incorporen allí la evidencia ejecutada de caída→503→recuperación, vinculada al commit e5f3949.

## A tener en cuenta

| Punto observado | Qué hay hoy | Qué falta |
|---|---|---|
| Captura redactada de la falla controlada | `README.md` y `docs/matriz_de_conectividad.md` dicen que la captura debe conservarse en `docs/evidencia/capturas_redactadas/`, pero la carpeta solo tiene `.gitkeep` | Subir a esa carpeta la evidencia de la secuencia caída de Redis → `503 DEPENDENCIA_NO_DISPONIBLE` → recuperación (`PONG` y `/health` 200), sin contraseñas ni tokens visibles |
| Vínculo con el commit | La ejecución del 22/10/2026 figura con commit observado `e5f3949` en `docs/matriz_de_conectividad.md` | Que la evidencia indique ese commit, la fecha y el `X-Request-ID` de la request que devolvió 503 |

Posible origen de la evidencia: `docs/evidencia/Screenshots Hito 11.pdf` (a revisar si incluye la caída y la recuperación) o una nueva ejecución de `bash scripts/evaluar_conectividad.sh fallo-redis`.

Criterio para los próximos hitos: toda evidencia que la documentación mencione tiene que estar efectivamente en el repositorio, en la ruta indicada.
