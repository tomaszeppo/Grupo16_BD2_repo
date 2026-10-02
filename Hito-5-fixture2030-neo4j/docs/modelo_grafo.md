# Modelo de grafo — Fixture 2030

## 1. Objetivo

El subgrafo representa entidades deportivas, de programación y de participación de usuarios del Fixture 2030 que se benefician de ser recorridas como relaciones.

El modelo conserva la estructura deportiva definida en los hitos anteriores y agrega usuarios, grupos y predicciones. La conexión entre ambos sectores se realiza mediante el nodo `Partido`, ya que cada predicción corresponde a un encuentro concreto.

Esto permite recorrer desde una persona hasta su grupo, sus predicciones y el partido asociado, y desde allí continuar hacia los equipos participantes, jugadores, estadio y eventos ocurridos durante el encuentro.

## 2. Etiquetas de nodos

### Equipo

Propiedades principales:

- `codigo`: identificador único de tres caracteres heredado del Hito 4.
- `nombre`: nombre del equipo.

### Jugador

Propiedades principales:

- `id`: identificador lógico único generado para Neo4j, porque los registros del Hito 4 no tenían un ID propio.
- `nombre`
- `apellido`
- `dorsal`
- `posicion`

La referencia al equipo no se mantiene como una propiedad de texto para el modelo de grafo; se representa mediante `PERTENECE_A`.

### Partido

Propiedades:

- `id`: identificador único.
- `fecha`
- `fase`

Los equipos participantes, la sede, los eventos y las predicciones asociadas al partido se representan mediante relaciones y no como propiedades duplicadas dentro del nodo.

### Estadio

Propiedades:

- `id`: identificador único.
- `nombre`
- `ciudad`

### Evento

Propiedades:

- `id`: identificador único.
- `tipo`
- `minuto`

Permite registrar qué ocurrió durante el partido y en qué momento del encuentro.

### Usuario

Propiedades principales:

- `idUsuario`: identificador único.
- `nombre`
- `origen`
- `email`
- `fechaRegistro`
- `activo`

### Grupo

Propiedades principales:

- `idGrupo`: identificador único.
- `nombreGrupo`
- `fechaCreacion`

### Prediccion

Propiedades principales:

- `idPrediccion`: identificador único.
- `paisGanador`
- `paisPerdedor`
- `golesPG`
- `golesPP`

La predicción no almacena el partido como un dato de texto, sino que se vincula con el nodo `Partido` mediante la relación `SOBRE`.

## 3. Relaciones

### `(:Jugador)-[:PERTENECE_A]->(:Equipo)`

Representa la pertenencia de un jugador a un equipo.

Cardinalidad esperada: un jugador pertenece a un equipo; un equipo puede tener muchos jugadores.

### `(:Equipo)-[:PARTICIPA_EN]->(:Partido)`

Representa la participación de un equipo en un partido.

En el modelo de prueba cada partido tiene dos equipos participantes.

### `(:Partido)-[:SE_JUEGA_EN]->(:Estadio)`

Representa la sede donde se disputa el partido.

Cada partido de la carga tiene una sede.

### `(:Evento)-[:OCURRE_EN]->(:Partido)`

Representa que un evento deportivo ocurre durante un partido.

La propiedad `minuto` del evento permite analizar lo sucedido durante el desarrollo del encuentro.

### `(:Usuario)-[:PERTENECE_A]->(:Grupo)`

Representa la pertenencia de una persona a un grupo.

La relación puede incluir la propiedad `fechaIngreso` para registrar desde cuándo forma parte del grupo.

### `(:Usuario)-[:REALIZA]->(:Prediccion)`

Representa qué predicciones fueron realizadas por cada usuario.

La relación puede incluir la propiedad `fechaPrediccion`, permitiendo conocer cuándo fue realizada y analizarla en relación con el desarrollo del partido.

### `(:Prediccion)-[:SOBRE]->(:Partido)`

Vincula cada predicción con el partido correspondiente.

Esta relación funciona como punto de conexión entre el subgrafo de usuarios y el subgrafo deportivo, permitiendo comparar lo pronosticado con los equipos, eventos y demás información del encuentro.

## 4. Recorridos principales

El modelo permite recorrer:

`Jugador → Equipo → Partido → Estadio`

`Evento → Partido ← Equipo`

`Grupo ← Usuario → Prediccion → Partido`

`Usuario → Prediccion → Partido ← Equipo ← Jugador`

`Usuario → Prediccion → Partido ← Evento`

Estos recorridos permiten responder preguntas relacionales sin tener que buscar entidades aisladas.

Por ejemplo, se puede conocer qué predicciones realizó una persona, qué usuarios de un grupo predijeron un determinado partido, qué equipos participaron en ese encuentro, qué jugadores pertenecían a esos equipos y qué eventos ocurrieron durante el partido.

La combinación de `fechaPrediccion` con los eventos del partido permite además analizar la predicción dentro del contexto temporal del encuentro.

## 5. Identidad e integridad

Se definieron restricciones de unicidad para:

- `Equipo.codigo`
- `Jugador.id`
- `Partido.id`
- `Estadio.id`
- `Evento.id`
- `Usuario.idUsuario`
- `Grupo.idGrupo`
- `Prediccion.idPrediccion`

Los equipos conservan el mismo `codigo` utilizado en MongoDB, permitiendo reconocer la misma entidad entre los distintos módulos de la arquitectura.

Para los jugadores se utiliza un identificador lógico estable con el formato:

`J-<codigo>-<numero>`

Las cargas utilizan `MERGE` para evitar duplicaciones cuando el proceso se ejecuta nuevamente y para vincular nuevas entidades con nodos ya existentes, por ejemplo una predicción con un partido previamente cargado.

## 6. Datos cargados

La carga parte de los datos del Hito 4 y contiene:

- 64 equipos.
- 1064 jugadores: 1000 provenientes del Hito 4 y 64 jugadores de prueba adicionales.
- 32 partidos de prueba.
- 10 estadios de prueba.
- 96 eventos de prueba.

Los partidos, estadios y eventos son datos de prueba generados para validar los recorridos requeridos por el Hito 5.

Sobre esta base se incorporan también usuarios, grupos y predicciones de prueba para validar los nuevos recorridos del modelo, principalmente:

`Grupo ← Usuario → Prediccion → Partido`

y:

`Usuario → Prediccion → Partido → información deportiva`

Estas incorporaciones permiten analizar en conjunto la participación de los usuarios y el contexto deportivo de cada predicción.
