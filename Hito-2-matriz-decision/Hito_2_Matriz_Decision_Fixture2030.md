# Hito 2 — Matriz de decisión (Fixture 2030)

Grupo 16 · Ingeniería de Datos II

## RF1. Punto de partida

Se recupera el inventario, las prioridades y los supuestos del Hito 1: nueve tipos de datos agrupados en datos de referencia, datos que cambian rápido durante los partidos y datos ligados a la cantidad de usuarios conectados. Los números del proyecto son 2 a 3 millones de usuarios simultáneos y picos de más de 100.000 solicitudes por segundo.

No se vuelven a evaluar acá los nueve datos del Hito 1: este hito profundiza solo en los seis casos donde la elección de motor no era obvia o dependía de un trade-off. El resto (Selecciones, Estadios, Jugadores, Usuarios, Sesiones) sigue con el modelo ya definido en el Hito 1, sin cambios. La siguiente tabla deja explícito, para cada dato del Hito 1, dónde queda cubierto en este hito y si el motor elegido cambió respecto a la propuesta original:

| Dato (Hito 1) | Modelo en Hito 1 | Necesidad equivalente acá | Modelo acá | ¿Cambió? |
| :--- | :--- | :--- | :--- | :--- |
| Selecciones, Estadios, Jugadores | MongoDB | Partidos finalizados y datos estáticos | MongoDB | No. Se agrupan bajo la misma necesidad por compartir el mismo patrón de acceso (datos estables, de lectura). |
| Partidos | MongoDB (documento único con estado y eventos) | Se separa en dos necesidades: *Partidos y valores en tiempo real* y *Partidos finalizados y datos estáticos* | Redis (en vivo) + MongoDB (finalizado) | **Sí.** En el Hito 1 todavía no se distinguía el partido en vivo del partido ya jugado. Acá se separa porque el problema de latencia en vivo (Redis, en memoria) no es el mismo problema que guardar el resultado definitivo (MongoDB, en disco). |
| Estadísticas de grupos y partidos (ranking) | Redis (sorted set, sin bloqueos) | Grupos y puntajes | IRIS | **Sí.** Cambió el criterio que más pesa: en el Hito 1 se priorizó la velocidad de actualización sin bloqueos; acá se prioriza que todos los integrantes de un grupo vean el mismo puntaje y la misma posición (consistencia fuerte), que es lo que mejor resuelve IRIS. No es un error, es un cambio de prioridad que conviene dejar explícito porque antes se había argumentado exactamente lo contrario. |
| Grupos privados (alta de grupo) | MongoDB (documento por grupo) | Grupos y puntajes | IRIS | **Sí.** Se fusiona con la necesidad anterior: la composición del grupo y sus puntajes pasan a tratarse como un mismo problema de consistencia, en vez de dos problemas separados (alta masiva por un lado, ranking por otro). |
| Estadísticas de partido (posesión, pases, tiros momento a momento) | Cassandra (escritura masiva y sostenida) | Métricas y estadísticas históricas | InfluxDB | **Sí.** El propio Hito 1 ya había anotado a InfluxDB como alternativa seria para este mismo dato ("ambas opciones son técnicamente válidas"). Acá se retoma esa alternativa y se elige InfluxDB, mejor preparada para series temporales y agregaciones por período. |
| *(sin equivalente directo en el Hito 1)* | — | Logs generados durante el partido | Cassandra | Cassandra no desaparece: pasa a cubrir otro problema, el volumen de eventos/logs en crudo, que el Hito 1 no había separado de las estadísticas de partido. |
| *(sin equivalente en el Hito 1)* | — | Predicciones de usuarios | Neo4j | Es una necesidad nueva, no identificada como dato propio en el Hito 1: la relación usuario-partido-pronóstico. |

## RF2. Criterios de comparación

