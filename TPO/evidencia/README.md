# Evidencia de las mediciones

Cada corrida de carga deja dos archivos con el mismo nombre:

- `<nombre>.jsonl`: un pedido por línea, con el segundo en que salió (`t`), la ruta, el estado HTTP y los milisegundos que tardó. En el partido en vivo, un evento por línea (conexión, comentario, entrega, audiencia).
- `<nombre>_resumen.json`: parámetros, entorno, notas, commit y resultado.

El nombre se arma con el escenario, una etiqueta y la fecha y hora en UTC. Las corridas de cierre de partido, la de escrituras directas a MongoDB y la de la réplica de Redis solo tienen resumen, porque no son una ráfaga de pedidos.

Las corridas de esta carpeta se hicieron el 20/11/2026 con `scripts/medir.ps1` y `scripts/prueba_de_falla.ps1`, sobre el commit `4d0ed3d`, sin otros contenedores pesados levantados en la máquina. Cada resumen guarda en `entorno` con qué configuración corrió (`redis_enabled`, `pronosticos_hasta_inicio_real`, `calendario_ttl_segundos`, CPU y procesos de la API). Cómo leerlas: [docs/rendimiento.md](../docs/rendimiento.md).

## Qué es cada corrida

| Archivos | Qué mide | Sección |
|---|---|---|
| `pico_pronosticos_c10/c50/c200_20261120_0435…/0436…` | Pico de pronósticos con 10, 50 y 200 usuarios a la vez | 2.1 |
| `diagnostico_mongo_20261120_050452` | Escrituras directas a MongoDB, sin la API, con tres garantías de escritura. Se corre aparte, por eso dice `"commit": "sin commit"` | 2.2 |
| `lecturas_fixture_c10/c50/c200_20261120_0436…/0437…` | Lecturas del fixture y de jugadas | 2.3 |
| `pico_mixto_20261120_043818` | 70 % pronósticos y 30 % lecturas | 2.3 |
| `pico_pronosticos_c50/c200_api_4cpu_4procesos_…`, `lecturas_fixture_c50/c200_api_4cpu_4procesos_…` | Lo mismo con la API con 4 CPU y 4 procesos | 2.4 |
| `cierre_partido_20000/100000_pronosticos_redis_…` | Tiempo de puntuación al cerrar un partido, puntuando en Redis (lo que levanta Compose), y repetición del cierre | 2.5 |
| `cierre_partido_20000/100000_pronosticos_mongodb_…` | Lo mismo puntuando dentro de MongoDB (`REDIS_ENABLED=false`) | 2.5 |
| `recalculo_puntajes_20261120_0443.txt` | Control: puntajes recalculados desde cero contra los guardados, después de los cuatro cierres | 2.5 |
| `posicion_ranking_c10/c50_redis_…` | Primeros 100 y puesto de un usuario leyendo de Redis, con 100.000 usuarios | 2.6 |
| `posicion_ranking_c10/c50_mongodb_…` | Lo mismo leyendo de MongoDB | 2.6 |
| `pico_pronosticos_sin_copia_del_calendario_…` | Validar el pronóstico consultando Neo4j cada vez (se compara con `pico_pronosticos_c50`) | 2.7 |
| `caida_primario_20261120_045502` | Pronósticos mientras se apaga con orden el primario de MongoDB | 2.8 |
| `caida_primario_corte_brusco_20261120_045721` | Pronósticos mientras se mata el primario | 2.8 |
| `caida_neo4j_corte_brusco_20261120_045940` | Pronósticos mientras se mata Neo4j | 2.8 |
| `vivo_500/1000/2000_espectadores_…` | Partido en vivo con espectadores conectados y comentarios | 2.9 |
| `replica_redis_20261120_045426` | Atraso de la réplica de Redis | 2.9 |
| `vivo_cassandra_europa_corte_brusco_20261120_050158` | Partido en vivo mientras se mata la región Europa de Cassandra | 2.9 |
| `cassandra_europa_corte_brusco_20261120_020404_conteo_por_region.txt` | Comentarios de ese partido contados en cada región, después de la caída (el nombre usa la hora local) | 2.9 |
| `memoria_redis_20261120_045443.txt` | Cuánta memoria ocupa en Redis cada tipo de clave al terminar la serie | 2.10 |

Las corridas de caída guardan en el resumen una línea de tiempo por segundo (`linea_de_tiempo`).

## Capturas

`capturas/grafana_api_y_bases.jpg` y `capturas/grafana_audiencia_influxdb.jpg` son del tablero de Grafana, tomadas el 20/11/2026 durante el desarrollo (commit `5f2ddf7`), con dos simulaciones de tres espectadores cada una. En la primera se ve cómo bajó la demora de InfluxDB al dejar de esperar el volcado a disco ([decisiones.md](../docs/decisiones.md#influxdb)).

## Corridas anteriores

[`anterior/`](anterior/) tiene dos series:

- Las corridas del 17/11/2026: anteriores al primer commit de esta carpeta (dicen `"commit": "sin commit"`) y hechas con los contenedores de los Hitos 10 y 13 levantados en la misma máquina. Se conservan porque la sección 2.3 de [rendimiento.md](../docs/rendimiento.md) cuenta con ellas el antes y el después de dos mejoras.
- Las del 20/11/2026 sobre el commit `9b8f940` (dicen ese commit): la serie completa anterior a que el ranking pasara a Redis. El cierre de partido y el puesto en el ranking de esa serie corresponden al camino de MongoDB. Se conservan para comparar, sobre todo las pruebas de caída, que no dieron siempre lo mismo (sección 2.8).

## Lo que no está acá

- Las corridas hechas con la primera versión del generador de carga, que se saturaba sola. Se descartaron porque medían al generador y no a la API.
- La primera prueba de caída de Neo4j, que mostró el defecto de la copia del calendario. No se conservó.
- Las corridas de prueba del partido en vivo y de la caída de Europa hechas mientras se escribía el código: se borraron porque no correspondían a ningún commit.

Todo eso está contado en [docs/rendimiento.md](../docs/rendimiento.md).

## Para repetirlas

```powershell
.\scripts\medir.ps1
.\scripts\prueba_de_falla.ps1 primario
.\scripts\prueba_de_falla.ps1 primario -Brusco
.\scripts\prueba_de_falla.ps1 neo4j -Brusco
.\scripts\prueba_de_falla.ps1 europa -Brusco -Partido P-10
```
