# Grupo16_BD2_repo

Hitos de la cursada Base de Datos II (profesor Salas), caso "Fixture 2030". Grupo 16.

| Hito | Contenido | Carpeta |
| :--- | :--- | :--- |
| 1 | Identificación de datos y problemas de SQL | `Hito-1-analisis/` |
| 2 | Matriz de decisión de los seis modelos para cada necesidad | `Hito-2-matriz-decision/` |
| 3 | Arquitectura distribuida: CAP, replicación, escenarios de falla | `Hito-3-arquitectura-distribuida/` |
| 4 | MongoDB: equipos y jugadores | `Hito-4-fixture2030-mongodb/` |
| 5 | Neo4j: fixture, partidos, eventos y entidades deportivas | `Hito-5-fixture2030-neo4j/` |
| 6 | Cassandra: comentarios masivos | `Hito-6-fixture2030-cassandra/` |
| 7 | Redis: caché de usuarios y sesiones | `Hito-7-fixture2030-redis/` |
| 8 | InfluxDB: estadísticas | `Hito-8-fixture2030-influxdb/` |
| 9 | InterSystems IRIS: entidades complejas (Partido, Evento, Persona) | `Hito-9-fixture2030-iris/` |

Los hitos 1 a 3 son documentos en Markdown; los PDF de la entrega anterior (reemplazados por
estos `.md`) quedan en `descartado/`, fuera de la entrega. Los hitos 4 a 9 son módulos que levantan con
`docker compose up -d`. Cada uno trae su README con los pasos, un `.env.example` cuando
usa credenciales (el `.env` real no se versiona) y su evidencia en `docs/evidencia/`.

Los hitos 4 a 9 usan el mismo criterio de identificación: códigos de equipo de tres letras según el
estándar FIFA (`ARG`, `GER`, `JPN`…), jugadores como `XXX-NN` y partidos como `P-NN`. Es la convención
que en algún momento va a permitir correlacionar datos entre los seis módulos cuando se integren como
un único sistema; todavía no arrancamos esa etapa de integración (sin red Docker ni compose compartido
entre módulos), pero cada módulo nuevo debe respetar estos códigos desde el vamos para no tener que
migrar datos después. Ver `CHANGELOG.md` para el historial de correcciones de consistencia entre módulos.
