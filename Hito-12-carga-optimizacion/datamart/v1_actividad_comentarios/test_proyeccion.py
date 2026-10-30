"""Pruebas de transformacion en memoria. Sin Cassandra, Docker ni archivos de datos."""
from datetime import datetime, timedelta
from types import SimpleNamespace
import unittest
from proyectar_comentarios import agregar


def fila(i, usuario='u1', segundos=0, estado='visible', likes=2):
    return SimpleNamespace(comentario_id=str(i),usuario_id=usuario,
        creado_en=datetime(2030,6,8,18)+timedelta(seconds=segundos),
        bucket=i%13,estado_moderacion=estado,likes=likes)


class ProyeccionTests(unittest.TestCase):
    def test_grano_usuarios_distintos_y_medidas(self):
        registros,n,buckets=agregar([fila(0),fila(1),fila(2,'u2',estado='pendiente'),fila(3,segundos=60)],'H12-test',10)
        self.assertEqual(n,4)
        self.assertEqual(len(registros),2)
        self.assertEqual(registros[0][2:],(3,2,2,1,6))
        self.assertEqual(sum(buckets.values()),4)

    def test_duplicado_rechazado(self):
        with self.assertRaises(ValueError):agregar([fila(0),fila(0)],'H12-test',10)

    def test_limite_acotado(self):
        with self.assertRaises(ValueError):agregar([fila(0),fila(1)],'H12-test',1)

    def test_faltantes_rechazados(self):
        with self.assertRaises(ValueError):agregar([fila(0,usuario=None)],'H12-test',10)


if __name__=='__main__':unittest.main()
