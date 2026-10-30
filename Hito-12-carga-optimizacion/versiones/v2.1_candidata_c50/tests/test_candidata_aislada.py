"""Verifica perfil y conservación; no envía operaciones, no usa Docker ni abre sockets."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

VERSION=Path(__file__).resolve().parents[1]
BASE=VERSION.parent/'v2.0_base'
sys.path.insert(0,str(VERSION/'carga'))
spec=importlib.util.spec_from_file_location('candidata_c50',VERSION/'carga/prueba_rendimiento.py')
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)


class TestCandidata(unittest.TestCase):
    def test_perfil_c50_valido_solo_lee_configuracion(self):
        perfil=candidate.validar_perfil(50000,50,1)
        self.assertEqual(perfil['version_experimento'],'v2.1_candidata_c50')

    def test_comando_anterior_se_rechaza_antes_de_conectar(self):
        original=candidate.Cluster
        def prohibido(*args,**kwargs):raise AssertionError('No se permite conectar en estas verificaciones')
        candidate.Cluster=prohibido
        try:
            with self.assertRaisesRegex(ValueError,'concurrencia 50'):
                candidate.correr_prueba(50000,100,'no-usado',9042,1,'fixture2030','H12-no-usado','NO_CREAR.jsonl')
        finally:candidate.Cluster=original

    def test_otros_cambios_de_carga_requieren_otra_version(self):
        for parametros in [(1000,50,1),(50000,50,2),(50000,200,1)]:
            with self.subTest(parametros=parametros),self.assertRaises(ValueError):
                candidate.validar_perfil(*parametros)

    def test_instrumentos_identicos_a_la_base(self):
        for nombre in ['carga/metricas_operaciones.py','carga/verificar_escrituras.py',
                       'scripts/registrar_base.py','scripts/esquema_comentarios_h6.cql','carga/requirements.txt']:
            self.assertEqual((BASE/nombre).read_bytes(),(VERSION/nombre).read_bytes(),nombre)

    def test_generacion_envio_y_medicion_conservados(self):
        trees=[ast.parse((root/'carga/prueba_rendimiento.py').read_text(encoding='utf-8')) for root in [BASE,VERSION]]
        for nombre in ['timeuuid','trabajo','ejecutar']:
            functions=[next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name==nombre) for t in trees]
            self.assertEqual(ast.dump(functions[0]),ast.dump(functions[1]),nombre)

    def test_historico_conserva_hashes_de_la_medicion(self):
        manifest=json.loads((BASE/'manifiesto_version.json').read_text(encoding='utf-8'))
        for entry in manifest['archivos']:
            self.assertEqual(hashlib.sha256((BASE/entry['ruta']).read_bytes()).hexdigest(),entry['sha256'])


if __name__=='__main__':unittest.main()
