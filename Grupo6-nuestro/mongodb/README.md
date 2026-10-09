# Fixture 2030 — Módulo Documental (Hito 4)

Módulo de persistencia de Equipos y Jugadores del Fixture 2030, sobre MongoDB.
Retoma las decisiones del Hito 2 (modelo Documental) y del Hito 3 (Información
deportiva con prioridad de disponibilidad y consistencia eventual). El detalle
completo está en `docs/decisiones-de-diseno.md`.

## Qué incluye

```
mongodb/
├── docker-compose.yml            Ambiente MongoDB (mongo:7)
├── .env.example                  Modelo del .env (el .env real no se versiona)
├── init-scripts/                 Corren solos la primera vez que se levanta el contenedor
│   ├── 01-create-collections.js    Colecciones y validación
│   ├── 02-create-indexes.js        Índices
│   └── 03-load-data.js             Llama a scripts/cargar-datos.js
├── scripts/
│   └── cargar-datos.js           Carga de 64 equipos y 1.536 jugadores (upsert, se puede repetir)
├── queries/
│   ├── 01-consultas-recuperacion.js  find, filtros, proyección, paginación, agregaciones
│   ├── 02-actualizaciones.js         Inserción y actualización (comprueba matchedCount)
│   ├── 03-analisis-indices.js        explain() con y sin índice
│   └── 04-verificar-idempotencia.js  Recarga, compara totales y prueba el índice único
├── schemas/
│   └── modelo-documental.md      Estructura de cada colección
├── docs/
│   ├── decisiones-de-diseno.md   Tabla de decisiones y vínculo con los otros hitos
│   └── evidencia/                Salidas reales de consola de cada prueba
└── README.md
```

## Cómo levantarlo

Hace falta Docker Desktop corriendo.

1. Crear un archivo `.env` en esta carpeta tomando `.env.example` como base,
   con el usuario y la clave de administración. No se versiona, y el
   `docker-compose.yml` no trae valores por defecto: sin `.env` no levanta.

2. Levantar el contenedor:

   ```
   docker compose up -d
   docker compose ps
   ```

   La primera vez (con el volumen vacío) Mongo ejecuta los tres scripts de
   `init-scripts/` en orden: crea las colecciones con validación, después los
   índices y por último carga los datos (el tercero llama a
   `scripts/cargar-datos.js`). Si volvés a correr `docker compose up -d` con
   el volumen ya creado, esos scripts **no** se ejecutan de nuevo, así
   funciona el mecanismo de Mongo.

3. Verificar que levantó bien:

   ```
   docker exec fixture2030-mongodb mongosh --eval "db.adminCommand('ping')"
   ```

4. Entrar y confirmar la carga:

   ```
   docker exec -it fixture2030-mongodb sh -c 'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin fixture2030'
   ```

   Las credenciales las toma el propio contenedor del `.env`, así que no hay
   que escribir la clave. El comando sirve igual en PowerShell, `cmd` y bash.

   Adentro de `mongosh`:

   ```
   db.equipos.countDocuments()      // esperado: 64
   db.jugadores.countDocuments()    // esperado: 1536
   ```

## Cómo correr las consultas

Las carpetas `queries/` y `scripts/` se montan en `/queries` y `/scripts` dentro
del contenedor y los archivos se corren enteros con el mismo patrón:

```
docker exec fixture2030-mongodb sh -c 'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin fixture2030 --file /queries/01-consultas-recuperacion.js'
```

- `01-consultas-recuperacion.js`: lectura, filtros, proyección, paginación y las
  dos agregaciones.
- `02-actualizaciones.js`: inserción y actualización. Imprime el `matchedCount`
  de cada update y corta con error si no encontró el documento. Al final borra
  los documentos de prueba. Deja cambios en la base (ranking de MAR, un gol de
  ARG-10, JPN-07 no convocado) que la recarga de datos no pisa.
- `03-analisis-indices.js`: `explain()` con y sin índice (IXSCAN contra COLLSCAN).
- `04-verificar-idempotencia.js`: cuenta, vuelve a cargar, cuenta de nuevo y
  compara (esperado 64 y 1.536 las dos veces). También prueba que un segundo
  `ARG` lo rechaza el índice único (error E11000).

## Recargar los datos con el contenedor ya creado

```
docker exec fixture2030-mongodb sh -c 'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin fixture2030 --file /scripts/cargar-datos.js'
```

La carga hace un upsert por `codigo`, así que se puede repetir sin duplicar: la
segunda vez informa 0 documentos nuevos y los mismos totales. Los datos de
referencia se corrigen si cambiaron en el script; `convocado`, `estadisticas` y
el contador de convocados solo se escriben cuando el documento no existía, para
no perder lo acumulado durante el torneo.

## Reiniciar o empezar de cero

- **Reiniciar sin perder datos**: `docker compose restart`. El volumen
  (`fixture2030_mongo_data`) sobrevive.
- **Empezar de cero**: `docker compose down -v && docker compose up -d`. Borra
  el volumen y vuelve a correr los `init-scripts`.

## Variables de entorno

El usuario y la clave de MongoDB se definen en `MONGO_ROOT_USER` y
`MONGO_ROOT_PASSWORD`, dentro de un `.env` que no se versiona. No están escritas
en el `docker-compose.yml`.
