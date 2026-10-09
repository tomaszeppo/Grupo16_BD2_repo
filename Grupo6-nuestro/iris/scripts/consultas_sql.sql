-- consultas_sql.sql
-- RF8: los mismos objetos cargados con Fixture2030.Carga.CargarMuestra()
-- tienen que verse igual via SQL relacional clasico (proyeccion multimodelo).
-- Correr desde el Management Portal (System Explorer > SQL) o desde un
-- cliente ODBC/JDBC apuntando al puerto 1972.

-- Tabla proyectada de Partido
SELECT Codigo, EquipoLocal, EquipoVisitante, Estado, GolesLocal, GolesVisitante
FROM Fixture2030.Partido;

-- Tabla proyectada de Evento, navegando la relacion con la sintaxis de
-- flecha de IRIS SQL (Partido->Codigo sigue la referencia sin un JOIN
-- explicito)
SELECT Partido->Codigo AS PartidoCodigo, Tipo, Minuto, JugadorCodigo
FROM Fixture2030.Evento
ORDER BY PartidoCodigo, Minuto;

-- Lo mismo con un JOIN explicito, para quien prefiera esa sintaxis
SELECT p.Codigo, p.EquipoLocal, p.EquipoVisitante, e.Minuto, e.Tipo, e.JugadorCodigo
FROM Fixture2030.Partido AS p
JOIN Fixture2030.Evento AS e ON e.Partido = p.ID
ORDER BY p.Codigo, e.Minuto;

-- Confirmar que la herencia tambien se proyecta: Jugador, Arbitro y
-- Tecnico son tablas propias (cada una con sus columnas heredadas de
-- Persona mas las propias)
SELECT Nombre, Categoria, PaisOrigen FROM Fixture2030.Arbitro;
