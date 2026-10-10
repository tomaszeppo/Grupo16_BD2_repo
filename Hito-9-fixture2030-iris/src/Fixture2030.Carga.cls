/// Script de carga y demostracion. Se invoca desde el Terminal de IRIS
/// (ver README.md para los comandos exactos).
Class Fixture2030.Carga Extends %RegisteredObject
{

/// Borra todos los datos de demostracion para poder repetir las demos.
/// Los Evento viven anidados bajo su Partido, asi que se van con el.
ClassMethod Limpiar() As %Status
{
    Set tSC = ##class(Fixture2030.Partido).%KillExtent()
    If $$$ISERR(tSC) Quit tSC
    Quit ##class(Fixture2030.Persona).%KillExtent()
}

/// RF6: instancia un arbol padre-hijo (Partido + 2 Evento) y lo persiste
/// con UN solo %Save() del padre -- guardado atomico.
ClassMethod CargarMuestra() As %Status
{
    Set tSC = ..Limpiar()
    If $$$ISERR(tSC) Quit tSC

    Set tArbitro = ##class(Fixture2030.Arbitro).%New()
    Set tArbitro.Nombre = "Daniele Orsato"
    Set tArbitro.Nacionalidad = "Italia"
    Set tArbitro.Categoria = "FIFA"
    Set tArbitro.PaisOrigen = "Italia"
    Set tSC = tArbitro.%Save()
    If $$$ISERR(tSC) Quit tSC

    Set tPartido = ##class(Fixture2030.Partido).%New()
    Set tPartido.Codigo = "P-01"
    Set tPartido.Fecha = $ZDATETIME($HOROLOG, 3)
    Set tPartido.Fase = "Fase de grupos - Fecha 1"
    Set tPartido.EquipoLocal = "ARG"
    Set tPartido.EquipoVisitante = "URU"
    Set tPartido.Estado = "EnCurso"
    Set tPartido.ArbitroPrincipal = tArbitro

    // Los hijos se insertan en el padre, NO se guardan por separado.
    Set tGol = ##class(Fixture2030.Evento).%New()
    Set tGol.Tipo = "Gol"
    Set tGol.Minuto = 23
    Set tGol.JugadorCodigo = "ARG-20"
    Set tGol.Descripcion = "Gol de ARG-20"
    Do tPartido.Eventos.Insert(tGol)

    Set tTarjeta = ##class(Fixture2030.Evento).%New()
    Set tTarjeta.Tipo = "TarjetaAmarilla"
    Set tTarjeta.Minuto = 41
    Set tTarjeta.JugadorCodigo = "URU-05"
    Set tTarjeta.Descripcion = "Amarilla a URU-05"
    Do tPartido.Eventos.Insert(tTarjeta)

    // Un unico Save del padre persiste padre + los dos hijos insertados.
    Set tSC = tPartido.%Save()
    If $$$ISERR(tSC) Quit tSC

    Write "Carga completa. Partido ID interno: ", tPartido.%Id(), !
    Quit tSC
}

/// RF7: navega los objetos por referencia (OREF), sin usar SQL.
ClassMethod ConsultarPorObjetos(pCodigo As %String = "P-01") As %Status
{
    Set tPartido = ##class(Fixture2030.Partido).CodigoIndexOpen(pCodigo)
    If '$IsObject(tPartido) {
        Write "Partido no encontrado: ", pCodigo, !
        Quit $$$OK
    }
    Write "Partido ", tPartido.Codigo, " (", tPartido.EquipoLocal, " vs ", tPartido.EquipoVisitante, ") - ", tPartido.Estado, !
    If $IsObject(tPartido.ArbitroPrincipal) {
        Write "Arbitro: ", tPartido.ArbitroPrincipal.Nombre, !
    }
    Write "Eventos:", !
    Set tKey = ""
    For {
        Set tEvento = tPartido.Eventos.GetNext(.tKey)
        Quit:tKey=""
        Write "  - Minuto ", tEvento.Minuto, ": ", tEvento.Tipo, " (", tEvento.JugadorCodigo, ")", !
    }
    Quit $$$OK
}

/// RF9 demostrado: intenta guardar un evento invalido (minuto 0 en un
/// partido Finalizado) y confirma que la validacion lo rechaza.
ClassMethod DemostrarFalloValidacion() As %Status
{
    // Si ya existe un P-99 de una corrida anterior, se borra para repetir la demo
    If ##class(Fixture2030.Partido).CodigoIndexExists("P-99", .tId) {
        Set tSC = ##class(Fixture2030.Partido).%DeleteId(tId)
        If $$$ISERR(tSC) Quit tSC
    }
    Set tPartido = ##class(Fixture2030.Partido).%New()
    Set tPartido.Codigo = "P-99"
    Set tPartido.Fecha = $ZDATETIME($HOROLOG, 3)
    Set tPartido.EquipoLocal = "JPN"
    Set tPartido.EquipoVisitante = "COR"
    Set tPartido.Estado = "Finalizado"
    Set tSC = tPartido.%Save()
    If $$$ISERR(tSC) Quit tSC

    Set tEventoInvalido = ##class(Fixture2030.Evento).%New()
    Set tEventoInvalido.Partido = tPartido
    Set tEventoInvalido.Tipo = "Gol"
    Set tEventoInvalido.Minuto = 0
    Set tSC = tEventoInvalido.%Save()
    If $$$ISERR(tSC) {
        Write "Rechazado correctamente: ", $System.Status.GetErrorText(tSC), !
    } Else {
        Write "ERROR: se guardo un evento que deberia haber sido rechazado", !
    }
    Quit $$$OK
}

/// Carga fallida controlada: se omite a proposito Codigo (requerido).
ClassMethod DemostrarCargaFallida() As %Status
{
    Set tPartido = ##class(Fixture2030.Partido).%New()
    Set tPartido.EquipoLocal = "BRA"
    Set tPartido.EquipoVisitante = "COL"
    Set tPartido.Estado = "Programado"
    Set tSC = tPartido.%Save()
    If $$$ISERR(tSC) {
        Write "Rechazado correctamente (falta Codigo): ", $System.Status.GetErrorText(tSC), !
    } Else {
        Write "ERROR: se guardo un partido sin codigo", !
    }
    Quit $$$OK
}

}
