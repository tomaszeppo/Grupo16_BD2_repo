Class Fixture.Partido Extends %Persistent
{
    Property Codigo As %String(MAXLEN = 32) [ Required ];
    Property EquipoLocal As %String(MAXLEN = 3) [ Required ];
    Property EquipoVisitante As %String(MAXLEN = 3) [ Required ];
    Property FechaHora As %TimeStamp [ Required ];
    Property Sede As %String(MAXLEN = 120) [ Required ];
    Property Estado As %String(MAXLEN = 24) [ Required ];

    Relationship Eventos As Fixture.Evento [ Cardinality = children, Inverse = Partido ];

    Index idxCodigo On Codigo [ Unique ];

    /// Restringe el flujo permitido: Programado -> En juego -> Finalizado.
    Method CambiarEstado(nuevoEstado As %String) As %Boolean
    {
        If ..Estado = "Programado" {
            If nuevoEstado = "En juego" {
                Set ..Estado = nuevoEstado
                Quit 1
            }
            Quit 0
        }

        If ..Estado = "En juego" {
            If nuevoEstado = "Finalizado" {
                Set ..Estado = nuevoEstado
                Quit 1
            }
            If nuevoEstado = "En juego" {
                Quit 1
            }
            Quit 0
        }

        Quit 0
    }

    /// Agrega un evento al árbol en memoria. No guarda por sí solo;
    /// el llamador persiste el padre con una única llamada a %Save().
    Method AgregarEvento(tipo As %String, minuto As %Integer, descripcion As %String = "", jugadorCodigo As %String = "") As %Boolean
    {
        If ..Estado = "Finalizado" {
            Quit 0
        }
        If minuto < 1 {
            Quit 0
        }
        If minuto > 130 {
            Quit 0
        }
        If tipo = "" {
            Quit 0
        }

        Set evento = ##class(Fixture.Evento).%New()
        Set evento.Tipo = tipo
        Set evento.Minuto = minuto
        Set evento.Descripcion = descripcion
        Set evento.JugadorCodigo = jugadorCodigo
        Do ..Eventos.Insert(evento)
        Quit 1
    }
}
