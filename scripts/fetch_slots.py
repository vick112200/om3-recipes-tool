# -*- coding: utf-8 -*-
"""补齐优化版槽位用到、但原版没有卡片的配方图片。"""
import json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
OUT = os.path.join(BASE, 'imgs960')
SCENES = ['marathon', 'peace-memorial', 'redbud', 'rosslyn-dusk', 'misty-mountains', 'moss']
UA = {'User-Agent': 'Mozilla/5.0'}

man = json.load(open(os.path.join(BASE, 'imgs960.json'), encoding='utf-8'))
rs = json.load(open(os.path.join(BASE, 'search.json'), encoding='utf-8'))['results']
by = {r['slug']: r for r in rs}
name2slug = {}
for r in rs:
    name2slug.setdefault((r['recipeName'].strip().lower(), r['authorName'].strip().lower()), r['slug'])

h = open(r'C:\Users\82302\Desktop\OM-3色彩配方手册.html', encoding='utf-8').read()
need = []
for m in re.finditer(r'<div class="oslot" id="(oC[^"]+)">', h):
    blk = h[m.start():m.start() + 4000]
    nm = re.search(r'<span class="osname">(.*?)</span>', blk)
    au = re.search(r'class="osauth">(.*?)</span>', blk)
    if not (nm and au):
        continue
    s = name2slug.get((nm.group(1).strip().lower(), au.group(1).strip().lower()))
    if s and s not in man and s not in need:
        need.append(s)
print('槽位缺失配方:', need)

tasks = []
for slug in need:
    r = by[slug]
    e = {'name': r['recipeName'], 'author': r['authorName'], 'cmp': {}, 'samples': []}
    cmap = {}
    for c in (r.get('comparisonImages') or []):
        k = c['preparedObjectKey'].split('/')[-1].rsplit('.', 1)[0].replace('_', '-')
        cmap[k] = c
    for sc in SCENES:
        c = cmap.get(sc)
        if not c:
            continue
        fn = '%s__cmp__%s.jpg' % (slug, sc)
        e['cmp'][sc] = fn
        tasks.append((c['assetUrls']['960'], os.path.join(OUT, fn)))
    for i, s in enumerate(r.get('sampleImages') or []):
        fn = '%s__s%02d.jpg' % (slug, i + 1)
        e['samples'].append({'file': fn, 'camera': s.get('camera'), 'lens': s.get('lens'),
                             'shutter': s.get('shutterSpeed'), 'aperture': s.get('aperture'),
                             'focal': s.get('focalLength'), 'iso': s.get('iso')})
        tasks.append((s['assetUrls']['960'], os.path.join(OUT, fn)))
    man[slug] = e


def dl(t):
    u, p = t
    if os.path.exists(p):
        return 0
    try:
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
    except Exception as ex:
        print('SKIP', os.path.basename(p), ex)
        return 0
    open(p, 'wb').write(b)
    return len(b)


if tasks:
    with ThreadPoolExecutor(max_workers=8) as ex:
        tot = sum(ex.map(dl, tasks))
    print('补下 %d 张 %.1f MB' % (len(tasks), tot / 1048576))

json.dump(man, open(os.path.join(BASE, 'imgs960.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('manifest 配方数', len(man))