1. **Capacidad y volumen de datos.** ¿Puede manejar el volumen que necesita el módulo, tanto los registros constantes de los partidos como una gran cantidad de usuarios que entran de forma esporádica?
2. **Performance.** ¿Qué tan rápido resuelve la tarea? ¿Puede mostrar el estado actual de un partido de forma casi instantánea, informar rápido a los ganadores y actualizar el seguimiento minuto a minuto?
3. **Consistencia.** ¿En qué medida asegura que la información sea consistente? ¿Es verídico el estado del partido, coincide el puntaje de todas las personas de un mismo grupo, es consistente el ganador?
4. **Escalabilidad y almacenamiento.** ¿Cómo almacena y cuánto crece? ¿Es efectivo en costo, es adecuado para manejar los datos a nivel global?
5. **Capacidad de consulta y modelado.** ¿Permite formar las relaciones que facilitan el desarrollo y cómo se optimizan sus consultas?

## RF3. Ponderación

| Criterio | Peso |
| :--- | ---: |
| Capacidad y volumen | 20 % |
| Performance | 25 % |
| Consistencia | 20 % |
| Escalabilidad y almacenamiento | 20 % |
| Consulta y modelado | 15 % |
| **Total** | **100 %** |

## RF4. Modelos evaluados

Se evalúan **los seis modelos** trabajados en clase para **cada una de las seis necesidades** de datos priorizadas:

| Motor | Modelo |
| :--- | :--- |
| MongoDB | Documental |
| Neo4j | Grafos |
| Redis | Clave-valor |
| Cassandra | Columnar |
| IRIS | Multimodelo con almacenamiento transaccional |
| InfluxDB | Series temporales |

## RF5. Matriz de decisión

Cada motor recibe de 1 a 5 puntos por criterio (5 es lo mejor). El total ponderado es la suma de cada valoración multiplicada por el peso del criterio, dividida por 100, por lo que el máximo posible es 5,00. Los puntajes son una valoración del grupo y no una medición; sirven para ordenar las alternativas con un criterio común y dejar a la vista dónde la diferencia es grande y dónde es corta.

### 1) Logs generados durante el partido

| Motor | Capacidad y volumen (20 %) | Performance (25 %) | Consistencia (20 %) | Escalabilidad y almacenamiento (20 %) | Consulta y modelado (15 %) | Total ponderado |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
| Cassandra | 5 | 5 | 3 | 5 | 3 | **4,30** |
| MongoDB | 4 | 4 | 4 | 4 | 4 | **4,00** |
| Redis | 3 | 5 | 4 | 4 | 3 | **3,90** |
| IRIS | 3 | 4 | 4 | 3 | 5 | **3,75** |
| InfluxDB | 3 | 4 | 3 | 4 | 4 | **3,60** |
| Neo4j | 2 | 2 | 4 | 2 | 2 | **2,40** |

Mejor puntaje: **Cassandra** (4,30). Le sigue MongoDB (4,00), a 0.30 puntos.

### 2) Partidos y valores en tiempo real

| Motor | Capacidad y volumen (20 %) | Performance (25 %) | Consistencia (20 %) | Escalabilidad y almacenamiento (20 %) | Consulta y modelado (15 %) | Total ponderado |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
| MongoDB | 4 | 5 | 4 | 4 | 4 | **4,25** |
| Redis | 3 | 5 | 4 | 4 | 5 | **4,20** |
| Cassandra | 4 | 4 | 3 | 5 | 3 | **3,85** |
| IRIS | 4 | 4 | 4 | 4 | 3 | **3,85** |
| InfluxDB | 3 | 4 | 3 | 4 | 4 | **3,60** |
| Neo4j | 2 | 2 | 4 | 2 | 2 | **2,40** |

Mejor puntaje: **MongoDB** (4,25). Le sigue Redis (4,20), a 0.05 puntos.

### 3) Partidos finalizados y datos estáticos

| Motor | Capacidad y volumen (20 %) | Performance (25 %) | Consistencia (20 %) | Escalabilidad y almacenamiento (20 %) | Consulta y modelado (15 %) | Total ponderado |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
| IRIS | 4 | 4 | 5 | 4 | 4 | **4,20** |
| MongoDB | 4 | 4 | 4 | 4 | 5 | **4,15** |
| Cassandra | 5 | 4 | 3 | 5 | 2 | **3,90** |
| InfluxDB | 3 | 4 | 3 | 4 | 3 | **3,45** |
| Neo4j | 3 | 3 | 4 | 3 | 4 | **3,35** |
| Redis | 2 | 5 | 3 | 3 | 2 | **3,15** |

Mejor puntaje: **IRIS** (4,20). Le sigue MongoDB (4,15), a 0.05 puntos.

