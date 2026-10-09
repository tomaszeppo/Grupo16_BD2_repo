# Diagrama del dominio de objetos

```text
                      +--------------------------+
                      |      Fixture.Persona     |  <<%Persistent>>
                      |--------------------------|
                      | Nombre: %String          |
                      | Nacionalidad: %String    |
                      | FechaNacimiento: %Date   |
                      +------------+-------------+
                                   ^
                  +----------------+----------------+
                  |                |                |
        +---------+------+ +-------+--------+ +------+----------------+
        | Fixture.Jugador | | Fixture.Arbitro| | Fixture.Tecnico      |
        |----------------| |----------------| |----------------------|
        | CodigoJugador  | | Licencia       | | Especialidad         |
        | NumeroCamiseta | | Rol            | | AniosExperiencia     |
        | Posicion       | |                | |                      |
        +----------------+ +----------------+ +----------------------+

+---------------------------+      children / parent      +--------------------------+
|       Fixture.Partido     | 1 ---------------------- *  |       Fixture.Evento      |
|---------------------------|                              |--------------------------|
| Codigo [Required, Unique] |                              | Tipo [Required]          |
| EquipoLocal [Required]    |                              | Minuto [Required]        |
| EquipoVisitante [Required]|                              | Descripcion              |
| FechaHora [Required]      |                              | JugadorCodigo             |
| Estado [Required]         |                              | Partido [Required, Index] |
| Sede [Required]           |                              +--------------------------+
| Eventos: children         |
| CambiarEstado()           |
| AgregarEvento()           |
+---------------------------+
```

## Ciclo de vida y decisiones

- `Persona` es la clase persistente base. `Jugador`, `Arbitro` y `Tecnico` heredan la identidad y las propiedades comunes; la herencia representa tipos estables, no estados como lesionado o suspendido.
- `Partido` y `Evento` usan una relación formal padre-hijo y bidireccional (`Partido.Eventos` / `Evento.Partido`). El evento depende del partido.
- `Fixture.Evento.idxPartido` indexa la relación en el extremo hijo.
- `Partido.%Save()` persiste el árbol alcanzable de objetos relacionados dentro de una misma transacción de guardado. La demo no invoca `%Save()` sobre el evento por separado.
- El código de equipos se mantiene como referencia lógica (`ARG`, `FRA`), consistente con el identificador reutilizado por los hitos previos; IRIS no duplica el catálogo de selecciones.
