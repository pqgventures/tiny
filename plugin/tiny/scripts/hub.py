#!/usr/bin/env python3
"""tiny hub: talk to Tiny World, the shared map of Tiny cities.
  hub.py where "<place, city>"                                   does this place start a city, grow one, or already exist?
  hub.py cities
  hub.py publish <tiny_folder> [--name "Place"] [--by "you"]     upload, wait for the check, print the link
  hub.py next <city> <work_folder> [--by "you"] [--near "place"]  get the next tile to paint (base + style images + prompt)
  hub.py submit <work_folder> <painted.png>                      send it back; prints accepted or why not, and your page
  hub.py me                                                      the page with every tile you painted
The address comes from TINY_WORLD (Tiny World's own /llms.txt tells you which one to set)."""
import io, json, os, sys, time, zipfile, urllib.request, urllib.parse, urllib.error
from pathlib import Path
HUB = (os.environ.get('TINY_WORLD') or os.environ.get('TINY_HUB') or '').rstrip('/')
UA = {'User-Agent': 'tiny-plugin/0.3 (+https://github.com/pqgventures/tiny)'}

def call(path, data=None, ctype='application/json', timeout=180):
    if not HUB: return {'error': 'Tiny World address not set. Set TINY_WORLD=<address> (it is in the llms.txt you were given).'}
    req = urllib.request.Request(HUB + path, data=data, headers=dict(UA, **({'Content-Type': ctype} if data is not None else {})))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read())
        except Exception: return {'error': f'Tiny World answered {e.code}'}
    except Exception as e: return {'error': f'could not reach Tiny World ({e})'}
def me():
    """a random id kept on this computer, so your tiles stay yours without an account"""
    f = Path.home() / '.tiny' / 'id'
    if not f.exists(): f.parent.mkdir(exist_ok=True); f.write_text(__import__('secrets').token_urlsafe(16))
    return f.read_text().strip()
def opt(name, default=''):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv) else default
def out(o): print(json.dumps(o, ensure_ascii=False))

def publish(folder):
    from PIL import Image
    D = Path(folder).expanduser(); plan = json.loads((D / 'plan.json').read_text()); qa = json.loads((D / 'qa.json').read_text()) if (D / 'qa.json').exists() else {}
    buf = io.BytesIO(); n = 0
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
        z.writestr('plan.json', json.dumps(plan, ensure_ascii=False))
        for t in plan['tiles']:
            f = D / 'gen' / qa.get(t['id'], {}).get('file', f"{t['id']}.png")      # the version stitch.py kept
            if not f.exists(): f = D / 'gen' / f"{t['id']}.png"
            if not f.exists(): continue
            b = io.BytesIO(); Image.open(f).convert('RGB').resize((1024, 1024), Image.LANCZOS).save(b, 'JPEG', quality=92); z.writestr(f"gen/{t['id']}.jpg", b.getvalue()); n += 1
    need = sum(1 for t in plan['tiles'] if not t.get('fog'))
    if n < need: return out({'error': f'{need - n} of {need} tiles are not painted yet. Finish the Tiny first.'})
    q = urllib.parse.urlencode({'name': opt('--name') or plan.get('place', '').split(',')[0], 'by': opt('--by')})
    r = call('/api/publish?' + q, buf.getvalue(), 'application/zip', 600)
    if r.get('error'): return out(r)
    for _ in range(40):                      # Tiny World redraws the place from OpenStreetMap and checks the painting against it
        time.sleep(10); s = call(r['status_url'])
        if s.get('status') in ('live', 'rejected'): return out({'status': s['status'], 'why': s.get('why'), 'city': r.get('city_name'), 'url': s['url']})
    out({'status': 'checking', 'url': r['url'], 'note': 'still checking; the link goes live when it passes'})

def nxt(city, work):
    W = Path(work).expanduser(); W.mkdir(parents=True, exist_ok=True)
    r = call('/api/jobs/next', json.dumps({'city': city, 'who': opt('--by'), 'painter': me(), 'near': opt('--near')}).encode())
    if r.get('error') or not r.get('tile'): return out(r if r.get('error') else {'done': True, 'note': 'nothing left to paint in this city right now'})
    for old in W.glob('[0-9]_*'): old.unlink()
    paths = []
    for i, u in enumerate(r['images']):
        p = W / f"{i + 1}_{u.rsplit('/', 1)[1].lstrip('-')}"
        with urllib.request.urlopen(urllib.request.Request(u if u.startswith('http') else HUB + u, headers=UA), timeout=120) as f: p.write_bytes(f.read())
        paths.append(str(p))
    (W / 'prompt.txt').write_text(r['prompt']); (W / 'job.json').write_text(json.dumps({k: r[k] for k in ('city', 'tile', 'lease')}))
    out({'tile': r['tile'], 'images_in_order': paths, 'prompt_file': str(W / 'prompt.txt'), 'minutes': r['minutes'], 'left': r['left']} | ({'km_from_there': r['km_from_there']} if 'km_from_there' in r else {}))

def submit(work, png):
    j = json.loads((Path(work).expanduser() / 'job.json').read_text())
    out(call('/api/jobs/submit?' + urllib.parse.urlencode(j), Path(png).expanduser().read_bytes(), 'image/png', 300))

if __name__ == '__main__':
    a = [x for x in sys.argv[1:]]
    if not a: print(__doc__)
    elif a[0] == 'cities': out(call('/api/cities'))
    elif a[0] == 'where': out(call('/api/where?' + urllib.parse.urlencode({'q': a[1], 'radius': opt('--radius', '260')})))
    elif a[0] == 'publish': publish(a[1])
    elif a[0] == 'next': nxt(a[1], a[2])
    elif a[0] == 'submit': submit(a[1], a[2])
    elif a[0] == 'me': out({'your_page': HUB + '/me/' + me()})
    else: print(__doc__)
