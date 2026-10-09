# Matriz de integridad — Entidades complejas (Hito 9)

## ¿Qué pasa con los eventos si se borra un partido?

Con una relación `parent`/`children`, IRIS borra en cascada: eliminar un `Partido` elimina automáticamente todos sus `Evento` asociados — no quedan eventos huérfanos apuntando a un padre que ya no existe. Es la integridad referencial bidireccional que pide RF3: no se puede borrar el padre y dejar hijos sueltos, ni crear un hijo sin padre válido (la propiedad `Partido` de `Evento` es parte de la relación formal, no un campo libre).

Esto es consistente con cómo se trató la misma pregunta en Cassandra (Hito 6): ahí la "eliminación controlada" exige borrar por clave completa y advierte contra un `DELETE` sin filtro. Acá el equivalente es no poder crear un `Evento` sin un `Partido` real detrás — la base lo impide estructuralmente, no hace falta disciplina del lado de la aplicación.

## ¿Qué pasa si se intenta guardar un objeto con un campo requerido faltante?

El `%Save()` falla y devuelve un `%Status` de error (`DemostrarCargaFallida()` en `Carga.cls` lo prueba a propósito, omitiendo `Codigo` en un `Partido`). No se persiste nada — ni el padre ni los hijos que se le hubieran insertado, porque el guardado es atómico: si el padre falla, los hijos tampoco quedan grabados.

## ¿Qué pasa si se intenta una transición de estado ilegal?

`Evento.%OnBeforeSave()` corre antes de persistir, dentro de la propia clase (RF9). El caso implementado es el literal de la consigna: un evento en el minuto 0 de un partido ya `Finalizado` se rechaza con un error explícito, sin llegar a tocar el almacenamiento.

**Lo que esta validación puntual NO cubre** (documentado como límite conocido, no como olvido): cualquier evento nuevo en un partido `Finalizado` — minuto 1, 45, el que sea — todavía se puede guardar. La consigna pide exactamente el caso de minuto 0 como ejemplo de "transición ilegal", así que es lo que se implementó; una regla de negocio más completa ("no se agregan eventos a un partido finalizado, salvo corrección explícita") quedaría para un hito posterior si hiciera falta.

## ¿Qué pasa con la referencia a Árbitro si se borra el árbitro?

`ArbitroPrincipal` es una referencia simple, no una relación formal — IRIS no la borra en cascada ni la protege de quedar colgando. Si se necesitara esa garantía, habría que promoverla a una `Relationship` formal como la de Partido-Evento, con su propio costo de modelado (ver `diagrama_objetos.md`). Queda como limitación conocida de este hito.
