/// Partido del Fixture 2030. Lado "padre" de la relacion estructural con
/// Evento (RF3): un partido tiene su lista subordinada de eventos, que no
/// tiene sentido ni identidad fuera de ese partido -- es composicion, no
/// una simple referencia.
Class Fixture2030.Partido Extends %Persistent
{

/// Mismo codigo que usan Mongo, Neo4j y Cassandra para el mismo partido
/// (ej. "P-01"), para mantener trazabilidad de identificadores entre
/// modulos sin ninguna conexion tecnica real entre ellos.
Property Codigo As %String(MAXLEN = 10) [ Required ];

Index CodigoIndex On Codigo [ Unique ];

Property Fecha As %TimeStamp [ Required ];

Property Fase As %String(MAXLEN = 60);

Property EquipoLocal As %String(MAXLEN = 10) [ Required ];

Property EquipoVisitante As %String(MAXLEN = 10) [ Required ];

Property GolesLocal As %Integer [ InitialExpression = 0 ];

Property GolesVisitante As %Integer [ InitialExpression = 0 ];

/// Estado del partido -- la maquina de estado que menciona la consigna.
/// Es un dato (una propiedad que cambia), no una jerarquia de clases: ver
/// la nota sobre herencia vs. estados variables en Persona.cls.
Property Estado As %String(VALUELIST = ",Programado,EnCurso,Finalizado") [ Required ];

/// Referencia simple (no relacion formal bidireccional) al arbitro
/// principal. Se deja como referencia de objeto comun para no diluir con
/// una segunda relacion formal la que realmente se evalua en este hito
/// (Partido-Evento, abajo).
Property ArbitroPrincipal As Fixture2030.Arbitro;

/// La relacion estructural padre-hijo del hito (RF3). Cardinality=children
/// del lado del padre; ver el Inverse en Evento.cls para el lado "parent".
/// Un unico %Save() de Partido persiste a Partido y a todos los Evento que
/// se le hayan insertado (RF6).
Relationship Eventos As Fixture2030.Evento [ Cardinality = children, Inverse = Partido ];

}
