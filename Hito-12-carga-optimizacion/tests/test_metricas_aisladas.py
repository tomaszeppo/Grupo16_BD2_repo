"""Solo cálculos y futuros falsos en memoria. No importa Cassandra ni abre sockets."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'carga'))
from metricas_operaciones import SesionMedida,detalle_error,estadisticas_ms,resumir


class FutureFalso:
    def add_callbacks(self,callback,errback):self.ok=callback;self.error=errback


class SesionFalsa:
    def __init__(self):self.futures=[]
    def execute_async(self,*args,**kwargs):
        f=FutureFalso();self.futures.append(f);return f


class WriteTimeout(Exception):
    received_responses=0
    required_responses=1


class TestMetricas(unittest.TestCase):
    def test_percentiles_rango_cercano(self):
        d=estadisticas_ms(list(range(1,101)))
        self.assertEqual((d['min'],d['promedio'],d['p50'],d['p95'],d['p99'],d['max']),
                         (1,50.5,50,95,99,100))

    def test_sin_muestras_no_inventa_latencias(self):
        d=resumir([],50000,2,None,None)
        self.assertEqual(d['no_intentadas'],50000)
        self.assertIsNone(d['latencia_todos_ms']['min'])
        self.assertIsNone(d['tasa_error_porcentaje'])

    def test_callbacks_fuera_de_orden_error_y_doble_notificacion(self):
        reloj=[0];fake=SesionFalsa();s=SesionMedida(fake,0,reloj=lambda:reloj[0])
        a=s.execute_async('IGNORADO',('H12',0,'id0'))
        reloj[0]=1_000_000;b=s.execute_async('IGNORADO',('H12',1,'id1'))
        reloj[0]=5_000_000;b.error(WriteTimeout('NO GUARDAR MENSAJE'))
        reloj[0]=8_000_000;a.ok(None)
        a.error(WriteTimeout('notificacion duplicada'))
        self.assertEqual(len(s.muestras),2)
        self.assertEqual(s.max_en_curso,2);self.assertEqual(s.en_curso,0)
        self.assertEqual([m['latencia_ms'] for m in s.muestras],[4,8])
        d=resumir(s.muestras,2,1,0,1_000_000_000)
        self.assertEqual(d['exitosas'],1);self.assertEqual(d['fallidas'],1)
        self.assertEqual(d['errores_por_tipo'],{'WriteTimeout':1})
        self.assertEqual(d['tasa_error_porcentaje'],50)
        self.assertNotIn('NO GUARDAR',str(d))

    def test_excepcion_antes_de_futuro_cuenta_un_intento(self):
        class Falla:
            def execute_async(self,*args,**kwargs):raise WriteTimeout('secreto')
        ticks=iter([0,2_000_000]);s=SesionMedida(Falla(),0,reloj=lambda:next(ticks))
        with self.assertRaises(WriteTimeout):s.execute_async('',('H12',0,'id'))
        self.assertEqual(len(s.muestras),1)
        self.assertFalse(s.muestras[0]['confirmada']);self.assertEqual(s.en_curso,0)

    def test_error_no_expone_hosts_ni_mensajes(self):
        e=WriteTimeout('password=secreto');e.errors={'host-privado':ValueError('token=secreto')}
        d=detalle_error(e)
        self.assertEqual(d['tipos_causa'],['ValueError'])
        self.assertNotIn('secreto',str(d));self.assertNotIn('host-privado',str(d))

    def test_percentil_global_no_promedia_procesos(self):
        muestras=[dict(confirmada=True,latencia_ms=v,fin_monotonico_ns=500_000_000,error=None)
                  for v in [1]+[9]*9]
        d=resumir(muestras,10,2,0,1_500_000_000)
        self.assertEqual(d['latencia_todos_ms']['p50'],9)
        self.assertEqual(len(d['serie_por_segundo']),2)
        self.assertEqual(d['serie_por_segundo'][1]['duracion_intervalo_s'],.5)
        self.assertEqual(d['serie_por_segundo'][1]['confirmadas'],0)

    def test_inconclusa_no_se_confunde_con_no_intentada(self):
        muestra=dict(confirmada=True,latencia_ms=1,fin_monotonico_ns=1,error=None)
        d=resumir([muestra],10,1,0,1_000_000_000,iniciadas=4)
        self.assertEqual(d['intentadas'],4)
        self.assertEqual(d['sin_resultado'],3)
        self.assertEqual(d['no_intentadas'],6)
        self.assertEqual(d['tasa_sin_confirmacion_porcentaje'],75)


if __name__=='__main__':unittest.main()
