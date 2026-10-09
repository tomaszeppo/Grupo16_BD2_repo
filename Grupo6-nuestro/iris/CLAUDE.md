# Fixture 2030 — Hito 9 (entidades complejas en InterSystems IRIS)

Contexto para retomar este proyecto en Claude Code. Viene de una conversación
larga en claude.ai donde se diseñó todo esto **sin acceso a Docker ni a una
instancia de IRIS real** — a diferencia del Hito 7 (Redis), donde sí se pudo
simular la lógica con una herramienta en memoria (`fakeredis`), acá no existe
un equivalente para ObjectScript/IRIS. Nada de este código se compiló ni se
ejecutó todavía contra un servidor real.

## Qué es esto

TP de Ingeniería de Datos II, Grupo 6, caso de estudio "Fixture 2030". Este
es el Hito 9: modelo orientado a objetos sobre InterSystems IRIS (Partido,
Evento, Persona/Jugador/Arbitro/Tecnico). La consigna completa debería
estar como PDF en el repositorio; si no está, pedirla.

## Tarea principal: validar contra IRIS real

1. Levantar el ambiente: `docker compose up -d` (requiere que exista
   `~/docker/data/iris` en el host — el usuario trabaja en Windows, ver
   README para la nota de WSL2).
2. Entrar a la terminal (`docker exec -it fixture2030-iris iris session iris`,
   ajustar el nombre de instancia si `iris list` muestra otro) y compilar
   todo `src/` con `Do $System.OBJ.ImportDir("/opt/src", "*.cls", "ck", .errors, 1)`.
   **Esto es lo más probable que necesite ajustes** — la sintaxis de
   ObjectScript se escribió con cuidado pero sin poder compilarla nunca,
   así que cualquier error de compilación hay que resolverlo ahí, no
   descartar el diseño por eso.
3. Correr en orden: `CargarMuestra()`, `ConsultarPorObjetos("P-01")`,
   `DemostrarFalloValidacion()`, `DemostrarCargaFallida()` (los cuatro
   métodos de `Fixture2030.Carga`), confirmando que cada uno hace lo que
   dice su nombre.
4. Correr las consultas de `scripts/consultas_sql.sql` desde el
   Management Portal y confirmar que los mismos datos se ven en SQL
   (RF8, proyección multimodelo).
5. Sacar las capturas de `docs/evidencia/CAPTURAS_PENDIENTES.md` y
   guardarlas ahí, reemplazando ese archivo de texto.

## Decisiones de diseño (ya cerradas, no re-discutir salvo que no compilen)

- Jerarquía de herencia: `Persona` (base) → `Jugador`, `Arbitro`, `Tecnico`.
  Representan tipos inmutables, no estados — ningún estado variable de un
  jugador (lesionado, suspendido) se modela como subclase.
- Relación estructural (RF3): `Partido` (padre, `Cardinality=children`) ↔
  `Evento` (hijo, `Cardinality=parent`), con `Inverse` cruzado en los dos
  lados. `Evento.Partido` tiene un índice (`PartidoIndex`) para evitar el
  escaneo completo que advierte RNF3.
- `ArbitroPrincipal` en `Partido` es una referencia simple, a propósito —
  no se promovió a una segunda `Relationship` formal para no diluir cuál
  es la relación que se está evaluando.
- Validación (RF9): `Evento.%OnBeforeSave()` rechaza un evento en minuto 0
  si el partido ya está `Finalizado` — es el ejemplo literal de la
  consigna, no una regla de negocio completa (ver límite documentado en
  `docs/matriz_integridad.md`).
- Los códigos de equipo, jugador y partido (`ARG`, `ARG-20`, `P-01`) son
  los mismos que usan los demás módulos del TP, sin ninguna conexión
  técnica real entre las bases.

## Preferencias del usuario para este proyecto

- Redacción natural y suelta en toda la documentación, como si la hubiera
  escrito el propio grupo — evitar anglicismos y jerga tipo "trade-off",
  "ad-hoc", "stack"; evitar tono genérico de IA.
- Prefiere validar con evidencia real antes de dar algo por entregado.
- Antes de la entrega final, este `CLAUDE.md` (y cualquier carpeta
  `.claude/` de la sesión de trabajo) se borra — no son parte de lo que se
  entrega al profesor. Los hitos anteriores (4, 5, 6, 7) siguieron ese
  mismo patrón.
- Este hito además pide específicamente un repositorio GitHub con
  historial de commits (RNF5) — no es solo un zip como los anteriores.
  Confirmar con el usuario si ya tiene el repo creado antes de asumir nada
  sobre `git init`/`git remote`.
