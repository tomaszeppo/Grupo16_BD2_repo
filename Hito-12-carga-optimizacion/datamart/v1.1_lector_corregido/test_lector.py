"""Regresion del lector con SQLite en memoria: sin archivos ni fuentes operacionales."""
import importlib.util
from pathlib import Path
import sqlite3
import unittest

spec = importlib.util.spec_from_file_location('lector_corregido', Path(__file__).with_name('consultar_proyeccion.py'))
lector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lector)


class LectorTests(unittest.TestCase):
    def test_punto_y_coma_en_comentarios_y_literales(self):
        texto = "-- comentario; no es una consulta\nSELECT 'a;b' AS valor;\n-- otro; comentario\nSELECT 2 AS total;\n"
        with sqlite3.connect(':memory:') as db:
            resultados = list(lector.consultar(db, texto))
        self.assertEqual(resultados, [(['valor'], [('a;b',)]), (['total'], [(2,)])])

    def test_archivo_original_que_fallo(self):
        archivo = Path(__file__).resolve().parents[1]/'v1_actividad_comentarios/consultas.sql'
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE actividad_comentarios(partido_codigo, minuto_utc, comentarios, usuarios_activos, comentarios_visibles, comentarios_otro_estado, likes_total)')
            db.execute("INSERT INTO actividad_comentarios VALUES ('H12-test','2030-06-08T18:00:00+00:00',3,2,3,0,7)")
            resultados = list(lector.consultar(db, archivo.read_text(encoding='utf-8')))
        self.assertEqual(len(resultados), 2)
        self.assertEqual(resultados[1][1], [(3, 3, 0)])

    def test_comentario_solo_no_produce_resultado(self):
        self.assertEqual(list(lector.separar_consultas('-- comentario; solamente\n')), [])

    def test_consulta_incompleta_rechazada(self):
        with self.assertRaises(ValueError):
            list(lector.separar_consultas('SELECT 1'))


if __name__ == '__main__':
    unittest.main()
