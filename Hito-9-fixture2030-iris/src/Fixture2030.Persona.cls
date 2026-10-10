/// Clase base de herencia (RF4). Representa el tipo inmutable "persona
/// vinculada al Fixture 2030" -- no un estado variable. Jugador, Arbitro y
/// Tecnico extienden esta clase porque estructuralmente SON personas con
/// datos adicionales segun su rol; ninguno de sus estados (lesionado,
/// suspendido, etc.) se modela como subclase, como advierte la consigna.
Class Fixture2030.Persona Extends %Persistent
{

/// Nombre completo. Obligatorio en toda la jerarquia.
Property Nombre As %String(MAXLEN = 100) [ Required ];

Property Nacionalidad As %String(MAXLEN = 60);

Property FechaNacimiento As %Date;

}
