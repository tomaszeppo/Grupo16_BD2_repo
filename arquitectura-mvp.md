# Arquitectura del Fixture 2030

Vista general de la plataforma que se fue armando a lo largo de los hitos. Los diagramas están escritos en Mermaid: GitHub los dibuja a partir del texto de los bloques `mermaid`.

## 1. Componentes y fuentes de datos

Cada base resuelve un tipo de acceso distinto. La API (Hito 10) tiene un adaptador por base y cada endpoint consulta solo la fuente que le corresponde.

```mermaid
flowchart LR
    subgraph clientes["Consumidores"]
        postman["Postman / Newman<br/>(colección de 38 requests)"]
        swagger["Swagger UI"]
        carga["Generador de carga<br/>(Hito 12)"]
    end

    subgraph api["API REST · FastAPI (Hito 10)"]
        rutas["routes<br/>HTTP y validación"]
        servicios["services<br/>casos de uso"]
        adaptadores["adapters<br/>un driver por base"]
        rutas --> servicios --> adaptadores
    end

    subgraph bases["Fuentes operacionales"]
        mongo[("MongoDB<br/>datos persistentes e historial<br/>equipos, jugadores y detalle de partidos")]
        neo4j[("Neo4j<br/>estructura del fixture y relaciones<br/>jugadores, partidos y jugadas<br/>Hito 5")]
        cassandra[("Cassandra<br/>comentarios<br/>Hito 6")]
        redis[("Redis<br/>sesiones, prode y ranking en tiempo real<br/>resultados durables → MongoDB")]
        influx[("InfluxDB<br/>actividad de app y jugadas<br/>series temporales")]
    end

    datamart[("Data Mart · SQLite<br/>actividad de comentarios<br/>Hito 12")]

    postman --> rutas
    swagger --> rutas
    adaptadores -- "/equipos, detalle y estado" --> mongo
    adaptadores -- "/fixture, relaciones y eventos" --> neo4j
    adaptadores -- "/comentarios" --> cassandra
    adaptadores -- "/sesiones" --> redis
    adaptadores -- "/estadisticas" --> influx
    adaptadores -- "/detalle, /estado" --> mongo
    carga -- "50.000 INSERT directos<br/>(sin pasar por la API)" --> cassandra
    cassandra -. "extracción por lotes" .-> datamart
```

## 2. Crear un comentario (escritura con dos bases)

`POST /partidos/{id}/comentarios` es el único endpoint que combina fuentes: verifica el partido en Neo4j y guarda en Cassandra. La `Idempotency-Key` permite reintentar sin duplicar.

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant API as API (FastAPI)
    participant N as Neo4j
    participant K as Cassandra

    C->>API: POST /partidos/{id}/comentarios + Idempotency-Key
    API->>N: ¿existe el partido?
    alt el partido no existe
        API-->>C: 404
    else el partido existe
        API->>K: INSERT comentarios_idempotencia IF NOT EXISTS
        alt la clave ya se usó para otro partido o país
            API-->>C: 409
        else clave nueva, o reintento del mismo comentario
            opt es un reintento
                API->>K: leer ventana, fecha e id originales
            end
            API->>K: INSERT comentarios_por_partido_pais IF NOT EXISTS
            API->>K: INSERT comentarios_por_likes_partido_pais IF NOT EXISTS
            API->>K: leer el comentario guardado
            API-->>C: 201 si es nuevo, 200 si es un reintento
        end
    end
```

## 3. Prueba de carga y Data Mart (Hito 12)

Camino que sigue la prueba: se carga, se verifica que no falte ni sobre nada, y recién después se proyecta la vista analítica.

```mermaid
flowchart TD
    gen["prueba_rendimiento.py<br/>datos sintéticos, semilla fija"]
    perfilA["Perfil A<br/>1 proceso × 100 en curso"]
    perfilB["Perfil B<br/>2 procesos × 50 en curso"]
    tabla[("Cassandra<br/>comentarios_por_partido<br/>13 particiones")]
    monitor["registrar_base.py<br/>CPU y memoria de contenedores"]
    verif{"verificar_escrituras.py<br/>¿50.000 guardadas y<br/>13 conteos correctos?"}
    extraer["proyectar_comentarios.py<br/>lee las 13 particiones"]
    sqlite[("actividad.sqlite<br/>una fila por partido y minuto")]
    lector["consultar_proyeccion.py v1.1<br/>consultas SQL"]
    descartar["La corrida no se usa<br/>y se conserva como evidencia"]

    gen --> perfilA & perfilB
    perfilA --> tabla
    perfilB --> tabla
    monitor -. "mide en paralelo" .-> tabla
    tabla --> verif
    verif -- "sí" --> extraer --> sqlite --> lector
    verif -- "no" --> descartar
```
