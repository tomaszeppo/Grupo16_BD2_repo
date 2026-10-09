# Matriz de integridad y reglas de dominio

| Regla | Implementación | Prueba del módulo |
|---|---|---|
| Persona requiere nombre, nacionalidad y fecha de nacimiento | Propiedades `[Required]` de `Fixture.Persona` | `Fixture.Demo.Run()` persiste subclases y omite intencionalmente `Licencia` en un árbitro inválido |
| Jugador requiere código, dorsal y posición | Propiedades `[Required]`; índice único en `CodigoJugador` | Se crea un `Fixture.Jugador` persistente |
| Árbitro requiere licencia y rol | Propiedades `[Required]`; índice único en `Licencia` | Un árbitro sin `Licencia` debe fallar en `%Save()` |
| Partido requiere código, equipos, sede, fecha y estado | Propiedades `[Required]`; índice único en `Codigo` | Se crea y guarda un partido de demostración |
| Un partido tiene cero o muchos eventos; cada evento depende de un partido | Relaciones inversas `children` / `parent` | Se navega desde el partido al evento y del evento al partido |
| La consulta de eventos por partido no debe exigir un escaneo completo | `Fixture.Evento.idxPartido` | Inspección de definición + navegación por relación |
| Los cambios de estado siguen el flujo de negocio | `CambiarEstado()`: `Programado -> En juego -> Finalizado` | Se intenta una transición directa `Programado -> Finalizado` y debe rechazarse |
| Minutos de evento son de 1 a 130 y no se agregan eventos a un partido finalizado | `AgregarEvento()` encapsula la regla | Se intenta añadir un gol en minuto 0 a un partido finalizado y debe rechazarse |
| Un evento no debe quedar si falla el guardado del árbol | Un único `%Save()` del objeto raíz para padre e hijos | La salida muestra los IDs persistentes del partido y del evento tras guardar |
| El evento depende del ciclo de vida del partido | Relación parent-child de IRIS | El diseño documenta la dependencia y eliminación subordinada; no se elimina el fixture de demostración durante el flujo normal |

## Comportamiento ante eliminación

`Evento` es hijo dependiente de `Partido`, no una entidad independiente de negocio. El diseño usa relación parent-child (no un mero ID suelto); al eliminar el padre, IRIS aplica la semántica de ciclo de vida de la relación dependiente. Antes de una eliminación real del fixture, el procedimiento operativo debe confirmar que el partido se puede retirar y conservar evidencia si la política académica lo requiere.
