Class Fixture.Persona Extends %Persistent
{
    Property Nombre As %String(MAXLEN = 120) [ Required ];
    Property Nacionalidad As %String(MAXLEN = 3) [ Required ];
    Property FechaNacimiento As %Date [ Required ];

    Index idxNacionalidad On Nacionalidad;
}
