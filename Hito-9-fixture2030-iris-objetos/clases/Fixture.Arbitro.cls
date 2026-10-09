Class Fixture.Arbitro Extends Fixture.Persona
{
    Property Licencia As %String(MAXLEN = 48) [ Required ];
    Property Rol As %String(MAXLEN = 32) [ Required ];

    Index idxLicencia On Licencia [ Unique ];
}
