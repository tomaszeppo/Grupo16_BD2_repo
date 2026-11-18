# Prode Mundial 2030 — proyecto final

Aplicación de prode para el Mundial 2030: los usuarios pronostican cada partido, suman puntos y compiten en un ranking general y en prodes privados con amigos.

Esta carpeta es independiente de los hitos: se levanta sola y no usa nada de las otras carpetas del repositorio.

## Qué hay construido

| Parte | Base | Estado |
|---|---|---|
| Usuarios, prodes, pronósticos, puntuación, ranking | MongoDB (tres nodos) | Construido |
| Fixture, partidos, jugadas y sus cadenas | Neo4j | Construido |
| API y interfaz de demostración | — | Construido |
| Sesiones y ranking en vivo | Redis | Punto de enganche listo |
| Comentarios por partido y región | Cassandra | Lectura reciente y publicación |
| Series temporales de simulación | InfluxDB | Posesión, tiros, pases, faltas y córners por equipo |
| Monitoreo | Prometheus y Grafana | La API ya expone `/metrics` |

IRIS no forma parte del proyecto final: [por qué](docs/por_que_no_iris.md).

## Documentación

- [Decisiones sobre las bases](docs/decisiones.md): qué guarda cada una, por qué, qué pasa si falla y qué cuesta.
- [Rendimiento](docs/rendimiento.md): qué medimos, qué mejoramos y qué no podemos afirmar.
- [Modelo de datos](docs/modelo_de_datos.md)
- [La API](docs/api.md)
- [Cómo sumar una base](docs/como_sumar_una_base.md): para Redis, Cassandra, InfluxDB y el monitoreo.
- [Por qué IRIS no entra](docs/por_que_no_iris.md)
- [Evidencia de las mediciones](evidencia/README.md)

## Levantar el entorno

Hace falta Docker Desktop. Todos los comandos se corren desde esta carpeta (`TPO`), en PowerShell.

```powershell
.\scripts\levantar.ps1
```

La primera vez crea el archivo `.env` y se detiene: hay que completar ahí `MONGO_PASSWORD`, `NEO4J_PASSWORD` (8 caracteres o más) y `ADMIN_CLAVE` con valores propios, y volver a correr el script. El archivo `.env` no se versiona.

Levanta tres nodos de MongoDB, Neo4j, Cassandra, InfluxDB y la API. El chequeo de salud del TPO informa MongoDB y Neo4j; Cassandra e InfluxDB todavía no aparecen allí. Cuando termina:

- Interfaz de demostración: http://127.0.0.1:8010/demo/
- Contrato de la API: http://127.0.0.1:8010/docs
- Estado de las bases: http://127.0.0.1:8010/health/dependencias

Después, cargar los datos de laboratorio:

```powershell
docker compose run --rm herramientas python -m seed.run --dias-hasta-inicio 3
```

Carga 48 equipos, sus planteles y los 104 partidos, con el primer partido sin jugar ubicado a tres días de hoy. Se puede repetir: no duplica nada. Para comprobarlo:

```powershell
docker compose run --rm herramientas python -m seed.run --verificar
```

Puertos en el equipo: 8010 (API), 27217 a 27219 (MongoDB), 7475 y 7688 (Neo4j) y 9043 (Cassandra). InfluxDB no publica puerto al equipo. Si alguno está ocupado, cambiarlo en `.env`; los hitos pueden usar algunos de los mismos puertos.

## Recorrer la demostración

1. Abrir http://127.0.0.1:8010/demo/ y crear un usuario.
2. En **Fixture**, entrar a un partido programado y cargar un pronóstico.
3. Entrar al primer partido (ya jugado) y tocar "¿De dónde vino?" en un gol: muestra la cadena de jugadas recorrida en Neo4j.
4. En **Administración** (pide la `ADMIN_CLAVE` del `.env`): elegir el partido pronosticado, ponerlo en juego, cargar un par de jugadas y cerrarlo. Se ve la puntuación paso por paso.
5. En **Ranking**, ver el puesto del usuario.
6. En **Mis prodes**, crear uno, compartir el código y ver su tabla.

Cada bloque de la pantalla tiene una etiqueta con la base que respondió.

Para empezar de cero entre un ensayo y otro (borra usuarios, pronósticos y resultados del laboratorio):

```powershell
docker compose run --rm herramientas python -m seed.run --reiniciar --dias-hasta-inicio 3
```

## Pruebas

Las unitarias no necesitan bases. Hace falta Python 3.12:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest tests/unit -q
```

Las de integración corren contra MongoDB y Neo4j reales, dentro de Docker:

```powershell
docker compose run --rm -e PERMITIR_REINICIO=1 herramientas python -m pytest tests/integration -q
```

En MongoDB usan una base aparte y no tocan los datos del laboratorio. En Neo4j no se puede (la edición comunitaria tiene una sola base), así que **borran el grafo**; por eso piden `PERMITIR_REINICIO=1`. Después hay que volver a cargar los datos con `seed.run --reiniciar`.

## Mediciones y pruebas de falla

```powershell
.\scripts\medir.ps1                              # toda la serie de carga; borra los datos de laboratorio al empezar
.\scripts\prueba_de_falla.ps1 primario           # apaga con orden el primario de MongoDB durante una carga
.\scripts\prueba_de_falla.ps1 primario -Brusco   # lo corta de golpe
.\scripts\prueba_de_falla.ps1 neo4j -Brusco      # corta Neo4j
```

Cada corrida deja su resultado en [`evidencia/`](evidencia/README.md). Las pruebas de falla detienen un contenedor de este proyecto y lo vuelven a levantar; no borran datos. Los resultados y cómo leerlos están en [docs/rendimiento.md](docs/rendimiento.md).

Para ver el detalle de cada pedido en el registro de la API: poner `LOG_NIVEL=DEBUG` en `.env` y correr `docker compose up -d api`. Por defecto se anotan solo los problemas.

## Mirar las bases directamente

```powershell
# MongoDB (pide la contraseña del .env)
docker compose exec mongo1 mongosh -u admin -p --authenticationDatabase admin prode2030

