"""Ejecuta el protocolo M02 conservando archivos, contenedores y datos de cada corrida."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
VERSION = ROOT / 'versiones/v2.2_candidata_paralelo'


def guardar(path, dato):
    with path.open('x', encoding='utf-8') as f:
        json.dump(dato, f, ensure_ascii=False, indent=2)


def ejecutar(args):
    manifiesto = json.loads((VERSION/'manifiesto_version.json').read_text(encoding='utf-8'))
    for item in manifiesto['archivos']:
        actual = hashlib.sha256((VERSION/item['ruta']).read_bytes()).hexdigest()
        if actual != item['sha256']:
            raise ValueError('Cambio respecto del manifiesto: '+item['ruta'])
    imagen = manifiesto['ambiente_referencia']['imagen_cliente']
    subprocess.run(['docker','image','inspect',imagen,'--format','{{.Id}}'],check=True)
    subprocess.run(['docker','exec','fixture2030-cassandra','cqlsh','-e',
                    'SHOW VERSION; DESCRIBE TABLE fixture2030.comentarios_por_partido;'],check=True)
    marca = datetime.now().strftime('%Y%m%d-%H%M%S')
    grupo = ROOT/'resultados/comparativas'/('m02-'+marca)
    grupo.mkdir(parents=True, exist_ok=False)
    orden = ['A1','B1','B2','A2','A3','B3']
    guardar(grupo/'protocolo.json', dict(fecha_utc=datetime.now(timezone.utc).isoformat(),
        version='v2.2_candidata_paralelo',orden=orden,filas_por_corrida=50000,
        escrituras_planeadas=300000,imagen_cliente=imagen,concurrencia_total=100,
        hipotesis_previa_sha256=manifiesto['hipotesis_previa_sha256'],
        manifiesto_version_sha256=hashlib.sha256((VERSION/'manifiesto_version.json').read_bytes()).hexdigest(),
        ejecutor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        criterios=dict(throughput_mediano_mejora_min_pct=10,p99_mediano_regresion_max_pct=5,
                       parejas_mejor_throughput_min=2,cero_errores_y_persistencia_completa=True),
        conservacion='Sin borrado de datos, contenedores ni resultados',
        pausa_entre_corridas_s=10,calentamiento_separado=False))
    print('GRUPO: '+str(grupo), flush=True)
    with (grupo/'ejecucion.jsonl').open('x',encoding='utf-8') as eventos:
        for posicion, etiqueta in enumerate(orden):
            perfil=etiqueta[0]
            corrida='m02-'+etiqueta+'-'+marca
            cliente='h12-'+corrida.lower()
            destino=grupo/etiqueta
            destino.mkdir()
            (destino/'capturas').mkdir()
            relativo=destino.relative_to(ROOT).as_posix()
            guardar(destino/'escenario.json',dict(perfil=perfil,repeticion=etiqueta,
                filas=50000,procesos=1 if perfil=='A' else 2,concurrencia_por_proceso=100 if perfil=='A' else 50,
                concurrencia_total=100,partido='H12-'+corrida,cliente=cliente,
                version='v2.2_candidata_paralelo',configuracion=json.loads((VERSION/'config/escenario_escritura_simple.json').read_text(encoding='utf-8'))))
            print('INICIO '+etiqueta+' | '+cliente,flush=True)
            recorder=str(VERSION/'scripts/registrar_base.py')
            with (destino/'entorno.consola.txt').open('x',encoding='utf-8') as out:
                subprocess.run([sys.executable,recorder,'entorno','--perfil',perfil,'--cliente',cliente,
                    '--salida',str(destino/'entorno.json')],stdout=out,stderr=subprocess.STDOUT,check=True)
            comun=['docker','run','--pull=never','--name',cliente,'--network','fixture2030-cassandra_default',
                '--mount',f'type=bind,source={ROOT},target=/h12','--workdir','/h12','--entrypoint','python',imagen]
            comando=comun+['versiones/v2.2_candidata_paralelo/carga/prueba_rendimiento.py',
                '--perfil',perfil,'--host','fixture2030-cassandra','--puerto','9042','--keyspace','fixture2030',
                '--partido-prueba','H12-'+corrida,'--salida','/h12/'+relativo+'/escrituras.jsonl','--confirmar-escrituras']
            guardar(destino/'comandos.json',dict(benchmark=comando))
            inicio=datetime.now(timezone.utc).isoformat()
            with (destino/'recursos.consola.txt').open('x',encoding='utf-8') as monout:
                monitor=subprocess.Popen([sys.executable,'-u',recorder,'recursos','--perfil',perfil,
                    '--cliente',cliente,'--salida',str(destino/'recursos.jsonl')],stdout=monout,stderr=subprocess.STDOUT)
                # Esperar registro inicial del monitor, sin suponer que arranco correctamente.
                limite=time.monotonic()+20
                while not (destino/'recursos.jsonl').exists() and time.monotonic()<limite and monitor.poll() is None:
                    time.sleep(0.1)
                if monitor.poll() is not None or not (destino/'recursos.jsonl').exists():
                    raise RuntimeError('No arranco el monitor; no se ejecuta la carga')
                with (destino/'carga.consola.txt').open('x',encoding='utf-8') as out:
                    carga=subprocess.run(comando,stdout=out,stderr=subprocess.STDOUT)
                try:
                    monitor_rc=monitor.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    # El monitor tiene su propio maximo. No terminarlo ni borrar evidencia.
                    raise RuntimeError('Monitor sigue activo; revisar antes de otra carga')
            evento=dict(corrida=etiqueta,inicio_utc=inicio,fin_utc=datetime.now(timezone.utc).isoformat(),
                        carga_exit_code=carga.returncode,monitor_exit_code=monitor_rc)
            if carga.returncode!=0:
                eventos.write(json.dumps(evento)+'\n');eventos.flush()
                print((destino/'carga.consola.txt').read_text(encoding='utf-8'),flush=True)
                raise RuntimeError('Carga con errores; se conserva evidencia y no se continua')
            verificar=comun.copy();verificar[verificar.index('--name')+1]=cliente+'-verificacion'
            verificar+=['versiones/v2.2_candidata_paralelo/carga/verificar_escrituras.py',
                '--registro','/h12/'+relativo+'/escrituras.jsonl','--salida','/h12/'+relativo+'/verificacion.json']
            with (destino/'verificacion.consola.txt').open('x',encoding='utf-8') as out:
                verificacion=subprocess.run(verificar,stdout=out,stderr=subprocess.STDOUT)
            evento['verificacion_exit_code']=verificacion.returncode
            eventos.write(json.dumps(evento)+'\n');eventos.flush()
            print((destino/'carga.consola.txt').read_text(encoding='utf-8'),flush=True)
            if verificacion.returncode or monitor_rc:
                raise RuntimeError('Verificacion o monitor con error; no se continua')
            print('FIN '+etiqueta+' | persistencia verificada',flush=True)
            if posicion<len(orden)-1:
                time.sleep(10)
    print('COMPLETO: '+str(grupo),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--confirmar-escrituras',action='store_true')
    args=ap.parse_args()
    if not args.confirmar_escrituras:
        ap.error('El protocolo inserta y conserva hasta 300.000 comentarios; requiere --confirmar-escrituras')
    ejecutar(args)
