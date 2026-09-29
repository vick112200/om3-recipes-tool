# -*- coding: utf-8 -*-
"""把文档里的卡片映射到站点配方，并下载 1200px 的对比场景 + 作者样片。"""
import json, re, os, sys, urllib.request, hashlib
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
DOC = r'C:\Users\82302\Desktop\OM-3色彩配方手册.html'
OUT = r'C:\Users\82302\AppData\Local\Temp\apk\assets\images'
SCENES = ['marathon', 'peace-memorial']
MAX_SAMPLE = 3
UA = {'User-Agent': 'Mozilla/5.0'}

os.makedirs(OUT, exist_ok=True)
data = json.load(open(os.path.join(BASE, 'search.json'), encoding='utf-8'))
recipes = data['results']


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


by_slug = {r['slug']: r for r in recipes}
by_norm = {}
for r in recipes:
    by_norm.setdefault(norm(r['slug']), r)
    # 也允许去掉作者前缀后的名字匹配
    if '_' in r['slug']:
        by_norm.setdefault(norm(r['slug'].split('_', 1)[1]), r)


def match(cid):
    if cid in by_slug:
        return by_slug[cid]
    n = norm(cid)
    if n in by_norm:
        return by_norm[n]
    for k, v in by_norm.items():
        if k.startswith(n) or n.startswith(k):
            return v
    return None


h = open(DOC, encoding='utf-8').read()
ids = []
for m in re.finditer(r'<div class="card" id="(r-[^"]+)">', h):
    ids.append(m.group(1)[2:])
for m in re.finditer(r'<div class="oslot" id="(oC[^"]+)">', h):
    seg = h[m.start():m.start() + 4000]
    nm = re.search(r'<span class="osname">(.*?)</span>', seg).group(1)
    au = re.search(r'<span class="osauth">(.*?)</span>', seg).group(1)
    ids.append((m.group(1), nm, au))

# 槽位从原版卡片名反查 slug
card_by_name = {}
for c in recipes:
    card_by_name.setdefault((c['recipeName'].strip().lower(), c['authorName'].strip().lower()), c)

tasks, mapping = [], []
seen_slug = {}

def add(slug, recipe, tag):
    if slug in seen_slug:
        return seen_slug[slug]
    files = {}
    cmp_imgs = {c['preparedObjectKey'].split('/')[-1].rsplit('.', 1)[0].replace('_', '-'): c
                for c in (recipe.get('comparisonImages') or [])}
    for i, sc in enumerate(SCENES):
        c = cmp_imgs.get(sc)
        if c:
            fn = '%s_cmp%d.jpg' % (slug, i + 1)
            files['cmp%d' % (i + 1)] = fn
            tasks.append((c['assetUrls']['1200'], os.path.join(OUT, fn)))
    for i, s in enumerate((recipe.get('sampleImages') or [])[:MAX_SAMPLE]):
        fn = '%s_s%d.jpg' % (slug, i + 1)
        files['s%d' % (i + 1)] = fn
        tasks.append((s['assetUrls']['1200'], os.path.join(OUT, fn)))
    seen_slug[slug] = files
    return files

unmatched = []
for cid in ids:
    if isinstance(cid, tuple):
        continue
    r = match(cid)
    if not r:
        unmatched.append(cid)
        continue
    mapping.append((cid, r['slug'], add(r['slug'], r, cid)))

print('原版卡片 %d 张：匹配 %d，未匹配 %d' % (len([i for i in ids if isinstance(i, str)]),
                                       len(mapping), len(unmatched)))
if unmatched:
    print('未匹配:', unmatched)

# 优化版槽位
slot_unmatched = []
for sid, nm, au in [i for i in ids if isinstance(i, tuple)]:
    key = (nm.strip().lower(), au.strip().lower())
    r = card_by_name.get(key)
    if not r:
        slot_unmatched.append((sid, nm, au))
        continue
    add(r['slug'], r, sid)

print('优化版槽位未匹配:', slot_unmatched)
print('需要下载的图片总数:', len(tasks))
tot_bytes = 0
unseen = {u for u, _ in tasks}
print('唯一 URL:', len(unseen))


def dl(t):
    url, path = t
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return os.path.getsize(path), 0
    req = urllib.request.Request(url, headers=UA)
    b = urllib.request.urlopen(req, timeout=40).read()
    open(path, 'wb').write(b)
    return len(b), 1


if '--download' in sys.argv:
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for size, new in ex.map(dl, tasks):
            tot_bytes += size
            done += new
    print('下载完成，新增 %d 个文件，共 %.1f MB' % (done, tot_bytes / 1048576))
else:
    print('（未加 --download，仅预演）')

json.dump({'mapping': mapping, 'seen': seen_slug}, open(os.path.join(BASE, 'imgmap.json'), 'w', encoding='utf-8'),
          ensure_ascii=False)
