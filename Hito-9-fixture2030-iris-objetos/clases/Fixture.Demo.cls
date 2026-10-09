Class Fixture.Demo Extends %RegisteredObject
{
    ClassMethod Run()
    {
        Write "HITO 9 - DEMOSTRACION IRIS ORIENTADA A OBJETOS",!!

        Set sufijo = $Piece($Horolog,",",1) _ "-" _ $Piece($Horolog,",",2)
        Set codigo = "H9-M-" _ sufijo

        // 1) Herencia: Jugador comparte atributos con Persona y añade los propios.
        Set jugador = ##class(Fixture.Jugador).%New()
        Set jugador.Nombre = "Jugador de demostracion"
        Set jugador.Nacionalidad = "ARG"
        Set jugador.FechaNacimiento = $ZDateH("2002-04-12",3)
        Set jugador.CodigoJugador = "J-H9-" _ sufijo
        Set jugador.NumeroCamiseta = 9
        Set jugador.Posicion = "Delantero"
        Set scJugador = jugador.%Save()
        If $System.Status.IsError(scJugador) {
            Write "ERROR al guardar Jugador",!
            Do $System.Status.DisplayError(scJugador)
        } Else {
            Write "HERENCIA OK: Jugador persistido; ID=", jugador.%Id(),", nombre=",jugador.Nombre,", posicion=",jugador.Posicion,!!
        }

        // Crear una instancia válida de la segunda subclase de Persona.
        Set arbitro = ##class(Fixture.Arbitro).%New()
        Set arbitro.Nombre = "Arbitro de demostracion"
        Set arbitro.Nacionalidad = "ARG"
        Set arbitro.FechaNacimiento = $ZDateH("1980-01-01",3)
        Set arbitro.Licencia = "LIC-H9-" _ sufijo
        Set arbitro.Rol = "Principal"
        Set scArbitro = arbitro.%Save()
        If $System.Status.IsError(scArbitro) {
            Write "ERROR al guardar Arbitro",!
            Do $System.Status.DisplayError(scArbitro)
        } Else {
            Write "HERENCIA OK: Arbitro persistido; ID=",arbitro.%Id(),", licencia=",arbitro.Licencia,!!
        }

        // 2) Fallo controlado: se omite intencionalmente la propiedad Licencia [Required].
        Set arbitroInvalido = ##class(Fixture.Arbitro).%New()
        Set arbitroInvalido.Nombre = "Arbitro incompleto de prueba"
        Set arbitroInvalido.Nacionalidad = "ARG"
        Set arbitroInvalido.FechaNacimiento = $ZDateH("1985-01-01",3)
        Set arbitroInvalido.Rol = "Asistente"
        Set scInvalido = arbitroInvalido.%Save()
        If $System.Status.IsError(scInvalido) {
            Write "VALIDACION OK: IRIS rechazo Arbitro sin Licencia obligatoria.",!
            Do $System.Status.DisplayError(scInvalido)
        } Else {
            Write "ERROR DE PRUEBA: IRIS acepto un Arbitro sin Licencia; revisar la definicion.",!
        }
        Write !

        // 3) Crear padre y evento subordinado completamente en memoria.
        Set partido = ##class(Fixture.Partido).%New()
        Set partido.Codigo = codigo
        Set partido.EquipoLocal = "ARG"
        Set partido.EquipoVisitante = "FRA"
        Set partido.FechaHora = $ZDateTime($Horolog,3)
        Set partido.Sede = "Estadio Monumental"
        Set partido.Estado = "Programado"

        Set cambioIlegal = partido.CambiarEstado("Finalizado")
        If 'cambioIlegal {
            Write "VALIDACION OK: se rechazo Programado -> Finalizado sin pasar por En juego.",!
        } Else {
            Write "ERROR DE PRUEBA: se acepto una transicion de estado ilegal.",!
        }

        Set cambioValido = partido.CambiarEstado("En juego")
        If cambioValido {
            Write "Transicion valida: Programado -> En juego.",!
        } Else {
            Write "ERROR al cambiar partido a En juego.",!
        }

        Set eventoAgregado = partido.AgregarEvento("Gol",12,"Gol de demostracion","J-H9-" _ sufijo)
        If eventoAgregado {
            Write "Evento agregado a la relacion en memoria; todavia no se guardo por separado.",!
        } Else {
            Write "ERROR: no se pudo agregar el evento valido.",!
        }

        // RF6: un único guardado del objeto raíz persiste el árbol alcanzable.
        Set scPartido = partido.%Save()
        If $System.Status.IsError(scPartido) {
            Write "ERROR al guardar Partido y Evento",!
            Do $System.Status.DisplayError(scPartido)
            Quit
        }
        Set idPartido = partido.%Id()
        Set eventoMemoria = partido.Eventos.GetAt(1)
        Set idEvento = eventoMemoria.%Id()
        Write "GUARDADO ATOMICO OK: se invoco Partido.%Save() una sola vez para persistir el arbol inicial.",!
        Write "Partido ID=",idPartido," Codigo=",partido.Codigo," Estado=",partido.Estado,!
        Write "Evento ID=",idEvento," Tipo=",eventoMemoria.Tipo," Minuto=",eventoMemoria.Minuto,!!

        // 4) Navegación por referencias de objetos sin SQL.
        Set partidoLeido = ##class(Fixture.Partido).%OpenId(idPartido)
        If $IsObject(partidoLeido) {
            Set eventoLeido = partidoLeido.Eventos.GetAt(1)
            Write "NAVEGACION OBJETOS OK: ",partidoLeido.Codigo," -> ",eventoLeido.Tipo," minuto ",eventoLeido.Minuto,!
            Write "Relacion inversa: el evento referencia al partido ",eventoLeido.Partido.Codigo,!!
        } Else {
            Write "ERROR: no se pudo reabrir el partido por ID.",!!
        }

        // 5) Validación adicional: un partido finalizado no acepta un evento nuevo.
        Set cambioFinal = partido.CambiarEstado("Finalizado")
        If cambioFinal {
            Set scFinal = partido.%Save()
            If $System.Status.IsError(scFinal) Do $System.Status.DisplayError(scFinal)
            Set minutoCero = partido.AgregarEvento("Gol",0,"Esto debe ser rechazado", "J-H9-" _ sufijo)
            If 'minutoCero {
                Write "VALIDACION OK: partido Finalizado rechazo un evento en minuto 0.",!!
            } Else {
                Write "ERROR DE PRUEBA: se acepto evento ilegal en partido Finalizado.",!!
            }
        }

        // 6) Proyección SQL: consulta las mismas instancias almacenadas como objetos.
        Write "PROYECCION MULTIMODELO - SQL SOBRE Fixture.Partido",!
        Set stmt = ##class(%SQL.Statement).%New()
        Set sc = stmt.%Prepare("SELECT ID, Codigo, EquipoLocal, EquipoVisitante, Estado, Sede FROM Fixture.Partido WHERE Codigo = ?")
        If $System.Status.IsError(sc) {
            Do $System.Status.DisplayError(sc)
        } Else {
            Set rs = stmt.%Execute(codigo)
            While rs.%Next() {
                Write "SQL Partido: ID=",rs.%Get("ID")," Codigo=",rs.%Get("Codigo")," ",rs.%Get("EquipoLocal"),"-",rs.%Get("EquipoVisitante")," Estado=",rs.%Get("Estado")," Sede=",rs.%Get("Sede"),!
            }
        }

        Write "PROYECCION MULTIMODELO - SQL SOBRE Fixture.Evento",!
        Set stmtEvento = ##class(%SQL.Statement).%New()
        Set sc = stmtEvento.%Prepare("SELECT ID, Tipo, Minuto, Descripcion FROM Fixture.Evento WHERE ID = ?")
        If $System.Status.IsError(sc) {
            Do $System.Status.DisplayError(sc)
        } Else {
            Set rsEvento = stmtEvento.%Execute(idEvento)
            While rsEvento.%Next() {
                Write "SQL Evento: ID=",rsEvento.%Get("ID")," Tipo=",rsEvento.%Get("Tipo")," Minuto=",rsEvento.%Get("Minuto")," Descripcion=",rsEvento.%Get("Descripcion"),!
            }
        }

        Write !!,"FIN DEMOSTRACION HITO 9",!
        Write "Codigo de partido usado: ",codigo,!
        Write "Conserva este codigo para localizar la fila en SQL.",!!
    }
}
