# Diagrama de objetos — Entidades complejas (Hito 9)

## Jerarquía de herencia (RF4)

```
Fixture2030.Persona (%Persistent)
├── Nombre* : %String
├── Nacionalidad : %String
├── FechaNacimiento : %Date
│
├── Fixture2030.Jugador
│   ├── Dorsal* : %Integer (1-26)
│   ├── Posicion* : %String (Arquero/Defensor/Mediocampista/Delantero)
│   └── EquipoCodigo* : %String
│
├── Fixture2030.Arbitro
│   ├── Categoria* : %String (FIFA/Continental/Nacional)
│   └── PaisOrigen : %String
│
└── Fixture2030.Tecnico
    ├── EquipoCodigo* : %String
    └── Formacion : %String
```
`*` = propiedad obligatoria (`[Required]`).

Las tres subclases SON personas con atributos propios de su rol — no representan un estado que cambia (ver la nota en `Persona.cls` sobre por qué un jugador lesionado no es una subclase).

## Relación estructural (RF3)

```
Fixture2030.Partido (%Persistent)                Fixture2030.Evento (%Persistent)
├── Codigo* : %String (índice único)              ├── Partido* : Relationship [parent]
├── Fecha* : %TimeStamp                            │   (índice sobre esta propiedad, RNF3)
├── Fase : %String                                 ├── Tipo* : %String (Gol/TarjetaAmarilla/
├── EquipoLocal* : %String                         │   TarjetaRoja/Cambio)
├── EquipoVisitante* : %String                      ├── Minuto* : %Integer (0-130)
├── GolesLocal / GolesVisitante : %Integer          ├── JugadorCodigo : %String
├── Estado* : %String (Programado/EnCurso/          └── Descripcion : %String
│   Finalizado)
├── ArbitroPrincipal : Fixture2030.Arbitro
│   (referencia simple, no relación formal)
└── Eventos : Relationship [children] ◄────────────► Partido : Relationship [parent]
                                                        Inverse = Eventos
```

**Por qué es `parent`/`children` y no una simple referencia:** un evento no tiene identidad ni sentido fuera del partido que lo contiene — es composición, no asociación. La consigna lo describe como "lista subordinada de eventos inalterables", que es exactamente lo que el patrón `parent`/`children` de IRIS modela: los hijos se guardan y se cargan junto con el padre, no por separado.

**`ArbitroPrincipal` queda como referencia simple**, no como una segunda `Relationship` formal, a propósito: el hito pide declarar una relación estructural sólida — ya está cubierta por Partido-Evento, y agregar una segunda relación bidireccional completa (Arbitro ↔ Partido) solo para sumar complejidad diluiría cuál es la que realmente se está evaluando.
