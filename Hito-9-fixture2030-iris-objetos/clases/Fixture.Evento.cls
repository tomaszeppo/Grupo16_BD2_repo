Class Fixture.Evento Extends %Persistent
{
    Property Tipo As %String(MAXLEN = 32) [ Required ];
    Property Minuto As %Integer [ Required ];
    Property Descripcion As %String(MAXLEN = 240);
    Property JugadorCodigo As %String(MAXLEN = 32);

    Relationship Partido As Fixture.Partido [ Cardinality = parent, Inverse = Eventos, Required ];

    // Índice explícito en el extremo hijo para ubicar eventos por partido.
    Index idxPartido On Partido;
}
