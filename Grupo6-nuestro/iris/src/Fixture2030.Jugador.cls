/// Jugador del Fixture 2030. Extiende Persona (RF4). El codigo de equipo es
/// el mismo identificador que ya usan los modulos de Mongo, Neo4j, Cassandra
/// y Redis -- no hay una clase Equipo propia en este hito, se referencia por
/// codigo para no duplicar ese dominio, que ya vive en otro modulo.
Class Fixture2030.Jugador Extends Fixture2030.Persona
{

Property Dorsal As %Integer(MAXVAL = 26, MINVAL = 1) [ Required ];

Property Posicion As %String(VALUELIST = ",Arquero,Defensor,Mediocampista,Delantero") [ Required ];

Property EquipoCodigo As %String(MAXLEN = 10) [ Required ];

Index EquipoIndex On EquipoCodigo;

}
