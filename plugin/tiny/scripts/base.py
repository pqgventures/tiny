#!/usr/bin/env python3
"""tiny base: desenha um mapa base isométrico a partir do OpenStreetMap e corta em quadros.

uso: python3 base.py "<lugar>" [raio_m] [saida]
grava <saida>/base.png (mapa inteiro), <saida>/tiles/<c>_<l>.png (quadros 1024 com sobreposição) e <saida>/plan.json
"""
import sys, json, math, hashlib, urllib.parse, os, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

UA = {'User-Agent': 'tiny-plugin/0.1 (bruno@pqgventures.com)'}
K = 4.0          # px por metro no eixo isométrico
HZ = 3.2         # px por metro de altura
TILE, OVER = 1024, 160

def get(url, data=None):
    cmd = ['curl', '-sS', '--fail', '-m', '200', '-A', UA['User-Agent'], url]
    if data is not None: cmd[1:1] = ['--data-binary', '@-']
    r = subprocess.run(cmd, input=data, capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode()[:200])
    return json.loads(r.stdout)

def geocode(q):
    r = get('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 1}))
    if not r: raise SystemExit('lugar não encontrado: ' + q)
    return float(r[0]['lat']), float(r[0]['lon']), r[0]['display_name']

def overpass(lat, lon, R):
    a = f'(around:{R},{lat},{lon})'
    q = f"""[out:json][timeout:120];(
way["building"]{a};relation["building"]{a};
way["highway"]{a};
way["leisure"~"park|garden|pitch|playground"]{a};way["landuse"~"grass|park|forest|meadow|recreation_ground|cemetery"]{a};
way["natural"~"water|wood|scrub|beach|sand"]{a};relation["natural"="water"]{a};way["waterway"~"river|canal|stream"]{a};
way["amenity"~"parking"]{a};way["railway"~"rail|subway|tram"]{a};
node["natural"="tree"]{a};
);out geom;"""
    for host in ('https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'):
        try: return get(host, urllib.parse.urlencode({'data': q}).encode())['elements']
        except Exception as e: err = e
    raise SystemExit(f'overpass falhou: {err}')

def main():
    place = sys.argv[1]; R = int(sys.argv[2]) if len(sys.argv) > 2 else 260
    out = Path(sys.argv[3] if len(sys.argv) > 3 else 'tiny'); (out / 'tiles').mkdir(parents=True, exist_ok=True)
    lat, lon, name = geocode(place)
    cache = out / 'osm.json'
    if cache.exists() and json.loads(cache.read_text()).get('key') == [lat, lon, R]: els = json.loads(cache.read_text())['elements']
    else:
        els = overpass(lat, lon, R + 60); cache.write_text(json.dumps({'key': [lat, lon, R], 'elements': els}))
    mx = 111320 * math.cos(math.radians(lat)); my = 110540
    def xy(p): return ((p['lon'] - lon) * mx, (p['lat'] - lat) * my)
    def scr(x, y, z=0): return ((x - y) * K * 0.7071, -(x + y) * K * 0.3536 - z * HZ)
    feats = []
    for e in els:
        t = e.get('tags', {}); geoms = []
        if e['type'] == 'way' and 'geometry' in e: geoms = [[xy(p) for p in e['geometry']]]
        elif e['type'] == 'relation': geoms = [[xy(p) for p in m['geometry']] for m in e.get('members', []) if m.get('role') == 'outer' and 'geometry' in m]
        elif e['type'] == 'node': geoms = [[xy(e)]]
        for g in geoms: feats.append((t, g))
    # limites da área (losango recortado em quadrado no chão)
    corners = [scr(x, y) for x in (-R, R) for y in (-R, R)]
    maxh = 120 * HZ
    x0 = min(c[0] for c in corners); x1 = max(c[0] for c in corners); y0 = min(c[1] for c in corners) - maxh; y1 = max(c[1] for c in corners)
    W, H = int(x1 - x0) + 2, int(y1 - y0) + 2
    im = Image.new('RGB', (W, H), (222, 216, 202)); d = ImageDraw.Draw(im)
    P = lambda x, y, z=0: (lambda s: (s[0] - x0, s[1] - y0))(scr(x, y, z))
    # chão: área fora do raio fica num tom mais claro
    d.polygon([P(-R, -R), P(R, -R), P(R, R), P(-R, R)], fill=(214, 207, 190))
    GREEN = (148, 186, 112); WATER = (118, 170, 206)
    def ground(t):
        if t.get('natural') in ('water',) or t.get('waterway'): return WATER
        if t.get('natural') in ('beach', 'sand'): return (232, 214, 168)
        if t.get('leisure') or t.get('landuse') or t.get('natural') in ('wood', 'scrub'): return GREEN if t.get('landuse') != 'cemetery' else (170, 182, 150)
        if t.get('amenity') == 'parking': return (176, 174, 168)
        return None
    for t, g in feats:
        c = ground(t)
        if c and len(g) >= 3 and not t.get('waterway'): d.polygon([P(x, y) for x, y in g], fill=c)
    RW = {'motorway': 22, 'trunk': 20, 'primary': 18, 'secondary': 15, 'tertiary': 12, 'residential': 9, 'unclassified': 9, 'living_street': 7,
          'service': 5, 'pedestrian': 6, 'footway': 2.5, 'path': 2, 'cycleway': 2.5, 'steps': 2}
    for t, g in feats:
        hw = t.get('highway'); wwy = t.get('waterway'); rw = t.get('railway')
        if t.get('area') == 'yes' or len(g) < 2: continue
        if wwy: w, col = {'river': 30, 'canal': 14}.get(wwy, 5), WATER
        elif hw in RW: w, col = RW[hw], (120, 120, 118) if RW[hw] >= 5 else (200, 192, 176)
        elif rw: w, col = 3, (96, 86, 80)
        else: continue
        pts = [P(x, y) for x, y in g]; d.line(pts, fill=col, width=max(1, int(w * K * 0.42)), joint='curve')
    # árvores e prédios juntos, pintados de trás pra frente (maior x+y primeiro)
    objs = []
    for t, g in feats:
        if t.get('natural') == 'tree' and len(g) == 1: objs.append((g[0][0] + g[0][1], 'tree', g[0], 0, t)); continue
        if 'building' in t and len(g) >= 3:
            try: h = float(str(t.get('height', '')).replace(',', '.').split()[0])
            except (ValueError, IndexError): h = 0
            if not h and t.get('building:levels'):
                try: h = float(t['building:levels']) * 3.2
                except ValueError: h = 0
            if not h:
                hv = int(hashlib.md5(str(g[0]).encode()).hexdigest(), 16)
                h = {'house': 6, 'garage': 3, 'shed': 3, 'church': 18}.get(t.get('building'), 7 + hv % 4 * 3)
            objs.append((max(x + y for x, y in g), 'bld', g, h, t))
    objs.sort(key=lambda o: -o[0])
    for _, kind, g, h, t in objs:
        if kind == 'tree':
            x, y = g; cx, cy = P(x, y, 5); r = 2.6 * K
            d.ellipse([cx - r, cy - r * 0.9, cx + r, cy + r * 0.9], fill=(96, 150, 78), outline=(70, 112, 58)); continue
        ring = g if g[0] != g[-1] else g[:-1]
        area = sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring))) / 2
        if area < 0: ring = ring[::-1]          # anti-horário
        for i in range(len(ring)):
            (ax, ay), (bx, by) = ring[i], ring[(i + 1) % len(ring)]
            nx, ny = by - ay, -(bx - ax)        # normal para fora
            if nx + ny >= 0: continue           # parede de costas para a câmera (câmera em x+y negativo)
            shade = (176, 168, 156) if nx < ny else (150, 142, 132)
            d.polygon([P(ax, ay), P(bx, by), P(bx, by, h), P(ax, ay, h)], fill=shade, outline=(92, 86, 80))
        roof = (196, 120, 92) if t.get('building') in ('house', 'residential', 'detached', 'terrace') and h <= 9 else (232, 228, 218)
        d.polygon([P(x, y, h) for x, y in ring], fill=roof, outline=(92, 86, 80))
    im.save(out / 'base.png')
    # corte em quadros com sobreposição
    step = TILE - OVER; tiles = []
    cols = max(1, math.ceil((W - OVER) / step)); rows = max(1, math.ceil((H - OVER) / step))
    for r in range(rows):
        for c in range(cols):
            bx, by = c * step, r * step
            crop = Image.new('RGB', (TILE, TILE), (214, 207, 190)); crop.paste(im.crop((bx, by, min(W, bx + TILE), min(H, by + TILE))), (0, 0))
            crop.save(out / 'tiles' / f'{c}_{r}.png'); tiles.append({'id': f'{c}_{r}', 'c': c, 'r': r, 'x': bx, 'y': by})
    cc, cr = (cols - 1) / 2, (rows - 1) / 2
    tiles.sort(key=lambda t: max(abs(t['c'] - cc), abs(t['r'] - cr)))   # do centro para fora
    plan = {'place': place, 'name': name, 'lat': lat, 'lon': lon, 'radius_m': R, 'size': [W, H], 'tile': TILE, 'overlap': OVER, 'cols': cols, 'rows': rows,
            'buildings': sum(1 for o in objs if o[1] == 'bld'), 'tiles': tiles}
    (out / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(json.dumps({k: plan[k] for k in ('name', 'size', 'cols', 'rows', 'buildings')}, ensure_ascii=False))

if __name__ == '__main__': main()

