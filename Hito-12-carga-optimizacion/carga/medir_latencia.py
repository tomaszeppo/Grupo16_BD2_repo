"""H12: mide GET de comentarios por la API, secuencialmente y sin escrituras.
Adaptado de H10/scripts/medir_latencia.py; ver docs/procedencia_scripts_carga.json.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import re
import statistics
import time
from urllib.parse import urlsplit

import httpx


def main(args):
    url=urlsplit(args.base_url)
    if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('base-url debe ser HTTP(S) sin credenciales, query ni fragmento')
    if args.n < 1 or args.calentamiento < 0 or not 1 <= args.limit <= 100 or args.timeout <= 0:
        raise ValueError('Revisar n, calentamiento, limit y timeout')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',args.partido) or not re.fullmatch(r'[A-Z]{3}',args.pais):
        raise ValueError('Partido o pais invalidos')
    ventana=datetime.fromisoformat(args.ventana.replace('Z','+00:00'))
    if ventana.tzinfo is None:
        raise ValueError('La ventana debe incluir zona horaria')
    ventana=ventana.astimezone(timezone.utc)
    if ventana.minute not in (0,30) or ventana.second or ventana.microsecond:
        raise ValueError('La ventana de la API H10 debe estar alineada a :00 o :30 UTC')
    ruta=f'partidos/{args.partido}/comentarios'
    params=dict(pais=args.pais,ventana=ventana.isoformat(),limit=args.limit)
    # La salida se reserva antes de enviar requests. Un archivo existente nunca se toca.
    with args.salida.open('x',encoding='utf-8') as archivo:
        with httpx.Client(base_url=args.base_url.rstrip('/')+'/',timeout=args.timeout) as client:
            def request():
                inicio=time.perf_counter()
                try:
                    r=client.get(ruta,params=params)
                    valida=False; cantidad=None
                    if r.status_code==200:
                        try:
                            body=r.json()
                            valida=isinstance(body,dict) and body.get('partido_id')==args.partido and body.get('pais')==args.pais and isinstance(body.get('items'),list)
                            if valida: cantidad=len(body['items'])
                        except ValueError:
                            pass
                    return dict(ms=(time.perf_counter()-inicio)*1000,status=r.status_code,
                                valida=valida,items=cantidad,request_id=r.headers.get('X-Request-ID'))
                except httpx.RequestError as exc:
                    return dict(ms=(time.perf_counter()-inicio)*1000,status=None,valida=False,tipo=type(exc).__name__)
            warm=[request() for _ in range(args.calentamiento)]
            inicio=time.perf_counter(); muestras=[request() for _ in range(args.n)]; elapsed=time.perf_counter()-inicio
        validas=[x['ms'] for x in muestras if x['valida']]; validas.sort()
        def percentil(q): return validas[max(0,math.ceil(len(validas)*q)-1)] if validas else None
        resumen=dict(intentos=len(muestras),validas=len(validas),errores=len(muestras)-len(validas),
            estados=dict(Counter(str(x['status']) for x in muestras)),segundos=elapsed,
            rps_intentos=len(muestras)/elapsed,rps_validas=len(validas)/elapsed,
            p50_validas_ms=statistics.median(validas) if validas else None,
            p95_validas_ms=percentil(.95),p99_validas_ms=percentil(.99))
        resultado=dict(fecha_utc=datetime.now(timezone.utc).isoformat(),metodo='GET secuencial, concurrencia 1',
            ruta='/'+ruta,parametros=params,base_url=args.base_url,python=platform.python_version(),httpx=httpx.__version__,
            n=args.n,calentamiento=args.calentamiento,fallos_calentamiento=sum(not x['valida'] for x in warm),
            resumen=resumen,muestras=muestras)
        json.dump(resultado,archivo,ensure_ascii=False,indent=2)
    print(json.dumps(resumen,indent=2))
    return 1 if resumen['errores'] else 0


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-url',required=True)
    ap.add_argument('--partido',required=True)
    ap.add_argument('--pais',required=True)
    ap.add_argument('--ventana',required=True)
    ap.add_argument('--limit',type=int,default=20)
    ap.add_argument('--n',type=int,default=50)
    ap.add_argument('--calentamiento',type=int,default=5)
    ap.add_argument('--timeout',type=float,default=15)
    ap.add_argument('--salida',type=Path,required=True,help='Archivo JSON nuevo; carpeta existente')
    raise SystemExit(main(ap.parse_args()))
