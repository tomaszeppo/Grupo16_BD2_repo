#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! docker compose ps --status running --services | grep -qx iris; then
  echo "ERROR: IRIS no está activo. Ejecutá bash scripts/01_inicializar.sh primero." >&2
  exit 1
fi

docker exec -i fixture2030-iris iris session IRIS <<'IRISCMDS'
Write !!,"=================================================",!
Write "PRUEBA RF6 / RF7 - ARBOL DE OBJETOS Y NAVEGACION",!
Write "=================================================",!!

Set sufijo = $Piece($Horolog,",")_"-"_$Piece($Horolog,",",2)
Set codigo = "H9-ARB-"_sufijo
Set partido = ##class(Fixture.Partido).%New()
Set partido.Codigo = codigo
Set partido.EquipoLocal = "ARG"
Set partido.EquipoVisitante = "FRA"
Set partido.FechaHora = $ZDateTime($Horolog,3)
Set partido.Sede = "Estadio Monumental"
Set partido.Estado = "Programado"

Set evento = ##class(Fixture.Evento).%New()
Set evento.Tipo = "Gol"
Set evento.Minuto = 17
Set evento.Descripcion = "Prueba de guardado padre-hijo"
Set evento.JugadorCodigo = "J-H9-ARB"
Do partido.Eventos.Insert(evento)

Write "Antes de guardar: Partido Codigo=",partido.Codigo,!
Write "Antes de guardar: Evento Tipo=",evento.Tipo," Minuto=",evento.Minuto,!
Write "Operacion de persistencia: una unica llamada a partido.%Save() sobre el padre.",!
Set sc = partido.%Save()
Write "Error al guardar (0 significa que no hay error): ",$System.Status.IsError(sc),!
If $System.Status.IsError(sc) Do $System.Status.DisplayError(sc)

Set idPartido = partido.%Id()
Set eventoGuardado = partido.Eventos.GetAt(1)
Set idEvento = eventoGuardado.%Id()
Write "ID Partido=",idPartido," | Codigo=",partido.Codigo,!
Write "ID Evento=",idEvento," | Tipo=",eventoGuardado.Tipo," | Minuto=",eventoGuardado.Minuto,!!

Set partidoLeido = ##class(Fixture.Partido).%OpenId(idPartido)
Set eventoLeido = partidoLeido.Eventos.GetAt(1)
Write "NAVEGACION PADRE -> HIJO: ",partidoLeido.Codigo," -> ",eventoLeido.Tipo," minuto ",eventoLeido.Minuto,!
Write "NAVEGACION INVERSA HIJO -> PADRE: ",eventoLeido.Partido.Codigo,!
Write "RESULTADO: RF6 y RF7 demostrados mediante objetos, sin SQL para navegar.",!!
Halt
IRISCMDS
