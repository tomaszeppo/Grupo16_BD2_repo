/// Tecnico (director tecnico) del Fixture 2030. Tercera extension de
/// Persona -- no era obligatoria (RF4 pide al menos dos), se agrega porque
/// completa el dominio de "personas" del partido sin costo extra de diseno.
Class Fixture2030.Tecnico Extends Fixture2030.Persona
{

Property EquipoCodigo As %String(MAXLEN = 10) [ Required ];

Property Formacion As %String(MAXLEN = 20);

}
