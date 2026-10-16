"""El driver de IRIS devuelve DataRow ligados al cursor: se invalidan al ejecutar otra consulta con el mismo cursor."""
from app.adapters.iris import IrisAdapter
from app.config.settings import Settings


class FilaLigada:
    def __init__(self, cursor, valores):
        self._cursor, self._gen, self._valores = cursor, cursor.generacion, valores

    def __getitem__(self, i):
        if self._gen != self._cursor.generacion:
            raise RuntimeError("Cursor closed; DataRow is inaccessible")
        return self._valores[i]

    def __iter__(self):
        for i in range(len(self._valores)):
            yield self[i]


class CursorFalso:
    def __init__(self):
        self.generacion = 0
        self._resultado = []

    def execute(self, sql, params):
        self.generacion += 1
        if "Fixture.Partido" in sql:
            self._resultado = [FilaLigada(self, (1, "P-01", "ARG", "BRA", "2030-06-15 18:30:00", "Estadio", "En juego"))]
        else:
            self._resultado = [FilaLigada(self, ("Gol", 32, None, "J-ARG-01"))]

    def fetchone(self):
        return self._resultado[0] if self._resultado else None

    def fetchall(self):
        return list(self._resultado)


class ConexionFalsa:
    def __init__(self):
        self._cursor = CursorFalso()

    def cursor(self):
        return self._cursor


def test_obtener_partido_copia_la_fila_antes_de_consultar_los_eventos():
    adaptador = IrisAdapter(Settings(_env_file=None))
    adaptador._conexion = ConexionFalsa()
    partido = adaptador.obtener_partido("P-01")
    assert partido["codigo"] == "P-01" and partido["estado"] == "En juego"
    assert partido["fecha_hora"] == "2030-06-15T18:30:00"
    assert partido["eventos"] == [{"tipo": "Gol", "minuto": 32, "descripcion": None, "jugador_codigo": "J-ARG-01"}]
