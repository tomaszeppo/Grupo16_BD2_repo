Class Fixture.Jugador Extends Fixture.Persona
{
    Property CodigoJugador As %String(MAXLEN = 32) [ Required ];
    Property NumeroCamiseta As %Integer [ Required ];
    Property Posicion As %String(MAXLEN = 32) [ Required ];

    Index idxCodigoJugador On CodigoJugador [ Unique ];
}
