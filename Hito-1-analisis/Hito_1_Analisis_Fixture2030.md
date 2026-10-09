# Hito 1 — Identificación de datos y problemas de SQL (Fixture 2030)

Grupo 16 · Ingeniería de Datos II

## 1. Identificación de datos

| Dato | Volumen | Crecimiento | Acceso |
| :--- | :--- | :--- | :--- |
| Partidos | 127 | Fijo | Lectura y escritura |
| Selecciones | 64 | Fijo | Lectura |
| Estadios | 20 | Fijo | Lectura |
| Jugadores | Más de 1.500 | Fijo | Lectura |
| Estadísticas de grupos y partidos | 16 grupos × cantidad de estadísticas por grupo | Crece después de cada partido | Lectura y escritura |
| Grupos privados | Máximo 5 por usuario | Crecimiento masivo al inicio del torneo | Lectura y escritura |
| Usuarios | 2 a 3 millones simultáneos | Crecimiento masivo inicial, con posibilidad de seguir creciendo | Lectura y escritura |
| Sesiones | 2 a 3 millones simultáneas | Irregular, con picos masivos después de cada partido | Lectura y escritura |
| Estadísticas de partido | Más de 1.000 por partido | Crecen mientras se juega | Lectura y escritura |

Los datos se agrupan en tres familias que se comportan distinto:

- **Datos de referencia**, casi fijos y de poco volumen: selecciones, estadios y jugadores.
- **Datos que cambian rápido durante los partidos**: partidos, estadísticas de grupos y partidos, y estadísticas de partido.
- **Datos ligados a la cantidad de usuarios conectados**: usuarios, sesiones y grupos privados.

## 2. Problemas que aparecen con una base relacional

La base relacional es la referencia con la que se compara. Se la evalúa por el volumen que tiene que sostener, la velocidad con que debe responder, la forma en que se accede a cada dato, la flexibilidad de su estructura y la facilidad para crecer. Sus garantías transaccionales (ACID) son valiosas y siguen siéndolo donde la información tiene que quedar exacta; lo que se analiza es dónde el modelo relacional deja de ser la mejor opción para este caso.

| Dato | Problema |
| :--- | :--- |
| Partidos | El partido ocurre en tiempo real y recibe muchísimas lecturas y escrituras por segundo para ajustar sus valores. Repartir la información en varias tablas relacionadas obliga a tocar varias filas por cada cambio, y la latencia crece en algo que debe verse de inmediato. |
| Selecciones | Son 64 registros con una estructura anidada (plantel, cuerpo técnico, ranking) que casi no cambian. Armarlas en varias tablas obliga a unirlas cada vez que se consulta una selección completa. |
| Estadios | Son pocos datos y estables. Mantener una tabla propia y unirla a los partidos agrega estructura sin aportar flexibilidad. |
| Jugadores | Misma situación que las selecciones: datos estables con estructura propia, que se leen casi siempre junto con su selección. |
| Estadísticas de grupos y partidos | Muchos usuarios pueden actualizar resultados y posiciones a la vez, sobre todo al terminar un partido. Eso genera competencia por las mismas filas, consultas agregadas costosas y demoras al recalcular las posiciones de cada grupo. |
| Usuarios | Durante un partido entran millones de usuarios a revisar su información. Si el acceso no está pensado para esa cantidad de lecturas, aparece latencia. |
| Grupos privados | Al comienzo del mundial muchísimas personas se anotan al mismo tiempo. Un volumen tan masivo de altas puede dejar el sistema lento en el momento más crítico de las inscripciones. |
| Estadísticas de partido | Registran momento a momento lo que pasa en cada partido. Sumando todos los partidos del mundial, la tabla crece de forma drástica y se vuelve difícil de manejar con una sola base relacional. |

## 3. Propuesta de modelos NoSQL

Para cada tipo de dato se propone el modelo más adecuado, la razón de la elección, sus ventajas frente a la base relacional y las alternativas que se consideraron.

