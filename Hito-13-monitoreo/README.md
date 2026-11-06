# Hito 13 - Monitoreo y defensa final del Fixture 2030

Sumamos Prometheus y Grafana a la plataforma que ya teníamos: la API del Hito 10 y sus seis bases (MongoDB, Neo4j, Cassandra, Redis, InfluxDB e IRIS). No cambiamos ningún archivo de hitos anteriores. La API se usa tal cual y se le agregan las métricas desde este hito.

## Qué hay y dónde

| Tema | Documento |
|---|---|
| Qué se monitorea, con qué mecanismo y qué riesgo observa cada componente | [Inventario de componentes](docs/inventario_de_componentes.md) |
| Configuración de Prometheus, métricas, consultas PromQL con unidad y período | [Métricas y consultas](docs/metricas_y_consultas.md) |
| Las cuatro alertas, con severidad, impacto y acción | [Alertas y umbrales](docs/alertas_y_umbral.md) |
| Por qué cada base, distribución, consistencia y fallas | [Decisiones de arquitectura](docs/decisiones_de_arquitectura.md) |
| Qué medimos, qué no, prueba de falla y mejora propuesta | [Limitaciones y evidencia](docs/limitaciones_y_evidencia.md) |
| Cómo vamos a mostrar el sistema en la defensa | [Defensa final](docs/defensa_final.md) |
| Lo que pensamos para el TP final y no metimos acá | [Proyecto final planteado](docs/proyecto_final_planteado.md) |
| El panel de Grafana | [grafana/README.md](grafana/README.md) |
| Capturas, series y registros de las pruebas | [evidencia/](evidencia/README.md) |

## Estructura

```text
docker-compose.yml       API instrumentada (8001), Prometheus (9090), Grafana (3000), exportadores y renderizador
Dockerfile.api           imagen de la API instrumentada (el código del Hito 10 se monta en solo lectura)
prometheus.yml           intervalo, destinos y etiquetas
prometheus/              reglas de alerta
grafana/                 datasource y panel aprovisionados desde archivos
api_instrumentada/       envoltura que agrega /metrics a la API del Hito 10
scripts/                 iniciar, verificar destinos, prueba controlada, limpiar
panel_web/               panel técnico (8085): métricas de Prometheus y botón "Simular situaciones"
vista_hincha/            vista del hincha (8086): pantallas del Fixture sobre la API
tests/                   pruebas de la instrumentación y del generador de comentarios (sin bases)
docs/                    documentación del hito
evidencia/               resultados de las pruebas, sin secretos
```

## Requisitos

- Docker Desktop con Compose v2 (probado con v5.6.0) y unos 6 GB de RAM libres para las seis bases y el monitoreo.
- PowerShell (Windows) para los scripts del hito. El Hito 10 usa bash (Git Bash o WSL).
- Python 3.12 en el host, solo para la prueba controlada y los tests. La API corre en su contenedor.

## Puesta en marcha (en este orden)

1. **Bases del Hito 10.** Desde `Hito-10-fixture2030-APIREST`, con su `.env` completo (ver su README):

   ```bash
   bash scripts/levantar_servicios.sh
   ```

   Levanta las seis bases en la red `fixture2030_net` y carga los datos de laboratorio (partidos `P-01` a `P-08`, sesiones `U001` a `U003`, etc.).

2. **Entorno de Python del hito** (una sola vez), desde esta carpeta:

   ```powershell
   python -m venv .venv
   .venv\Scripts\pip install -r requirements-scripts.txt
   ```

3. **Monitoreo.** Copiar `.env.example` a `.env` y poner una contraseña para Grafana. Después:

   ```powershell
   & .\scripts\iniciar_monitoreo.ps1
   ```

   Construye la API instrumentada y levanta todo. Las credenciales de las bases se leen del `.env` del Hito 10; no se copian.