# Neo4j (pide la contraseña del .env); también en http://127.0.0.1:7475
docker compose exec neo4j cypher-shell -u neo4j
```

Desde fuera de Docker (Compass, por ejemplo) se puede entrar a un nodo de MongoDB con conexión directa: `mongodb://admin:<contraseña>@127.0.0.1:27217/?directConnection=true&authSource=admin`. No se puede usar la dirección del conjunto de réplicas completo, porque los nodos se anuncian con sus nombres internos de Docker.

## Detener

```powershell
.\scripts\limpiar.ps1                # detiene los contenedores y conserva los datos
.\scripts\limpiar.ps1 -BorrarDatos   # además borra los volúmenes de este proyecto
```

## Si algo no anda

- **La interfaz dice que una base no responde.** Mirar http://127.0.0.1:8010/health/dependencias y `docker compose ps`. Recién levantado, Neo4j tarda un rato en quedar listo; `docker compose ps` lo muestra como `healthy` cuando está.
- **"Falta el encabezado X-Admin-Clave o no es correcto".** La clave es la `ADMIN_CLAVE` del `.env`. Si se cambió, hay que correr `docker compose up -d api`.
- **Un puerto está ocupado.** Cambiarlo en `.env` (están listados en `.env.example`).
- **El fixture muestra un partido con el estado viejo.** El listado sale de una copia que se renueva cada 30 segundos; el detalle del partido está siempre al día.

## Estructura

```
TPO/
├── app/          la API: rutas, servicios, adaptadores (uno por base) y puertos
├── seed/         datos de laboratorio y carga en las dos bases
├── carga/        generador de carga y escenarios de medición
├── scripts/      levantar, limpiar, medir, pruebas de falla y control de puntajes
├── ui/           interfaz de demostración
├── tests/        pruebas unitarias y de integración
├── docs/         documentación
├── evidencia/    resultados de las mediciones
└── mongo/        arranque del conjunto de réplicas
```


## Estadísticas de la simulación (InfluxDB)

La simulación registra cada minuto una muestra sintética por equipo: posesión instantánea, tiros, tiros al arco, pases, faltas y córners de ese minuto. La pantalla muestra el promedio de posesión, suma las acciones y calcula la precisión de pases. El marcador sigue en MongoDB y el estado en Neo4j. Las simulaciones anteriores no contienen las nuevas métricas y se muestran con un guion. Si una escritura falla se marca la información como incompleta; no hay reintentos automáticos.

Compose inicia InfluxDB 3 y crea la base `fixture2030_metrics`. El contenedor está limitado por defecto a 0,5 CPU y 1 GB y usa un volumen propio. Para este laboratorio funciona sin autenticación, accesible solo desde la red interna de Docker y sin puerto publicado; no usar esta configuración para un despliegue compartido. Se puede ajustar `INFLUX_CPUS` e `INFLUX_MEMORIA` en `.env`.


## Histórico en Neo4j

Al finalizar una simulación, el TPO consulta las muestras por equipo y minuto de InfluxDB y sus resúmenes. Si están las 91 muestras de ambos equipos y los goles coinciden con el marcador, las guarda en Neo4j como relaciones `ESTADISTICA_MINUTO` y `RESUMEN_ESTADISTICO` entre el partido y sus equipos. El guardado usa claves estables y se puede repetir sin duplicar. `GET /partidos/{id}/historico` devuelve el resumen y los 182 puntos archivados; después del archivo, el bloque de estadísticas consulta Neo4j.

Cada simulación usa un guion de jugadas de MongoDB y, al terminar, lo cruza con las muestras de InfluxDB. Neo4j conserva los eventos, sus jugadores y las relaciones entre jugadas, además de los totales y las muestras por minuto. Las acciones estadísticas sintéticas que no están en el guion siguen siendo contadores, no jugadas individuales. Si faltan muestras o falla el traspaso, el partido puede quedar finalizado con `archivo_estado=pendiente`. Un administrador puede reintentar con `POST /administracion/simulaciones/{id}/archivar` y el encabezado `X-Admin-Clave`. Las simulaciones antiguas sin muestras completas o sin goles por minuto no pueden archivarse como completas.


## Preparar jugadas simuladas

La plantilla editable es [`seed/guion_simulacion.json`](seed/guion_simulacion.json): cada entrada indica tipo, minuto, equipo (`local` o `visitante`), dorsal y, opcionalmente, el número de una jugada anterior en `previa`. Los dorsales se resuelven contra los jugadores ya cargados en MongoDB y se usan los mismos IDs del grafo.

Con el entorno levantado y el fixture cargado, ejecutar desde `TPO` en PowerShell:

```powershell
.\scripts\cargar_guion.ps1 -Partido P-12
```

Se puede repetir sin borrar ni sobrescribir el guion ya guardado. Al iniciar una simulación sin guion, se crea automáticamente desde la plantilla. La plantilla se aplica solamente a nuevos guiones; editarla no modifica los que ya se guardaron. No usar `seed.run --reiniciar` para este procedimiento.
