import re, sys
sys.path.insert(0, 'C:/Users/Galli/Desktop/personal/Hitos/Grupo16_BD2_repo/Grupo6-nuestro/scratch_tools')
from codigos import MAPA, VIEJOS

base = 'C:/Users/Galli/Desktop/personal/Hitos/Grupo16_BD2_repo/Grupo6-nuestro/redis/scripts/'

# --- carga_muestra.redis: codigos FIFA, timestamps 2030, DEL inicial ---
p = base + 'carga_muestra.redis'
t = open(p, encoding='utf-8').read()
t = re.sub(r'cache:equipo:(%s)\b' % VIEJOS, lambda m: 'cache:equipo:' + MAPA[m.group(1)], t)
t = re.sub(r'\\"codigo\\":\\"(%s)\\"' % VIEJOS, lambda m: '\\"codigo\\":\\"' + MAPA[m.group(1)] + '\\"', t)
t = t.replace('ZADD espectadores:P-01 1749408000 sess-000001', 'ZADD espectadores:P-01 1907172000 sess-000001')
t = t.replace('ZADD espectadores:P-01 1749408005 sess-000002', 'ZADD espectadores:P-01 1907172005 sess-000002')
t = t.replace('ZADD espectadores:P-01 1749408010 sess-000003', 'ZADD espectadores:P-01 1907172010 sess-000003')

# claves tocadas por la muestra (lista finita, nunca KEYS)
claves = []
for linea in t.splitlines():
    linea = linea.strip()
    if not linea or linea.startswith('#'):
        continue
    partes = linea.split()
    cmd = partes[0].upper()
    if cmd in ('HSET', 'SET', 'ZADD', 'INCR', 'SADD', 'EXPIRE'):
        claves.append(partes[1])
    elif cmd == 'EVAL':
        # EVAL "<script>" 2 hash zset ...
        m = re.search(r'" 2 (\S+) (\S+)', linea)
        claves += [m.group(1), m.group(2)]
vistas = []
for c in claves:
    if c not in vistas:
        vistas.append(c)
dels = '\n'.join('DEL ' + c for c in vistas)
cabecera = '''# --- Limpieza previa: borra las claves de muestra (lista finita, nunca KEYS) ---
# HINCRBY, INCR y EVAL suman sobre lo que ya hay; sin esto, correr la carga dos
# veces duplicaria puntos, antelacion y likes. Con el DEL inicial el resultado es
# el mismo en la primera y en la N-esima corrida.
'''
corte = t.index('# --- Sesiones de muestra')
t = t[:corte] + cabecera + dels + '\n\n' + t[corte:]
open(p, 'w', encoding='utf-8').write(t)
print(len(vistas), 'claves en el DEL inicial')
