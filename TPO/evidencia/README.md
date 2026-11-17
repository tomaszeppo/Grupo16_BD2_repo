# Evidencia de las mediciones

Cada corrida deja dos archivos con el mismo nombre:

- `<nombre>.jsonl`: un pedido por línea, con el segundo en que salió (`t`), la ruta, el estado HTTP y los milisegundos que tardó.
- `<nombre>_resumen.json`: parámetros, entorno, notas y resultado (pedidos por segundo, percentiles, errores por estado y desglose por ruta).

El nombre se arma con el escenario, una etiqueta y la fecha y hora en UTC. Las corridas de cierre de partido y la de escrituras directas a MongoDB solo tienen resumen, porque no son una ráfaga de pedidos.

Todas se hicieron el 17/11/2026 en el entorno descripto en [docs/rendimiento.md](../docs/rendimiento.md), con los contenedores de los Hitos 10 y 13 levantados en la misma máquina. Figuran como `"commit": "sin commit"` porque son anteriores al primer commit de esta carpeta.

## Qué es cada corrida

| Archivos | Qué mide | Condición |
|---|---|---|
| `diagnostico_mongo_20261117_182300` | Escrituras directas a MongoDB, sin la API, con tres garantías de escritura | — |
| `pico_pronosticos_c10_…183009`, `c50_…183042`, `c200_…183115` | Pico de pronósticos con 10, 50 y 200 usuarios a la vez | Antes de las mejoras |
| `lecturas_fixture_c10_…183149`, `c50_…183225`, `c200_…183259` | Lecturas del fixture y de jugadas | Antes de las mejoras |
| `pico_mixto_20261117_183333` | 70 % pronósticos y 30 % lecturas | Antes de las mejoras |
| `lecturas_fixture_c10/c50/c200_listado_desde_la_copia_…` | Lecturas | Con el listado desde la copia del calendario; todavía con una línea de registro por pedido |
| `pico_pronosticos_c10/c50/c200_registro_minimo_…` | Pico de pronósticos | Con las dos mejoras |
| `lecturas_fixture_c10/c50/c200_registro_minimo_…` | Lecturas | Con las dos mejoras |
| `pico_mixto_registro_minimo_20261117_184900` | Pronósticos y lecturas | Con las dos mejoras |
| `pico_pronosticos_c50/c200_api_4cpu_4procesos_…`, `lecturas_fixture_c50/c200_api_4cpu_4procesos_…` | Lo mismo con la API con 4 CPU y 4 procesos | Con las dos mejoras |
| `cierre_partido_20000_pronosticos_…`, `cierre_partido_100000_pronosticos_…` | Tiempo de puntuación al cerrar un partido y repetición del cierre | — |
| `recalculo_puntajes_20261117_191922.txt` | Control: puntajes recalculados desde cero contra los guardados | — |
| `posicion_ranking_c10/c50_100000_usuarios_…` | Primeros 100 y puesto de un usuario, leyendo de MongoDB | — |
| `pico_pronosticos_c50_sin_copia_del_calendario_…` y `…con_copia_del_calendario_…` | Validar el pronóstico consultando Neo4j cada vez, o con la copia | Corridas consecutivas |
| `caida_primario_de_mongodb_20261117_185620` | Pronósticos mientras se apaga con orden el primario | Línea de tiempo por segundo en el resumen |
| `caida_primario_de_mongodb_corte_brusco_20261117_185830` | Pronósticos mientras se mata el primario | Ídem |
| `caida_neo4j_corte_brusco_20261117_190440` | Pronósticos mientras se mata Neo4j | Ídem |

## Lo que no está acá

- Las corridas hechas con la primera versión del generador de carga, que se saturaba sola. Se descartaron porque medían al generador y no a la API.
- La primera prueba de caída de Neo4j, que mostró el defecto de la copia del calendario. No se conservó; la que figura es la posterior a la corrección.

Las dos cosas están contadas en [docs/rendimiento.md](../docs/rendimiento.md).

## Para repetirlas

```powershell
.\scripts\medir.ps1
.\scripts\prueba_de_falla.ps1 primario -Brusco
```
