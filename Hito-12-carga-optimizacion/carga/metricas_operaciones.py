"""Instrumentación del cliente: no abre conexiones y no envía consultas por sí sola."""
from collections import Counter
from datetime import datetime, timezone
import math
import statistics
import threading
import time


def detalle_error(exc):
    salida={'tipo':type(exc).__name__}
    # No registrar mensajes libres ni direcciones: pueden contener datos del destino.
    for nombre in ('code','received_responses','required_responses','write_type','consistency'):
        valor=getattr(exc,nombre,None)
        if isinstance(valor,(int,float,str,bool)):
            salida[nombre]=valor
    causas=getattr(exc,'errors',None)
    if isinstance(causas,dict):
        salida['tipos_causa']=sorted({type(e).__name__ for e in causas.values()})
    return salida


def estadisticas_ms(valores):
    datos=sorted(valores)
    if not datos:
        return {'n':0,'min':None,'promedio':None,'p50':None,'p95':None,'p99':None,'max':None}
    def pct(q):return datos[max(0,math.ceil(len(datos)*q)-1)]
    return {'n':len(datos),'min':datos[0],'promedio':statistics.fmean(datos),
            'p50':pct(.5),'p95':pct(.95),'p99':pct(.99),'max':datos[-1]}


class SesionMedida:
    """Delega al driver original. Conserva su planificador y añade callbacks de medición.

    La latencia va desde antes de execute_async hasta el callback (o excepción síncrona).
    Incluye trabajo del driver/red/reintentos implícitos; no es tiempo puro del servidor.
    No incluye espera de turno antes del envío, conexión ni prepare.
    """
    def __init__(self,sesion,proceso,desde=0,reloj=time.perf_counter_ns):
        self.sesion=sesion;self.proceso=proceso;self.siguiente=desde;self.reloj=reloj
        self.lock=threading.Lock();self.muestras=[];self.en_curso=0;self.max_en_curso=0

    def __getattr__(self,nombre):return getattr(self.sesion,nombre)

    def execute_async(self,statement,parameters,*args,**kwargs):
        with self.lock:
            numero=self.siguiente;self.siguiente+=1
            self.en_curso+=1;self.max_en_curso=max(self.max_en_curso,self.en_curso)
        inicio=self.reloj();terminada=False
        def terminar(ok,exc=None):
            nonlocal terminada
            fin=self.reloj()
            with self.lock:
                if terminada:return
                terminada=True;self.en_curso-=1
                self.muestras.append({'operacion':numero,'proceso':self.proceso,
                    'bucket':parameters[1],'comentario_id':str(parameters[2]),
                    'inicio_monotonico_ns':inicio,'fin_monotonico_ns':fin,
                    'fecha_fin_utc':datetime.now(timezone.utc).isoformat(),
                    'latencia_ms':(fin-inicio)/1_000_000,'confirmada':ok,
                    'error':None if ok else detalle_error(exc)})
        try:
            future=self.sesion.execute_async(statement,parameters,*args,**kwargs)
            future.add_callbacks(callback=lambda _r:terminar(True),
                                 errback=lambda exc:terminar(False,exc))
            return future
        except Exception as exc:
            terminar(False,exc)
            raise


def resumir(muestras,previstas,segundos_total,inicio_ns,fin_ns,iniciadas=None):
    confirmadas=[r for r in muestras if r['confirmada']]
    errores=[r for r in muestras if not r['confirmada']]
    segundos_carga=(fin_ns-inicio_ns)/1e9 if inicio_ns is not None and fin_ns is not None else 0
    tipos=Counter(r['error']['tipo'] for r in errores)
    por_segundo={}
    for r in muestras:
        segundo=max(0,(r['fin_monotonico_ns']-inicio_ns)//1_000_000_000)
        fila=por_segundo.setdefault(segundo,{'segundo':segundo,'confirmadas':0,'sin_confirmacion':0})
        fila['confirmadas' if r['confirmada'] else 'sin_confirmacion']+=1
    serie=[]
    for segundo in range(math.ceil(segundos_carga)):
        fila=por_segundo.get(segundo,{'segundo':segundo,'confirmadas':0,'sin_confirmacion':0})
        ancho=min(1.0,max(0.0,segundos_carga-segundo))
        serie.append({**fila,'duracion_intervalo_s':ancho,
                      'confirmadas_por_segundo':fila['confirmadas']/ancho if ancho else None})
    n=len(muestras)
    iniciadas=n if iniciadas is None else iniciadas
    inconclusas=max(0,iniciadas-n)
    return {'previstas':previstas,'intentadas':iniciadas,'con_resultado':n,
        'sin_resultado':inconclusas,'exitosas':len(confirmadas),'fallidas':len(errores),
        'sin_confirmacion_total':len(errores)+inconclusas,
        'no_intentadas':max(0,previstas-iniciadas),'segundos':segundos_total,'segundos_carga':segundos_carga,
        'escrituras_por_segundo':len(confirmadas)/segundos_carga if segundos_carga else 0,
        'intentos_por_segundo':iniciadas/segundos_carga if segundos_carga else 0,
        'escrituras_por_segundo_total':len(confirmadas)/segundos_total if segundos_total else 0,
        'tasa_error_porcentaje':100*len(errores)/iniciadas if iniciadas else None,
        'tasa_sin_confirmacion_porcentaje':100*(len(errores)+inconclusas)/iniciadas if iniciadas else None,
        'errores_por_tipo':dict(tipos),
        'latencia_todos_ms':estadisticas_ms([r['latencia_ms'] for r in muestras]),
        'latencia_confirmadas_ms':estadisticas_ms([r['latencia_ms'] for r in confirmadas]),
        'latencia_sin_confirmacion_ms':estadisticas_ms([r['latencia_ms'] for r in errores]),
        'percentiles_metodo':'rango mas cercano: ceil(q*n); sin promediar percentiles entre procesos',
        'serie_por_segundo':serie,
        'interpretacion_errores':'Sin confirmacion del cliente no implica rechazo ni ausencia en Cassandra; contrastar persistencia',
        'observaciones_estabilidad':[
            'Revisar serie temporal, errores y recursos durante la carga; una cifra agregada no demuestra estabilidad',
            'Ultimo intervalo puede ser parcial y se informa su duracion',
            'Las metricas incluyen el costo de instrumentacion del cliente; mantenerlo igual al comparar versiones']}