4. **Verificar destinos.**

   ```powershell
   & .\scripts\verificar_targets.ps1            # tabla de destinos y disponibilidad de las seis bases
   & .\scripts\verificar_targets.ps1 -Guardar   # además guarda la evidencia en evidencia/
   ```

   Sale con código 1 si algún destino está DOWN. Qué revisar en ese caso: [inventario, sección "Si un destino está DOWN"](docs/inventario_de_componentes.md#si-un-destino-está-down).

| Servicio | Dirección |
|---|---|
| API con métricas (Swagger) | http://127.0.0.1:8001/docs |
| Métricas crudas de la API | http://127.0.0.1:8001/metrics |
| Prometheus, destinos | http://127.0.0.1:9090/targets |
| Prometheus, alertas | http://127.0.0.1:9090/alerts |
| Grafana, panel "Fixture 2030 — Plataforma" | http://127.0.0.1:3000 (usuario `admin`, contraseña del `.env`) |
| Panel técnico (paso 5) | http://127.0.0.1:8085 |
| Vista del hincha (paso 5) | http://127.0.0.1:8086 |

5. **Panel técnico y vista del hincha** (opcionales). Corren en el host, cada uno en su terminal. La primera vez, instalar sus dependencias en el mismo entorno:

   ```powershell
   .venv\Scripts\pip install -r panel_web\requirements.txt -r vista_hincha\requirements.txt
   cd panel_web;    ..\.venv\Scripts\python -m uvicorn server:app --host 127.0.0.1 --port 8085
   cd vista_hincha; ..\.venv\Scripts\python -m uvicorn server:app --host 127.0.0.1 --port 8086
   ```

   El panel técnico consulta Prometheus y muestra lo mismo que los 15 paneles de Grafana, más el estado de las cuatro reglas de alerta. Cada base indica si se mide solo desde la API o también con exportador. La vista del hincha está explicada en [vista_hincha/README.md](vista_hincha/README.md).

## Repetir la demostración

### Desde el panel técnico: "Simular situaciones"

El botón **Simular situaciones** corre seis situaciones seguidas, sin intervención, en unos 6 minutos:

| Situación | Qué hace | Qué se mira |
|---|---|---|
| 0. Preparación | Vuelve a sembrar las sesiones de Redis si vencieron y elige un partido en "Programado" (P-08, P-06 o P-02) | Consola de actividad |
| 1. Operación normal | 40 s de lecturas contra las seis bases: es la línea de base | Pedidos por segundo, latencia por base, exportadores |
| 2. Pico de comentarios | El mismo momento `pico` de abajo | Tráfico, comentarios por país, p99 de crear comentarios frente al umbral de 500 ms |
| 3. Cambio de estado | El momento `estado` sobre el partido elegido | Respuestas por código: aparece el 409 |
| 4. Caída de Redis | El momento `falla` | Disponibilidad, 503, destinos y reglas de alerta |
| 5. Captura | Guarda los 15 paneles y las series de todo el recorrido en `evidencia/dashboards/recorrido_<fecha>/` | Consola de actividad |

Mientras corre, una barra indica la situación actual y qué mirar, y los gráficos correspondientes se marcan con "MIRAR". Pide confirmación antes de empezar, porque detiene Redis y deja un partido en "Finalizado" sin vuelta atrás. Si no queda partido en "Programado", la situación 3 se saltea y el resto sigue. La situación 1 también se puede correr sola con `.venv\Scripts\python scripts\prueba_controlada.py normal --duracion 40`.

### Desde la terminal

```powershell
& .\scripts\ejecutar_prueba_controlada.ps1                    # los tres momentos y las capturas (unos 5 minutos)
& .\scripts\ejecutar_prueba_controlada.ps1 -Momento pico      # solo la ráfaga de comentarios
& .\scripts\ejecutar_prueba_controlada.ps1 -Momento estado -PartidoEstado P-04
& .\scripts\ejecutar_prueba_controlada.ps1 -Momento falla     # caída y recuperación de Redis
```

1. **Pico de comentarios:** 3.000 comentarios a 50 por segundo, repartidos entre ARG, BRA, ESP y MAR, contra `POST /partidos/P-01/comentarios`. Cada corrida usa claves de idempotencia nuevas y al final verifica en Cassandra que estén todos y sin duplicados.
2. **Estado del partido en IRIS:** `Programado → En juego → Finalizado`, y un intento de volver a `En juego` que debe ser rechazado (409).
3. **Falla de Redis:** con tráfico de fondo, se detiene el contenedor de Redis 75 s y se vuelve a iniciar. No se borra su volumen.

Al terminar se guardan en `evidencia/dashboards/` las capturas de los 15 paneles y las series de Prometheus de esa ventana.

**Para repetir el momento de estado:** la transición no tiene vuelta atrás, así que cada ensayo necesita un partido en "Programado". En nuestras corridas ya se usaron `P-03`, `P-04` y `P-05`; quedan `P-06` y `P-07` (pasarlos con `-PartidoEstado`). La siembra de IRIS del Hito 10 no pisa partidos existentes, así que no los vuelve a "Programado".

**Antes del momento de falla:** las sesiones vencen a los 30 minutos sin uso. Si se sembraron hace más, volver a sembrarlas desde la carpeta del Hito 10 con `docker compose --profile api run --rm api python -m seed.run --solo redis`; si no, la sesión `U001` da 404 por vencimiento y no se puede ver que sobrevive a la caída.

## Tests

```powershell
.venv\Scripts\python -m pytest tests -q
```

Prueban la instrumentación (plantilla de ruta como etiqueta, errores, reintentos de comentarios que no cuentan, base caída) y el generador de comentarios. No necesitan las bases. Los 118 tests unitarios del Hito 10 siguen pasando sin cambios.

## Limpieza segura

```powershell
& .\scripts\limpiar_entorno.ps1
```

Detiene solo los contenedores de este hito. Conserva los volúmenes de Prometheus y Grafana y no toca las bases del Hito 10. Para detenerlas, `docker compose stop` desde la carpeta del Hito 10. **No usar `docker compose down -v`**, que borra los volúmenes.

Si se usa `docker compose` a mano en esta carpeta, hay que pasar los dos archivos de entorno, como hacen los scripts:

```powershell
docker compose --env-file .env --env-file ..\Hito-10-fixture2030-APIREST\.env ps
```

## Seguridad

No se versionan `.env`, contraseñas ni tokens. La contraseña de MongoDB llega al exportador como variable de entorno, no dentro de una URI escrita en el repo. Las capturas y los registros de `evidencia/` se revisaron antes de subirlos.
