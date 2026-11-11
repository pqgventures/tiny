#!/usr/bin/env python3
"""tiny paint_api: paint tiles with an image model over an API, for agents that have no image tool of their own.
  paint_api.py <tiny_folder> [parallel=2]     paints every missing tile of a Tiny (gen/<id>.png) and restitches
  paint_api.py --job <work_folder>            paints the tile fetched by "hub.py next" -> <work_folder>/painted.png
Needs OPENROUTER_API_KEY. Model: TINY_MODEL (default google/gemini-nano-banana-2.1). Prints what each tile cost."""
import base64, io, json, os, subprocess, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
MODEL = os.environ.get('TINY_MODEL', 'google/gemini-nano-banana-2.1'); S = Path(__file__).resolve().parent

def b64(p):
    im = Image.open(p).convert('RGB'); b = io.BytesIO(); im.save(b, 'JPEG', quality=93)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
def paint(images, prompt):
    """images: paths in order (the last one is the base to redraw) -> (PIL image, cost in US$)"""
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key: raise SystemExit('Set OPENROUTER_API_KEY (openrouter.ai/keys) to paint without a built-in image tool.')
    body = {'model': MODEL, 'messages': [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': b64(p)}} for p in images] + [{'type': 'text', 'text': prompt}]}],
            'modalities': ['image', 'text'], 'image_config': {'aspect_ratio': '1:1', 'image_size': '1K'}, 'usage': {'include': True}}
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', json.dumps(body).encode(), {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as r: d = json.loads(r.read())
    except urllib.error.HTTPError as e: raise RuntimeError(f'{e.code}: {e.read()[:200].decode(errors="replace")}')
    imgs = ((d.get('choices') or [{}])[0].get('message') or {}).get('images') or []
    if not imgs: raise RuntimeError('the model returned no image: ' + json.dumps(d)[:200])
    return Image.open(io.BytesIO(base64.b64decode(imgs[0]['image_url']['url'].split(',', 1)[1]))).convert('RGB'), float((d.get('usage') or {}).get('cost') or 0)

def tiny(folder, par):
    D = Path(folder).expanduser(); plan = json.loads((D / 'plan.json').read_text()); (D / 'gen').mkdir(exist_ok=True)
    prompt = ((D / 'prompt.txt') if (D / 'prompt.txt').exists() else (S / 'prompt.txt')).read_text()
    todo = [t['id'] for t in plan['tiles'] if not t.get('fog') and not (D / 'gen' / f"{t['id']}.png").exists()]
    def one(i):
        try:
            im, cost = paint([D / 'tiles' / f'{i}.png'], prompt); im.save(D / 'gen' / f'{i}.png'); print(json.dumps({'tile': i, 'ok': True, 'usd': round(cost, 4)}), flush=True); return cost
        except Exception as e: print(json.dumps({'tile': i, 'ok': False, 'error': str(e)[:200]}), flush=True); return 0
    with ThreadPoolExecutor(par) as ex: total = sum(ex.map(one, todo))
    subprocess.run([sys.executable, str(S / 'stitch.py'), str(D)])
    print(json.dumps({'painted': len(todo), 'usd': round(total, 3)}))

def job(work):
    W = Path(work).expanduser(); images = sorted(W.glob('[0-9]_*'))
    im, cost = paint(images, (W / 'prompt.txt').read_text()); im.save(W / 'painted.png')
    print(json.dumps({'painted': str(W / 'painted.png'), 'usd': round(cost, 4)}))

if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--job': job(sys.argv[2])
    elif len(sys.argv) >= 2: tiny(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2)
    else: print(__doc__)