### 4) Grupos y puntajes

| Motor | Capacidad y volumen (20 %) | Performance (25 %) | Consistencia (20 %) | Escalabilidad y almacenamiento (20 %) | Consulta y modelado (15 %) | Total ponderado |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
| IRIS | 4 | 4 | 5 | 5 | 5 | **4,55** |
| MongoDB | 4 | 5 | 4 | 4 | 4 | **4,25** |
| Redis | 3 | 5 | 4 | 4 | 3 | **3,90** |
| Cassandra | 4 | 4 | 3 | 5 | 3 | **3,85** |
| InfluxDB | 3 | 4 | 3 | 4 | 4 | **3,60** |
| Neo4j | 2 | 2 | 4 | 2 | 2 | **2,40** |

Mejor puntaje: **IRIS** (4,55). Le sigue MongoDB (4,25), a 0.30 puntos.

### 5) Predicciones de usuarios

| Motor | Capacidad y volumen (20 %) | Performance (25 %) | Consistencia (20 %) | Escalabilidad y almacenamiento (20 %) | Consulta y modelado (15 %) | Total ponderado |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
| IRIS | 4 | 4 | 5 | 4 | 4 | **4,20** |
| MongoDB | 4 | 4 | 4 | 4 | 4 | **4,00** |
| Cassandra | 5 | 4 | 3 | 5 | 2 | **3,90** |
| Neo4j | 3 | 3 | 5 | 3 | 5 | **3,70** |
| InfluxDB | 3 | 4 | 3 | 4 | 3 | **3,45** |
| Redis | 2 | 5 | 3 | 3 | 2 | **3,15** |

Mejor puntaje: **IRIS** (4,20). Le sigue MongoDB (4,00), a 0.20 puntos.

### 6) Métricas y estadísticas históricas

| Motor | Capacidad y volumen (20 %) | Performance (25 %) | Consistencia (20 %) | Escalabilidad y almacenamiento (20 %) | Consulta y modelado (15 %) | Total ponderado |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
| InfluxDB | 4 | 5 | 3 | 4 | 4 | **4,05** |
| Cassandra | 5 | 4 | 3 | 5 | 2 | **3,90** |
| MongoDB | 4 | 3 | 4 | 4 | 4 | **3,75** |
| IRIS | 3 | 3 | 5 | 3 | 4 | **3,55** |
| Redis | 2 | 5 | 3 | 3 | 2 | **3,15** |
| Neo4j | 2 | 2 | 4 | 2 | 3 | **2,55** |

Mejor puntaje: **InfluxDB** (4,05). Le sigue Cassandra (3,90), a 0.15 puntos.

## RF6. Selección por necesidad

| Necesidad | Primero en la matriz | Modelo seleccionado | Alternativa considerada |
| :--- | :--- | :--- | :--- |
| Logs generados durante el partido | Cassandra (4,30) | **Cassandra** (4,30) | InfluxDB |
| Partidos y valores en tiempo real | MongoDB (4,25) | **Redis** (4,20) | MongoDB |
| Partidos finalizados y datos estáticos | IRIS (4,20) | **MongoDB** (4,15) | IRIS |
| Grupos y puntajes | IRIS (4,55) | **IRIS** (4,55) | MongoDB |
| Predicciones de usuarios | IRIS (4,20) | **Neo4j** (3,70) | MongoDB |
| Métricas y estadísticas históricas | InfluxDB (4,05) | **InfluxDB** (4,05) | Cassandra |

En tres necesidades el modelo seleccionado no es el primero de la matriz. Se aclara en cada caso:

- **Partidos y valores en tiempo real.** MongoDB (4,25) y Redis (4,20) quedan prácticamente empatados. Se elige Redis porque el requisito que más pesa en este dato es responder en menos de 100 ms con picos superiores a 100.000 solicitudes por segundo, y para eso MongoDB, que guarda en disco, tiene menos margen. Es una decisión por el criterio de Performance, el de mayor peso (25 %).
- **Partidos finalizados y datos estáticos.** IRIS (4,20) y MongoDB (4,15) también quedan casi empatados. Se elige MongoDB porque el dato ya no cambia y su estructura (equipos, estadio, resultado y eventos juntos) es la de un documento; la ventaja transaccional de IRIS no se aprovecharía acá y sumaría un motor más para operar.
- **Predicciones de usuarios.** Con estos pesos, la matriz favorece a IRIS (4,20) y a MongoDB (4,00) por encima de Neo4j (3,70). Neo4j se mantuvo en el Hito 2 porque la relación directa entre usuario, partido y pronóstico es lo que mejor se representa como grafo, y el criterio de Consulta y modelado pesa solo 15 %. Es la decisión menos respaldada por la matriz y queda marcada para revisarla cuando se implemente ese módulo.

