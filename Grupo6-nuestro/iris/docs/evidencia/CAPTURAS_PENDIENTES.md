Guardar en esta carpeta las capturas de pantalla o salidas de consola de:

1. `docker compose up -d` corriendo sin errores, y `docker ps` mostrando el
   contenedor `fixture2030-iris` con la imagen `intersystems/iris-community`.
2. Resultado de `Do $System.OBJ.ImportDir(...)` compilando las 7 clases sin
   errores (RNF2 -- deben compilar sin dependencias sintacticas no
   declaradas).
3. Resultado de `Do ##class(Fixture2030.Carga).CargarMuestra()` -- el
   Partido ID impreso al final.
4. Resultado de `Do ##class(Fixture2030.Carga).ConsultarPorObjetos()` --
   mostrando el partido, el arbitro y los dos eventos navegados por
   referencia (RF7).
5. Resultado de `Do ##class(Fixture2030.Carga).DemostrarFalloValidacion()`
   -- confirmando el rechazo del evento en minuto 0 (RF9).
6. Resultado de `Do ##class(Fixture2030.Carga).DemostrarCargaFallida()` --
   confirmando el rechazo por falta de Codigo (RF5).
7. Resultado de las consultas de `scripts/consultas_sql.sql` desde el
   Management Portal (System Explorer > SQL), mostrando que los mismos
   datos se ven en tablas relacionales (RF8).
8. Captura del arbol de clases compiladas en el Management Portal
   (System Explorer > Classes), mostrando la jerarquia de Persona y la
   relacion Partido-Evento.

Se puede borrar este archivo de texto una vez que las capturas esten cargadas.
