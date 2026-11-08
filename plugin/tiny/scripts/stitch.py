#!/usr/bin/env python3
"""tiny stitch: junta gen/<id>.png na posição de cada quadro do plan.json, reencaixa pelo mapa base e funde as sobreposições.
uso: python3 stitch.py <pasta>   -> <pasta>/tiny.png, <pasta>/tiny.jpg, <pasta>/index.html, <pasta>/qa.json"""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

N = 256
def edges(im):
    a = np.asarray(im.convert('L').resize((N, N), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2)), np.float32)
    e = np.abs(np.diff(a, axis=1, prepend=a[:, :1])) + np.abs(np.diff(a, axis=0, prepend=a[:1]))
    e -= e.mean(); return e / (e.std() + 1e-6)
def shift(a, b):
    c = np.fft.irfft2(np.fft.rfft2(a) * np.conj(np.fft.rfft2(b)), s=a.shape)
    i = np.unravel_index(np.argmax(c), c.shape); dy, dx = [v if v < N // 2 else v - N for v in i]
    return float(c[i] / a.size), dx, dy
def fit(base, g, T):
    eb = edges(base); best = (shift(eb, edges(g))[0], 1.0, 0, 0); k = T / N
    for s in np.arange(0.88, 1.121, 0.02):
        w = round(T * s); im = g.resize((w, w), Image.LANCZOS); c = Image.new('RGB', (T, T)); o = (T - w) // 2
        c.paste(im, (o, o)) if s <= 1 else c.paste(im.crop((-o, -o, -o + T, -o + T)), (0, 0))
        sc, dx, dy = shift(eb, edges(c))
        if abs(dx) < 24 and abs(dy) < 24 and sc > best[0]: best = (sc, float(s), dx, dy)
    sc, s, dx, dy = best; w = round(T * s); im = g.resize((w, w), Image.LANCZOS)
    ox, oy = round((T - w) / 2 + dx * k), round((T - w) / 2 + dy * k)
    out = Image.new('RGB', (T, T)); out.paste(im, (ox, oy))
    a = np.asarray(out).copy(); x0, y0, x1, y1 = max(0, ox), max(0, oy), min(T, ox + w), min(T, oy + w)
    a[:, :x0] = a[:, x0:x0 + 1]; a[:, x1:] = a[:, x1 - 1:x1]; a[:y0] = a[y0:y0 + 1]; a[y1:] = a[y1 - 1:y1]
    return Image.fromarray(a), {'corr_base': round(sc, 3), 'escala': round(s, 2), 'dx': int(dx * k), 'dy': int(dy * k)}

FOG_C = np.array([226, 231, 234], np.float32)
def fog(img, plan):
    """a cidade continua até a borda e some numa névoa com bordas de nuvem (em vez de terminar no vazio)"""
    H, W = img.shape[:2]; R, M = plan['radius_m'], plan['margin_m']; K = plan['K']; x0, y0 = plan['origin']; fi, fo = plan['fog']
    sx = np.arange(W, dtype=np.float32)[None] + x0; sy = np.arange(H, dtype=np.float32)[:, None] + y0
    a = sx / (K * 0.7071); b = -sy / (K * 0.3536); d = np.maximum(np.abs((a + b) / 2), np.abs((b - a) / 2))   # distância no chão (quadrado)
    t = np.clip((d - (R + fi * M)) / ((fo - fi) * M), 0, 1)
    rng = np.random.default_rng(7); n = None
    for cell, w in ((260, 0.6), (110, 0.3), (48, 0.1)):   # nuvens: ruído suave em 3 escalas
        z = Image.fromarray((rng.random((H // cell + 2, W // cell + 2)) * 255).astype(np.uint8)).resize((W + 2 * cell, H + 2 * cell), Image.BICUBIC)
        z = np.asarray(z, np.float32)[cell:cell + H, cell:cell + W] / 255; n = z * w if n is None else n + z * w
    al = np.clip(t * 1.25 + (n - 0.5) * 0.9 * np.sin(np.pi * np.clip(t, 0, 1)), 0, 1)
    al = al * al * (3 - 2 * al)
    puff = 1 + 0.035 * (n - 0.5)[..., None] * 2          # leve volume na névoa
    return img * (1 - al[..., None]) + FOG_C * puff * al[..., None]

def main():
    D = Path(sys.argv[1]); plan = json.loads((D / 'plan.json').read_text()); T, O = plan['tile'], plan['overlap']; W, H = plan['size']
    acc = np.zeros((H + T, W + T, 3), np.float32); wsum = np.zeros((H + T, W + T, 1), np.float32)
    base = Image.open(D / 'base.png').convert('RGB'); qa = {}
    ramp = np.minimum(1, (np.arange(T) + 1) / O); m1 = np.minimum(ramp, ramp[::-1]); mask = np.minimum.outer(m1, m1)[..., None].astype(np.float32)
    for t in plan['tiles']:
        p = D / 'gen' / f"{t['id']}.png"
        if t.get('fog') and not p.exists(): qa[t['id']] = {'nevoa': True}
        if p.exists():
            g = Image.open(p).convert('RGB').resize((T, T), Image.LANCZOS)
            bt = Image.open(D / 'tiles' / f"{t['id']}.png").convert('RGB')
            g, info = fit(bt, g, T); qa[t['id']] = info
        else:
            g = Image.open(D / 'tiles' / f"{t['id']}.png").convert('RGB'); qa.setdefault(t['id'], {'faltando': True})
        x, y = t['x'], t['y']; ga = np.asarray(g, np.float32)
        have = wsum[y:y + T, x:x + T, 0] > 0.05
        if have.sum() > 4000:   # casa a cor com o que já está no mapa (média e desvio por canal, ganho limitado)
            cur = acc[y:y + T, x:x + T][have] / wsum[y:y + T, x:x + T][have]; new_ = ga[have]
            gain = np.clip(cur.std(0) / (new_.std(0) + 1e-6), 0.85, 1.18); off = cur.mean(0) - new_.mean(0) * gain
            ga = (ga * gain + off).clip(0, 255); qa[t['id']]['cor'] = [round(float(v), 2) for v in gain]
        acc[y:y + T, x:x + T] += ga * mask; wsum[y:y + T, x:x + T] += mask
    img = (acc / np.maximum(wsum, 1e-6))[:H, :W]
    if plan.get('margin_m'): img = fog(img, plan)
    img = img.clip(0, 255).astype(np.uint8)
    out = Image.fromarray(img); out.save(D / 'tiny.png'); out.save(D / 'tiny.jpg', quality=88)
    (D / 'qa.json').write_text(json.dumps(qa, indent=1))
    name = plan.get('name', '').split(',')[0]
    (D / 'index.html').write_text(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Tiny {name}</title><style>html,body{{margin:0;height:100%;background:#e2e7ea;overflow:hidden;font:15px system-ui}}
#v{{position:absolute;inset:0;cursor:grab}}#v img{{position:absolute;transform-origin:0 0;image-rendering:pixelated;user-select:none}}
h1{{position:fixed;left:16px;top:12px;margin:0;font-size:18px;background:#fffd;padding:6px 10px;border-radius:8px}}</style>
<h1>Tiny {name}</h1><div id=v><img id=i src="tiny.jpg" draggable=false></div><script>
const v=document.getElementById('v'),i=document.getElementById('i');let s=1,x=0,y=0,d=null;
const ap=()=>i.style.transform='translate('+x+'px,'+y+'px) scale('+s+')';
i.onload=()=>{{s=Math.max(innerWidth/i.naturalWidth,innerHeight/i.naturalHeight);x=(innerWidth-i.naturalWidth*s)/2;y=(innerHeight-i.naturalHeight*s)/2;ap()}};
v.onwheel=e=>{{e.preventDefault();const k=Math.exp(-e.deltaY*0.0015),n=Math.min(4,Math.max(0.1,s*k));x=e.clientX-(e.clientX-x)*n/s;y=e.clientY-(e.clientY-y)*n/s;s=n;ap()}};
v.onpointerdown=e=>{{d=[e.clientX-x,e.clientY-y];v.setPointerCapture(e.pointerId)}};v.onpointermove=e=>{{if(d){{x=e.clientX-d[0];y=e.clientY-d[1];ap()}}}};v.onpointerup=()=>d=null;
</script>""")
    print(json.dumps({'tiny': str(D / 'tiny.png'), 'gerados': sum(1 for v in qa.values() if 'corr_base' in v), 'total': sum(1 for v in qa.values() if 'nevoa' not in v),
                      'corr_media': round(float(np.mean([v['corr_base'] for v in qa.values() if 'corr_base' in v] or [0])), 3)}))
if __name__ == '__main__': main()