## RF7. Justificación y costos aceptados

**Logs generados durante el partido → Cassandra.** Está orientada a escrituras intensivas, crece agregando nodos y mantiene la disponibilidad. Eso responde al flujo constante de registros que generan los partidos. Se acepta una consistencia que se puede configurar y un modelado pensado alrededor de las consultas, que limita las consultas improvisadas. InfluxDB conviene más para análisis puramente temporales, pero Cassandra admite registros con estructuras distintas.

**Partidos y valores en tiempo real → Redis.** Mantiene en memoria el estado vigente de los partidos, con la baja latencia que exigen los picos de más de 100.000 solicitudes por segundo y la respuesta en menos de 100 ms. Se acepta un mayor costo de memoria y el riesgo de perder datos si hay una falla antes de que queden guardados de forma definitiva. Cassandra ofrece más durabilidad pero no la misma velocidad para consultar el estado vigente.

**Partidos finalizados y datos estáticos → MongoDB.** Cada partido finalizado es un documento con equipos, estadio, resultado y eventos, sin consultas con múltiples uniones. El esquema flexible permite sumar atributos sin migraciones complejas. Se acepta cierta duplicación y desnormalización de datos. IRIS daría más control transaccional, pero ese control no es prioritario para información que cambia poco una vez validada.

**Grupos y puntajes → IRIS.** Sus garantías transaccionales aseguran que la composición de los grupos, los puntajes y las posiciones que ven los usuarios sean consistentes, y permite repartir la información entre regiones. Se acepta mayor complejidad operativa y sumar un motor especializado. Neo4j representaría bien las relaciones entre usuarios y grupos, pero el requisito principal es actualizar correctamente los puntajes, no recorrer relaciones complejas.

**Predicciones de usuarios → Neo4j.** Representa directamente la relación entre usuario, partido y pronóstico, y facilita consultas que recorren esas conexiones. El volumen es limitado: usuarios por partidos disponibles. Se acepta mantener un motor adicional y más complejidad de operación. MongoDB sería más simple si los pronósticos solo se consultaran por usuario o por partido; la conveniencia de Neo4j se valida con las consultas que se implementen.

**Métricas y estadísticas históricas → InfluxDB.** Está pensado para series temporales: guarda datos con marca de tiempo y permite agregarlos por período, como usuarios conectados, eventos por minuto o evolución de estadísticas durante los partidos. Se acepta que no sea adecuado para documentos generales ni para relaciones complejas. Cassandra soporta un volumen histórico parecido, pero exigiría más trabajo para las consultas y agregaciones temporales.

## RF8. Mapa de persistencia preliminar

| Necesidad del Fixture 2030 | Motor |
| :--- | :--- |
| Logs generados durante el partido | Cassandra |
| Partidos y valores en tiempo real | Redis |
| Partidos finalizados y datos estáticos | MongoDB |
| Grupos y puntajes | IRIS |
| Predicciones de usuarios | Neo4j |
| Métricas y estadísticas históricas | InfluxDB |

## RF9. Preguntas, riesgos y validaciones pendientes

- Definir cómo se consolidan y se guardan de forma definitiva los datos de un partido una vez finalizado, y qué pasa si ese paso falla.
- Hasta dónde escala Neo4j si la cantidad de usuarios supera cierto punto.
- Debatir los costos de operar seis motores distintos.
- Definir respaldos y alternativas en caso de ser necesarios.
- Decidir el límite de almacenamiento de los registros de los partidos.
- Definir cuestiones de seguridad: datos que necesiten cifrarse y privacidad.
- Revisar la elección de Neo4j para las predicciones, que la matriz no respalda por sí sola.
