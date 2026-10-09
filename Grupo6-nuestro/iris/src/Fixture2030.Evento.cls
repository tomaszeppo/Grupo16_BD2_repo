/// Evento deportivo (gol, tarjeta, cambio) del Fixture 2030. Lado "hijo"
/// (parent) de la relacion con Partido -- no existe por fuera de un
/// partido, y la consigna describe esta lista como inalterable: una vez
/// registrado, un evento no deberia reescribirse, solo agregarse.
Class Fixture2030.Evento Extends %Persistent
{

/// Cardinality=parent: este es el lado "muchos" de la relacion. IRIS
/// recorre los hijos de un Partido buscando quien le apunta por aca --
/// el indice de abajo es justo para que ese cruce no sea un escaneo
/// completo (RNF3).
Relationship Partido As Fixture2030.Partido [ Cardinality = parent, Inverse = Eventos ];

Index PartidoIndex On Partido;

Property Tipo As %String(VALUELIST = ",Gol,TarjetaAmarilla,TarjetaRoja,Cambio") [ Required ];

Property Minuto As %Integer(MINVAL = 0, MAXVAL = 130) [ Required ];

/// Codigo de jugador, mismo formato que usan Mongo/Neo4j (ej. "ARG-20").
Property JugadorCodigo As %String(MAXLEN = 15);

Property Descripcion As %String(MAXLEN = 200);

/// Validacion encapsulada (RF9): el ejemplo literal de la consigna --
/// no se puede registrar un evento en el minuto 0 de un partido que ya
/// esta Finalizado. %OnBeforeSave corre dentro de la clase, antes de
/// persistir, sin depender de nada externo a este archivo.
Method %OnBeforeSave(insert As %Boolean) As %Status
{
    If $IsObject(..Partido) && (..Partido.Estado = "Finalizado") && (..Minuto = 0) {
        Quit $$$ERROR($$$GeneralError, "No se puede registrar un evento en el minuto 0 de un partido ya finalizado.")
    }
    Quit $$$OK
}

}
