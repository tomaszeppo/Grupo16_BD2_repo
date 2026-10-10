/// Arbitro del Fixture 2030. Segunda extension de Persona (RF4).
Class Fixture2030.Arbitro Extends Fixture2030.Persona
{

Property Categoria As %String(VALUELIST = ",FIFA,Continental,Nacional") [ Required ];

Property PaisOrigen As %String(MAXLEN = 60);

}
