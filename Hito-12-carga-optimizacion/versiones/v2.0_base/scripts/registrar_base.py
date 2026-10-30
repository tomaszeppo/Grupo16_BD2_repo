"""Registra entorno y recursos por lectura. No inicia cargas ni crea/modifica bases."""
import argparse
import ctypes
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def utc():return datetime.now(timezone.utc).isoformat()


def comando(args,timeout=20):
    try:
        p=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        return {'ok':p.returncode==0,'codigo':p.returncode,'salida':p.stdout.strip()}
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {'ok':False,'tipo':type(exc).__name__,'salida':''}


def inspeccionar(nombre):
    dato=comando(['docker','inspect',nombre])
    if not dato['ok']:return {'disponible':False}
    try:
        o=json.loads(dato['salida'])[0];host=o.get('HostConfig',{});config=o.get('Config',{})
        return {'disponible':True,'nombre':o.get('Name'),'imagen_etiqueta':config.get('Image'),
            'imagen_id':o.get('Image'),'estado':o.get('State',{}).get('Status'),
            'limites':{k:host.get(k) for k in ['Memory','MemorySwap','NanoCpus','CpuQuota','CpuPeriod','CpusetCpus']},
            'redes':list(o.get('NetworkSettings',{}).get('Networks',{}))}
    except (ValueError,KeyError,IndexError):return {'disponible':False,'tipo':'RespuestaInesperada'}


class RecursosHost:
    def __init__(self):self.anterior=None

    def muestra(self):
        base={'cpu_porcentaje':None,'ram_total_bytes':None,'ram_usada_bytes':None,
              'nota':'Mediciones del host; CPU Docker usa otra escala (100% equivale a un nucleo)'}
        if platform.system()!='Windows':
            base['no_disponible']='Recolector host implementado para Windows; usar recursos de contenedores'
            return base
        try:
            class Mem(ctypes.Structure):
                _fields_=[('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[(n,ctypes.c_uint64) for n in
                    ['total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended']]
            m=Mem();m.length=ctypes.sizeof(m)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                base.update(ram_total_bytes=m.total_phys,ram_usada_bytes=m.total_phys-m.avail_phys,
                            ram_porcentaje=m.load)
            idle=ctypes.c_uint64();kernel=ctypes.c_uint64();user=ctypes.c_uint64()
            if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle),ctypes.byref(kernel),ctypes.byref(user)):
                actual=(idle.value,kernel.value+user.value)
                if self.anterior:
                    di=actual[0]-self.anterior[0];dt=actual[1]-self.anterior[1]
                    base['cpu_porcentaje']=max(0,min(100,100*(dt-di)/dt)) if dt>0 else None
                self.anterior=actual
        except (OSError,AttributeError) as exc:base['no_disponible']=type(exc).__name__
        return base


def entorno(args):
    with args.salida.open('x',encoding='utf-8') as f:
        archivos={}
        for relativo in ['carga/prueba_rendimiento.py','carga/metricas_operaciones.py',
                         'carga/verificar_escrituras.py','config/escenario_escritura_simple.json',
                         'scripts/esquema_comentarios_h6.cql','scripts/registrar_base.py']:
            p=ROOT/relativo;archivos[relativo]=hashlib.sha256(p.read_bytes()).hexdigest()
        head=comando(['git','-C',str(ROOT),'rev-parse','HEAD'])
        status=comando(['git','-C',str(ROOT),'status','--short'])
        info=comando(['docker','info','--format','{{json .}}'])
        producto={}
        if info['ok']:
            try:
                o=json.loads(info['salida'])
                producto={k:o.get(k) for k in ['ServerVersion','OperatingSystem','OSType','Architecture','NCPU','MemTotal','KernelVersion']}
            except ValueError:producto={'disponible':False}
        esquema=comando(['docker','exec',args.cassandra,'cqlsh','-e',
            'SHOW VERSION; DESCRIBE TABLE fixture2030.comentarios_por_partido;'])
        configuracion=json.loads((ROOT/'config/escenario_escritura_simple.json').read_text(encoding='utf-8'))
        dato={'fecha_utc':utc(),'modo':'solo_lectura','commit':head,'estado_git':status,
            'codigo_sha256':archivos,'escenario':configuracion,
            'api':'No interviene: el benchmark usa directamente el modulo Cassandra',
            'host':{'sistema':platform.platform(),'python_registro':platform.python_version(),'cpu_logicas':os.cpu_count(),
                    'recursos':RecursosHost().muestra()},'docker':producto,
            'cassandra':inspeccionar(args.cassandra),'cliente':inspeccionar(args.cliente),
            'cliente_imagen':comando(['docker','image','inspect','fixture2030-api-api','--format','{{.Id}}']),
            'version_y_esquema_cassandra':esquema,
            'nota':'Sin variables de entorno de contenedores ni credenciales; limites 0 indican ausencia de limite individual'}
        json.dump(dato,f,ensure_ascii=False,indent=2)
    print(f'Entorno guardado en {args.salida}')
    if not esquema['ok']:print('No se pudo leer el esquema; revisar antes de medir.')


