# Conservación de versiones del experimento

Regla del usuario: los cambios futuros se harán en una versión nueva; la anterior queda
histórica. No se borran ni sobrescriben fuentes, datos ni resultados anteriores.

| Versión | Estado |
|---|---|
| `v2.0_base/` | Histórico del código/configuración de base-20261030-002022, identificado por manifiesto y hashes |
| `v2.1_candidata_c50/` | Candidata implementada con concurrencia 50, perfil validado y trazabilidad; carga real y decisión pendientes |
| `v2.2_candidata_paralelo/` | M02: control A 1x100 y candidata B 2x50, datos iguales e inicio coordinado; nueve pruebas offline aprobadas; carga y decisión pendientes |

Antes de cada cambio:

1. Registrar hipótesis, evidencia, variables, riesgo y prueba según 5.5.
2. Crear otra carpeta desde la referencia y conservarla sin modificaciones.
3. Cambiar una variable por vez en la copia nueva y registrar el diff.
4. Mantener el medidor para comparar; guardar hashes y parámetros efectivos.
5. Usar nuevas carpetas, IDs y nombres de contenedores por corrida, sin pisar resultados.
6. Agregar resultado real y decisión sin reescribir la hipótesis previa.

El commit no identifica por sí solo archivos locales no versionados: conservar los hashes.
Las imágenes y dependencias realmente observadas están en el manifiesto y las evidencias.
La versión del experimento puede cambiar solo por configuración; eso no exige cambiar
el instrumento de medición. No se ejecutaron cargas para crear estas copias.

Los manifiestos históricos describen el momento de su conservación y no se actualizan
para reflejar estados futuros. El índice de esta carpeta informa qué versiones existen hoy.
