"""Verifica solo por lectura las 13 particiones de una corrida del benchmark H12.
No modifica ni elimina registros. Guarda un JSON nuevo de evidencia.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from cassandra.cluster import Cluster


def main(args):
    eventos=[json.loads(line) for line in args.registro.read_text(encoding='utf-8').splitlines() if line.strip()]
    config=next(e['configuracion'] for e in eventos if e.get('evento')=='inicio')
    resultado=next((e for e in reversed(eventos) if e.get('evento')=='resultado'),None)
    keyspace=config['keyspace']; partido=config['partido_prueba']; rows=int(config['rows'])
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',keyspace) or keyspace.lower().startswith('system'):
        raise ValueError('Keyspace invalido')
    if not re.fullmatch(r'H12-[A-Za-z0-9_-]{1,60}',partido) or rows<=0:
        raise ValueError('Partido o cantidad invalidos')
    # Exclusivo: no reemplazar una comprobacion anterior.
    with args.salida.open('x',encoding='utf-8') as f:
        cluster=Cluster([config['host']],port=config['puerto'],connect_timeout=10)
        try:
            ses=cluster.connect(keyspace);ses.default_timeout=30
            query=ses.prepare('SELECT count(*) FROM comentarios_por_partido WHERE partido_codigo=? AND bucket=?')
            particiones=[]
            print(f'Verificacion de solo lectura: {partido}')
            print('Bucket | Esperados | Guardados | Coincide')
            for bucket in range(13):
                n=ses.execute(query,(partido,bucket)).one()[0]
                esperado=rows//13+(1 if bucket<rows%13 else 0)
                particiones.append(dict(bucket=bucket,esperados=esperado,guardados=n,coincide=n==esperado))
                print(f'{bucket:6} | {esperado:9} | {n:9} | {"SI" if n==esperado else "NO"}')
            total=sum(p['guardados'] for p in particiones)
            ok=total==rows and all(p['coincide'] for p in particiones)
            cliente_ok=bool(resultado and resultado.get('exitosas')==rows and
                not resultado.get('fallidas') and not resultado.get('no_intentadas') and
                not resultado.get('sin_resultado') and
                not resultado.get('errores_fase'))
            print(f'Total esperado: {rows} | Total guardado: {total}')
            print('RESULTADO: '+('COINCIDE' if ok else 'REVISAR DIFERENCIAS'))
            print('Criterio completo (confirmaciones y persistencia): '+('CUMPLIDO' if ok and cliente_ok else 'REVISAR'))
            if resultado and total!=resultado.get('exitosas'):
                print('Conteos y confirmaciones difieren. Un timeout puede haber persistido; conservar evidencia.')
            json.dump(dict(fecha_utc=datetime.now(timezone.utc).isoformat(),modo='solo_lectura',
                partido_prueba=partido,keyspace=keyspace,esperados=rows,guardados=total,
                coincide=ok,particiones=particiones,
                confirmadas_cliente=resultado.get('exitosas') if resultado else None,
                sin_confirmacion_cliente=resultado.get('fallidas') if resultado else None,
                resultado_cliente_disponible=resultado is not None,
                criterio_completo_cumplido=ok and cliente_ok),f,indent=2)
            return 0 if ok and cliente_ok else 1
        except Exception as exc:
            json.dump(dict(estado='error',tipo=type(exc).__name__),f)
            raise
        finally:
            cluster.shutdown()


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--registro',type=Path,required=True,help='JSONL del benchmark')
    ap.add_argument('--salida',type=Path,required=True,help='JSON nuevo para la verificacion')
    raise SystemExit(main(ap.parse_args()))
