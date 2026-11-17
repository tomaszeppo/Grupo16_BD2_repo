"""Resume una comparativa A/B de M02 leyendo solo sus archivos. No conecta a Cassandra ni ejecuta cargas."""
import argparse
import csv
import json
from pathlib import Path
import statistics

METRICAS = [('segundos_carga', 'Tiempo de carga (s)'), ('throughput', 'Throughput (escrituras/s)'),
            ('promedio', 'Latencia promedio (ms)'), ('p50', 'p50 (ms)'), ('p95', 'p95 (ms)'),
            ('p99', 'p99 (ms)'), ('max', 'Latencia maxima (ms)')]


def leer_corrida(carpeta):
    eventos = [json.loads(l) for l in (carpeta/'escrituras.jsonl').open(encoding='utf-8')]
    r = next(e for e in eventos if e.get('evento') == 'resultado')
    v = json.loads((carpeta/'verificacion.json').read_text(encoding='utf-8'))
    lat = r['latencia_confirmadas_ms']
    # CPU de Docker: 100% equivale a un nucleo. Solo muestras con el cliente en ejecucion.
    cpu_cliente, cpu_cassandra = [], []
    for linea in (carpeta/'recursos.jsonl').open(encoding='utf-8'):
        m = json.loads(linea)
        if m.get('evento') != 'muestra':
            continue
        for c in m.get('contenedores', []):
            if c.get('CPUPerc') in (None, '--'):
                continue
            cpu = float(c['CPUPerc'].rstrip('%'))
            if c['Name'] == 'fixture2030-cassandra':
                cpu_cassandra.append(cpu)
            elif c['Name'].startswith('h12-') and m.get('estado_cliente') == 'running':
                cpu_cliente.append(cpu)
    return dict(segundos_carga=r['segundos_carga'], throughput=r['escrituras_por_segundo'],
                promedio=lat['promedio'], p50=lat['p50'], p95=lat['p95'], p99=lat['p99'], max=lat['max'],
                exitosas=r['exitosas'], fallidas=r['fallidas'], sin_confirmacion=r['sin_confirmacion_total'],
                no_intentadas=r['no_intentadas'], guardados=v['guardados'],
                particiones_ok=v['coincide'] and all(p['coincide'] for p in v['particiones']),
                cpu_cliente_max=max(cpu_cliente, default=None), muestras_cliente=len(cpu_cliente),
                cpu_cassandra_max=max(cpu_cassandra, default=None))


def resumir(grupo, salida_csv=None):
    protocolo = json.loads((grupo/'protocolo.json').read_text(encoding='utf-8'))
    corridas = {et: leer_corrida(grupo/et) for et in protocolo['orden']}
    for et, c in corridas.items():
        print(et, json.dumps(c, ensure_ascii=False))
    # Mediana de cada metrica por separado: puede provenir de corridas distintas.
    mediana = {g: {k: statistics.median(c[k] for et, c in corridas.items() if et[0] == g) for k, _ in METRICAS}
               for g in 'AB'}
    filas = []
    print()
    for k, nombre in METRICAS:
        a, b = mediana['A'][k], mediana['B'][k]
        filas.append(dict(metrica=nombre, mediana_A=a, mediana_B=b, variacion_porcentaje=(b-a)/a*100))
        print(f'{nombre}: A={a} B={b} variacion={(b-a)/a*100:.1f}%')
    criterios = protocolo['criterios']
    pares = [('A'+i, 'B'+i) for i in '123']
    ganadas = sum(corridas[b]['throughput'] > corridas[a]['throughput'] for a, b in pares)
    integras = all(c['fallidas'] == c['sin_confirmacion'] == c['no_intentadas'] == 0
                   and c['guardados'] == c['exitosas'] == protocolo['filas_por_corrida'] and c['particiones_ok']
                   for c in corridas.values())
    print('\nCriterios fijados en protocolo.json:')
    print(' throughput mediano +%d%% o mas:' % criterios['throughput_mediano_mejora_min_pct'],
          filas[1]['variacion_porcentaje'] >= criterios['throughput_mediano_mejora_min_pct'])
    print(' p99 mediano sin empeorar mas de %d%%:' % criterios['p99_mediano_regresion_max_pct'],
          filas[5]['variacion_porcentaje'] <= criterios['p99_mediano_regresion_max_pct'])
    print(' parejas con mas throughput en B: %d de 3 (minimo %d)' % (ganadas, criterios['parejas_mejor_throughput_min']))
    print(' cero errores y persistencia completa:', integras)
    if salida_csv:
        # Modo 'x': no se sobrescribe una tabla existente.
        with open(salida_csv, 'x', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['corrida'] + [k for k, _ in METRICAS] + ['exitosas', 'fallidas', 'guardados',
                        'particiones_ok', 'cpu_cliente_max_pct', 'muestras_cliente', 'cpu_cassandra_max_pct'])
            for et, c in corridas.items():
                w.writerow([et] + [c[k] for k, _ in METRICAS] + [c['exitosas'], c['fallidas'], c['guardados'],
                           c['particiones_ok'], c['cpu_cliente_max'], c['muestras_cliente'], c['cpu_cassandra_max']])
            for g in 'AB':
                w.writerow(['mediana_'+g] + [mediana[g][k] for k, _ in METRICAS])
        print('\nCSV:', salida_csv)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('grupo', type=Path, help='carpeta resultados/comparativas/m02-...')
    ap.add_argument('--csv', help='archivo nuevo donde guardar la tabla por corrida')
    args = ap.parse_args()
    resumir(args.grupo, args.csv)
