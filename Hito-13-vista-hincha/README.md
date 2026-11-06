# Fixture 2030 · Vista del hincha

Recorrido separado en login, menú principal, historial y detalle del partido. El inicio muestra encuentros en juego y próximos; el historial incluye solo finalizados, según el estado consultado en IRIS. Al abrir un encuentro en juego se entra a su tribuna, con comentarios actualizados automáticamente por país. HTML, CSS y JavaScript sin framework; FastAPI sirve la vista y adapta el contrato del Hito 10 para usar un mismo origen.

Todo lo nuevo está en esta carpeta. No modifica la API, las bases, el panel de observabilidad ni su Compose. Rama: `codex/vista-hincha`.

## Iniciar localmente

Python 3.12 o superior. Desde esta carpeta:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8086
```

Abrir http://127.0.0.1:8086. En Windows, usar `.venv\Scripts\pip` y `.venv\Scripts\python`.

Para conectar la API del Hito 10 sin instrumentación:

```bash
FIXTURE_API_URL=http://127.0.0.1:8000 .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8086
```

Por defecto usa `http://127.0.0.1:8001`, la API instrumentada. El panel administrador y esta vista corren por separado.

## Acceso y límites

- **Entrar a mi tribuna:** consulta `GET /sesiones/{usuario_id}`. U001 y U003 se siembran activas, U002 cerrada. Redis distingue sesión inexistente o vencida (404) de dependencia caída (503). Se verifica la sesión en cada operación real. `DELETE /sesiones/{usuario_id}` cierra la sesión en Redis; para volver a entrar hay que sembrarla otra vez.
- La API existente **no tiene registro, contraseñas ni endpoint para crear sesiones**. Este acceso es de laboratorio, no autentica la identidad de una persona. El nombre y país son preferencias de esta vista. No se agregó un login ficticio con contraseña.
- **Explorar la demostración:** acceso explícito a datos sintéticos sin bases. El modo está indicado en todas las pantallas. La tribuna demo vive en memoria y se comparte entre visitantes del mismo país y partido. Cerrar sesión no borra lo publicado; reiniciar el servidor sí. La idempotencia demo se conserva en la sesión que envió el comentario. P-01 está en juego, P-02 finalizado y los otros seis programados: son estados sintéticos para recorrer las pantallas. Nunca se usa como fallback silencioso del modo conectado.
- Cookie local HttpOnly y SameSite=Lax, con identificador aleatorio y vigencia máxima de 30 minutos, limitada por el TTL real. Las sesiones de la vista viven en memoria: usar un solo proceso, sin `--workers`. Solo escuchar en loopback. No es una solución de autenticación para producción.

## Endpoints utilizados

| Experiencia | Contrato existente |
|---|---|
| Acceso / salida | GET y DELETE `/sesiones/{usuario_id}` |
| Fixture | GET `/partidos/P-01` a `/partidos/P-08` (no hay listado general) |
| Estado del encuentro | GET `/partidos/{id}/detalle` (IRIS) |
| Jugadas | GET `/partidos/{id}/eventos` (Neo4j) |
| Planteles | GET `/equipos/{codigo}/jugadores` (MongoDB) |
| Números | GET `/partidos/{id}/estadisticas?desde=…&hasta=…&agregacion=1m` (InfluxDB) |
| Tribuna | GET `/partidos/{id}/comentarios?pais=…&ventana=…&cursor=…` (Cassandra) |
| Comentar | POST `/partidos/{id}/comentarios`, cuerpo original e `Idempotency-Key` |

El servidor toma usuario, nombre y país de la sesión de la vista para comentar. Conserva la misma clave en un reintento del mismo texto/partido para evitar duplicados. Solo se permite comentar si el estado consultado es “En juego”, tanto en la interfaz como en el servidor de esta vista. Al publicar, la tribuna pasa al directo: la API fija `ventana` y `creado_en` con la hora del servidor.

Los comentarios sembrados están en `(P-01, ARG, 2030-06-15T18:30:00Z)`. Las estadísticas sembradas de P-01/P-02 están entre 18:30 y 18:40 UTC de ese día. Los controles muestran tu hora local. Posesión es el promedio de muestras agregadas; pases, tiros y recuperaciones se suman en diez minutos, no en todo el partido. Los marcadores son simulados. La muestra original tiene eventos de Neo4j que no siempre coinciden con el estado de IRIS: la vista conserva ambas fuentes y señala la diferencia.

## Comentarios en directo

El navegador abre `GET /api/directo/{partido_id}/comentarios` mediante EventSource (SSE). El servidor de esta vista consulta los endpoints existentes cada 2 segundos; no modifica Cassandra ni requiere WebSockets o cambios en la API del compañero. Cada ciclo valida la sesión, consulta la partición actual y la anterior para mantener continuidad al cambiar de media hora, y envía los 40 comentarios más recientes sin duplicados. Es una vista reciente, no una exportación de todo el historial. La latencia real depende además del tiempo de respuesta de la API.

La interfaz distingue conectando, sincronizado, sin sincronizar y reconectando; muestra la hora de la última consulta confirmada. Si pasan 10 segundos sin confirmación, deja de indicar sincronización. Un error no se transforma en una lista vacía exitosa. Los reintentos usan la misma clave del envío y el texto permanece si falla. El borrador y el scroll de la tribuna no se reinician por cada actualización.

En el historial la tribuna queda en lectura. El selector permite consultar por separado los comentarios de muestra de 2030. Las páginas tienen rutas `#/inicio`, `#/historial` y `#/partido/P-01`, compatibles con volver/avanzar del navegador.

### Probarlo en dos pestañas

1. Abrir http://127.0.0.1:8086 y elegir “Explorar la demostración”.
2. Entrar a Argentina–Brasil desde “Partidos en curso”. Debe aparecer “En directo · sincronizado”.
3. Abrir la misma dirección del partido en otra pestaña y publicar un mensaje.
4. Verificar que aparece en la primera sin actualizar. La segunda muestra la hora de confirmación del servidor.
5. Volver al inicio → “Ver historial” → España–Francia. Debe mostrar “Finalizado” y tribuna de lectura.
6. Para probar como otra persona, usar otro navegador o una ventana privada, entrar con otro nombre y el mismo país. Si el país es distinto, la tribuna estará separada.

## Observabilidad para el hincha

“Tu experiencia, al día” indica si respondieron las consultas de jugadas, estado, estadísticas y comentarios. Es disponibilidad desde esta vista, no una medición histórica ni de rendimiento. Los p95, CPU, memoria, exportadores, alertas y controles de falla siguen en el panel técnico del compañero. Esta vista no permite cambiar estados ni detener contenedores.

## Verificación

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests -q
```

Las pruebas cubren sesión vencida/cerrada, fallas reales sin fallback, cierre remoto, idempotencia, separación por país, tribuna compartida entre sesiones, clasificación de estados, cierre de comentarios fuera de juego, transición de media hora, eventos SSE, identidad tomada de sesión y contrato de lectura. No necesitan las bases. Para probar el camino real: iniciar Hito 10 + Hito 13, sembrar sesiones y entrar con U001. No se guardan credenciales en el front.