def recursos(args):
    if args.intervalo<=0 or args.max_segundos<=0:raise ValueError('Intervalo y duracion deben ser positivos')
    with args.salida.open('x',encoding='utf-8') as f:
        def guardar(o):f.write(json.dumps(o,ensure_ascii=False)+'\n');f.flush()
        guardar({'evento':'inicio','fecha_utc':utc(),'intervalo_objetivo_s':args.intervalo,
            'max_segundos':args.max_segundos,'cassandra':args.cassandra,'cliente':args.cliente})
        host=RecursosHost();inicio=time.monotonic();motivo='duracion_maxima'
        print('Monitoreo de solo lectura activo. Ahora iniciar benchmark en la otra consola.')
        print('Se detiene al terminar el contenedor cliente o con Ctrl+C; no detiene Cassandra ni la carga.')
        try:
            while time.monotonic()-inicio<args.max_segundos:
                t=time.monotonic();fecha=utc();estado=inspeccionar(args.cliente)
                nombres=[args.cassandra]+([args.cliente] if estado.get('estado')=='running' else [])
                stats=comando(['docker','stats','--no-stream','--format','{{json .}}',*nombres],timeout=15)
                registros=[]
                for linea in stats['salida'].splitlines():
                    try:registros.append(json.loads(linea))
                    except ValueError:pass
                dato={'evento':'muestra','fecha_inicio_utc':fecha,'fecha_fin_utc':utc(),
                    'desde_inicio_s':t-inicio,'ventana_consulta_s':time.monotonic()-t,
                    'estado_cliente':estado.get('estado','no_creado'),'host':host.muestra(),
                    'contenedores':registros,'consulta_ok':stats['ok']}
                guardar(dato)
                print(f"{fecha} | cliente={dato['estado_cliente']} | CPU host={dato['host'].get('cpu_porcentaje')} | "+
                      ' | '.join(f"{r.get('Name')}: CPU={r.get('CPUPerc')} RAM={r.get('MemUsage')} RED={r.get('NetIO')} DISCO={r.get('BlockIO')}" for r in registros))
                if estado.get('estado') in ('exited','dead'):
                    motivo='cliente_terminado';break
                time.sleep(max(0,args.intervalo-(time.monotonic()-t)))
        except KeyboardInterrupt:motivo='interrupcion_manual_del_monitor'
        finally:guardar({'evento':'fin','fecha_utc':utc(),'motivo':motivo})
    print(f'Recursos conservados en {args.salida}')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('modo',choices=['entorno','recursos'])
    ap.add_argument('--salida',type=Path,required=True,help='Archivo NUEVO; carpeta existente')
    ap.add_argument('--cassandra',default='fixture2030-cassandra')
    ap.add_argument('--cliente',required=True)
    ap.add_argument('--intervalo',type=float,default=2)
    ap.add_argument('--max-segundos',type=float,default=600)
    args=ap.parse_args()
    (entorno if args.modo=='entorno' else recursos)(args)
