"""Validacion offline: sin driver, Docker, conexiones ni escrituras en bases."""
import datetime
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import random
import sys
import time
import types
import unittest
from unittest.mock import Mock, patch, mock_open

V=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V/'carga'))
import perfil_paralelo as perfil
spec=importlib.util.spec_from_file_location('benchmark_m02',V/'carga/prueba_rendimiento.py')
bench=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def trabajador_falso(indice):
    # Prueba solamente spawn y rendezvous, sin generar ni enviar operaciones.
    preparado=time.perf_counter_ns()
    perfil.esperar_inicio()
    return os.getpid(), preparado, time.perf_counter_ns()


class ParalelismoTests(unittest.TestCase):
    def tearDown(self):
        perfil.inicializar_worker(None)

    def test_datos_identicos_a_base_y_entre_perfiles(self):
        azar=random.Random(2030)
        esperado=[]
        for i in range(50000):
            momento=bench.BASE+datetime.timedelta(milliseconds=i)
            esperado.append(('H12-offline',i%13,bench.timeuuid(momento,i),f'user-{i%5000:06d}',
                'Comentario de prueba de rendimiento',momento,'visible',azar.randint(0,10)))
        a=perfil.parametros(0,50000,'H12-offline',bench.BASE,bench.timeuuid)
        b=perfil.parametros(0,25000,'H12-offline',bench.BASE,bench.timeuuid)+perfil.parametros(
            25000,50000,'H12-offline',bench.BASE,bench.timeuuid)
        self.assertEqual(esperado,a)
        self.assertEqual(a,b)
        self.assertEqual(len({fila[2] for fila in b}),50000)

    def test_perfiles_validos_total_100(self):
        for nombre, valores in perfil.PERFILES.items():
            perfil.validar_perfil(nombre,*valores)
            self.assertEqual(valores[1]*valores[2],100)

    def test_rechazo_antes_de_conectar(self):
        with patch.object(bench,'Cluster') as cluster:
            for nombre, valores in [('B',(50000,100,2)),('A',(50000,50,1)),('B',(1000,50,2))]:
                with self.assertRaises(ValueError):
                    bench.correr_prueba(valores[0],valores[1],'no-usar',9042,valores[2],
                        'fixture2030','H12-offline',Path('no_crear.jsonl'),nombre)
            cluster.assert_not_called()

    def test_espera_y_aborto(self):
        barrera=Mock()
        perfil.inicializar_worker(barrera)
        perfil.esperar_inicio();barrera.wait.assert_called_once_with(timeout=60)
        perfil.abortar_inicio();barrera.abort.assert_called_once_with()

    def test_spawn_y_barrera_dos_procesos_sin_base(self):
        contexto=multiprocessing.get_context('spawn')
        barrera=contexto.Barrier(2)
        with contexto.Pool(2,initializer=perfil.inicializar_worker,initargs=(barrera,)) as pool:
            resultados=pool.map_async(trabajador_falso,[0,1]).get(timeout=30)
        self.assertEqual(len({r[0] for r in resultados}),2)
        self.assertGreaterEqual(min(r[2] for r in resultados),max(r[1] for r in resultados))

    def test_fallo_preparacion_aborta_y_cierra(self):
        barrera=Mock();perfil.inicializar_worker(barrera)
        cluster=Mock();cluster.connect.side_effect=RuntimeError('fallo simulado')
        with patch.object(Path,'open',mock_open()), patch.object(bench,'Cluster',return_value=cluster):
            salida=bench.trabajo((0,0,1,50,'falso',9042,'fixture2030','H12-offline','salida_falsa.jsonl'))
        self.assertIsNotNone(salida['error_fase'])
        self.assertIsNone(salida['inicio_ns'])
        barrera.abort.assert_called_once_with();cluster.shutdown.assert_called_once_with()

    def test_prepare_y_barrera_antes_del_envio(self):
        orden=[]
        barrera=Mock();barrera.wait.side_effect=lambda **kw:orden.append('barrera')
        perfil.inicializar_worker(barrera)
        cluster=Mock();session=cluster.connect.return_value
        session.prepare.side_effect=lambda _:orden.append('prepare') or 'insert_falso'
        medida=Mock(muestras=[],siguiente=2,max_en_curso=2)
        modulo=types.ModuleType('cassandra.cluster');modulo.EXEC_PROFILE_DEFAULT='falso'
        def enviar(*args,**kwargs):
            orden.append('envio')
            self.assertEqual(len(args[2]),2)
            self.assertEqual(kwargs,dict(concurrency=50,raise_on_first_error=False))
            return [(True,None),(True,None)]
        with patch.dict(sys.modules,{'cassandra.cluster':modulo}), \
             patch.object(bench,'Cluster',return_value=cluster), \
             patch.object(bench,'version',return_value='falsa'), \
             patch.object(bench,'SesionMedida',return_value=medida), \
             patch.object(bench,'execute_concurrent_with_args',side_effect=enviar,create=True), \
             patch.object(Path,'open',mock_open()):
            resultado=bench.trabajo((0,0,2,50,'falso',9042,'fixture2030','H12-offline','falso.jsonl'))
        self.assertIsNone(resultado['error_fase'])
        self.assertEqual(orden,['prepare','barrera','envio'])
        barrera.abort.assert_not_called()

    def test_medidor_y_verificador_historicos_identicos(self):
        base=V.parent/'v2.0_base'
        for relativo in ['carga/metricas_operaciones.py','carga/verificar_escrituras.py',
                         'scripts/esquema_comentarios_h6.cql','carga/requirements.txt']:
            self.assertEqual((V/relativo).read_bytes(),(base/relativo).read_bytes())
        self.assertEqual(hashlib.sha256((base/'carga/prueba_rendimiento.py').read_bytes()).hexdigest(),
            '1f079cf0dd0772adce7605744c60348382493811438ae47485e78ba3e33ea3ca')

    def test_configuracion_concuerda(self):
        config=json.loads((V/'config/escenario_escritura_simple.json').read_text(encoding='utf-8'))
        for nombre,(filas,concurrencia,procesos) in perfil.PERFILES.items():
            self.assertEqual(config['perfiles'][nombre],dict(filas=filas,concurrencia_por_proceso=concurrencia,procesos=procesos))


if __name__=='__main__':
    unittest.main()
