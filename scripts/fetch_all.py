# -*- coding: utf-8 -*-
"""批量下载：6 个对比场景 × 58 个配方 + 全部作者样片（960px）。"""
import json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
OUT = os.path.join(BASE, 'imgs960')
SCENES = ['marathon', 'peace-memorial', 'redbud', 'rosslyn-dusk', 'misty-mountains', 'moss']
UA = {'User-Agent': 'Mozilla/5.0'}
os.makedirs(OUT, exist_ok=True)

data = json.load(open(os.path.join(BASE, 'search.json'), encoding='utf-8'))
by_slug = {r['slug']: r for r in data['results']}
imap = json.load(open(os.path.join(BASE, 'imgmap.json'), encoding='utf-8'))

doc_slugs = []
for cid, slug, files in imap['mapping']:
    if slug not in doc_slugs:
        doc_slugs.append(slug)
print('配方数', len(doc_slugs))

tasks = []
manifest = {}
for slug in doc_slugs:
    r = by_slug[slug]
    entry = {'name': r['recipeName'], 'author': r['authorName'], 'cmp': {}, 'samples': []}
    cmap = {}
    for c in (r.get('comparisonImages') or []):
        key = c['preparedObjectKey'].split('/')[-1].rsplit('.', 1)[0]
        cmap[key.replace('_', '-')] = c
    for sc in SCENES:
        c = cmap.get(sc)
        if not c:
            continue
        fn = '%s__cmp__%s.jpg' % (slug, sc)
        entry['cmp'][sc] = fn
        tasks.append((c['assetUrls']['960'], os.path.join(OUT, fn)))
    for i, s in enumerate((r.get('sampleImages') or [])):
        fn = '%s__s%02d.jpg' % (slug, i + 1)
        entry['samples'].append({
            'file': fn,
            'camera': s.get('camera'), 'lens': s.get('lens'),
            'shutter': s.get('shutterSpeed'), 'aperture': s.get('aperture'),
            'focal': s.get('focalLength'), 'iso': s.get('iso'),
        })
        tasks.append((s['assetUrls']['960'], os.path.join(OUT, fn)))
    manifest[slug] = entry

print('图片总数', len(tasks))
json.dump(manifest, open(os.path.join(BASE, 'imgs960.json'), 'w', encoding='utf-8'), ensure_ascii=False)


def dl(t):
    url, path = t
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return 0
    try:
        b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    except Exception as e:
        print('SKIP', os.path.basename(path), e)
        return 0
    open(path, 'wb').write(b)
    return len(b)


if '--download' in sys.argv:
    tot = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        for n in ex.map(dl, tasks):
            tot += n
    print('下载 %.1f MB' % (tot / 1048576))
else:
    print('（预演）')