| Dato | Modelo propuesto | Razón de la elección | Ventajas frente a SQL | Alternativas consideradas |
| :--- | :--- | :--- | :--- | :--- |
| Partidos | Documental (MongoDB) | Cada partido se representa como un único documento con su estado y sus eventos. | Se actualiza un solo documento en lugar de varias tablas relacionadas. Encaja con el volumen alto de lecturas y escrituras en tiempo real. | Clave-valor (Redis): se pensó para el marcador en vivo, pero no sirve como registro histórico del partido. Grafos (Neo4j): útil para los cruces del fixture, pero no resuelve la latencia en vivo, que es la prioridad. |
| Selecciones | Documental (MongoDB) | Pocos datos con una estructura anidada (plantel, cuerpo técnico, ranking). | Se lee la selección completa en una sola consulta, sin unir tablas de jugadores y cuerpo técnico. | Clave-valor: se pierde la estructura anidada. Seguir en SQL: el volumen es bajo, pero se descartó por coherencia con el resto de la arquitectura. |
| Estadios | Documental (MongoDB) | Mismo criterio que las selecciones: pocos datos, estables, de consulta poco frecuente. | Evita mantener una tabla relacional completa solo para 20 registros; el estadio se puede incluir en el partido si conviene. | Seguir en SQL: se descartó para no mezclar dos formas de guardar datos de referencia parecidos. |
| Jugadores | Documental (MongoDB) | Documento por jugador, con sus estadísticas históricas incluidas. | No requiere una tabla separada de estadísticas, y admite sumar torneos o temporadas más adelante. | Grafos (Neo4j): se pensó para relaciones jugador–selección–partido, pero no hay necesidad real de recorrer relaciones complejas entre jugadores. |
| Estadísticas de grupos y partidos | Clave-valor (Redis) | El problema es la competencia por actualizar las mismas posiciones al mismo tiempo. | Leer y actualizar una tabla de posiciones es una operación muy rápida, sin recalcular agregados como en SQL. | Documental (MongoDB): un documento por grupo con la tabla de posiciones incluida; se descartó porque reescribir el documento completo en cada actualización es menos eficiente. |
| Grupos privados | Documental (MongoDB) | El problema es el volumen masivo de altas al inicio del torneo. | Crear un grupo es insertar un único documento con hasta 5 miembros, sin tablas de relación de muchos a muchos. | Clave-valor: se consideró (id de grupo y lista de miembros), pero el modelo documental permite filtrar por otros campos del grupo sin perder simplicidad. |
| Usuarios | Documental (MongoDB) | Hay muchísimos usuarios consultando su perfil durante el partido. | Un documento por usuario permite lecturas directas por identificador y preferencias variables sin migraciones. | Clave-valor puro: se descartó como modelo principal porque el perfil tiene estructura que conviene poder filtrar; queda como candidato para una capa complementaria en momentos de pico. |
| Sesiones | Clave-valor (Redis) | Es el caso típico de clave-valor: un identificador de sesión y los datos asociados, con vencimiento. | Acceso por clave muy rápido y capacidad para millones de sesiones simultáneas en memoria. | Documental: se descartó porque las sesiones no necesitan estructura anidada ni consultas complejas. |
| Estadísticas de partido | Columnar (Cassandra) | Crecimiento drástico momento a momento durante todos los partidos. | Pensado para escrituras masivas y sostenidas, sin degradarse a medida que crece el volumen. | Series temporales (InfluxDB): también encaja con datos momento a momento y fue seriamente considerado. Se optó por Cassandra como referencia de grandes volúmenes de datos, aunque ambas opciones son técnicamente válidas. |

### Resumen

| Dato | Modelo | Motivo principal |
| :--- | :--- | :--- |
| Partidos | Documental (MongoDB) | Estado del partido y sus eventos en un solo documento |
| Selecciones | Documental (MongoDB) | Dato estable con estructura anidada |
| Estadios | Documental (MongoDB) | Dato estable y de bajo volumen |
| Jugadores | Documental (MongoDB) | Dato estable con estadísticas incluidas |
| Estadísticas de grupos y partidos | Clave-valor (Redis) | Posiciones que se leen y actualizan muy rápido |
| Grupos privados | Documental (MongoDB) | Altas masivas al inicio, sin relaciones de muchos a muchos |
| Usuarios | Documental (MongoDB) | Perfil con estructura flexible y consulta por campos |
| Sesiones | Clave-valor (Redis) | Acceso rápido por clave |
| Estadísticas de partido | Columnar (Cassandra) | Escritura masiva y sostenida durante todo el torneo |

## 4. Conclusión

Se identificaron 9 tipos de datos del Fixture 2030, agrupados en las tres familias descritas: datos de referencia, datos que cambian rápido durante los partidos y datos ligados a la cantidad de usuarios conectados.

Los números del proyecto son el argumento principal para no depender de una única base relacional: entre 2 y 3 millones de usuarios simultáneos, picos de más de 100.000 solicitudes por segundo y un objetivo de 99,99 % de disponibilidad. Con ese volumen, esa velocidad y esa forma de acceso, una sola base relacional que crece solo en vertical no alcanza.

El modelo relacional ofrece consistencia fuerte, y esa garantía se conserva donde hace falta. Los modelos propuestos permiten, en cambio, flexibilizar la estructura y repartir la carga entre varios tipos de motor según el dato, que es lo que muestran los casos de empresas como Twitter, Amazon o Netflix vistos en clase: ninguna usa un único modelo, y una arquitectura políglota es el camino más realista también para el Fixture 2030.

Este análisis es la base teórica para el resto del cuatrimestre. En los próximos hitos se va a refinar la matriz de decisión y después se va a pasar a la implementación, donde se podrá confirmar en la práctica si las elecciones (sobre todo las alternativas descartadas) siguen siendo las más apropiadas.
