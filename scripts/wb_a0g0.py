# -*- coding: utf-8 -*-
"""用文档里权威的白平衡签名（IDX.sl）重筛 C4 候选：
只有签名 = A0 G0 的配方才能挂在本档（Auto A0 G0）上零位移。
再按风格距离挑最不像的两格。
"""
import itertools
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
h = open(BASE + r'\app\base.html', encoding='utf-8').read()
recs = json.load(open(BASE + r'\all_recipes.json', encoding='utf-8'))['results']
by_key = {(r['recipeName'].strip().lower(), r['authorName'].strip().lower()): r for r in recs}
CH = ['yellow', 'orange', 'orangeRed', 'red', 'magenta', 'violet',
      'blue', 'blueCyan', 'cyan', 'greenCyan', 'green', 'yellowGreen']
CV = ['shadows', 'midtones', 'highlights', 'contrast', 'sharpness']

IDX, _ = json.JSONDecoder().raw_decode(h, h.find('var IDX=') + len('var IDX='))
sig = {(e['n'].strip().lower(), e['a'].strip().lower()): e['sl'] for e in IDX}
# 原版 C1 档下的卡片也是 A0 G0
c1 = set()
for m in re.finditer(r'<div class="card" id="r-([^"]+)">', h):
    nxt = h.find('<div class="card" id="r-', m.end())
    blk = h[m.start():nxt if nxt > 0 else m.start() + 25000]
    nm = re.search(r'<span class="cname">(.*?)</span>', blk)
    au = re.search(r'<span class="cauth">(.*?)</span>', blk)
    if nm and au and sig.get((nm.group(1).strip().lower(), au.group(1).strip().lower()), '').startswith('C1'):
        c1.add((nm.group(1).strip().lower(), au.group(1).strip().lower()))

plan = {}
for m in re.finditer(r'<div class="oslot" id="(oC\d-\d)">(.*?)(?=<div class="oslot"|\Z)', h, re.S):
    b = m.group(2)
    nm = re.search(r'<span class="osname">(.*?)</span>', b)
    au = re.search(r'<span class="osauth">(.*?)</span>', b)
    if nm and au:
        k = (nm.group(1).strip().lower(), au.group(1).strip().lower())
        if k in by_key:
            plan[m.group(1)] = k
used = set(plan.values())
solo = {('the night mayor', 'burak yilmaz'), ('bluegill teal', '')}


def d(x, y):
    rx, ry = by_key[x], by_key[y]
    return (sum(abs((rx.get(c) or 0) - (ry.get(c) or 0)) for c in CH)
            + 2 * sum(abs((rx.get(c) or 0) - (ry.get(c) or 0)) for c in CV))


cards = {}
for m in re.finditer(r'<div class="card" id="r-([^"]+)">', h):
    nxt = h.find('<div class="card" id="r-', m.end())
    blk = h[m.start():nxt if nxt > 0 else m.start() + 25000]
    nm = re.search(r'<span class="cname">(.*?)</span>', blk)
    au = re.search(r'<span class="cauth">(.*?)</span>', blk)
    tg = re.findall(r'<div class="tags">(.*?)</div>', blk, re.S)
    if nm and au:
        k = (nm.group(1).strip().lower(), au.group(1).strip().lower())
        cards[k] = {'n': nm.group(1).strip(), 'a': au.group(1).strip(),
                    'tags': re.findall(r'<span>(.*?)</span>', tg[0]) if tg else []}

pool = [k for k in cards if (sig.get(k, '') == '备选池 · A0 G0' or k in c1)]
print('A0 G0 签名且未被优化版占用、也不在单独占档名单里的卡：')
rows = []
for k in pool:
    if k in used or k in solo:
        continue
    r = by_key[k]
    near = sorted((d(k, v), kk) for kk, v in plan.items())
    c4keep = [('city look', 'giuseppe ardica'), ('q116', 'robsoncabanas')]
    d_keep = min(d(k, x) for x in c4keep)
    rows.append((k, r, near, d_keep))
rows.sort(key=lambda x: -min(x[2][1][0], 999) if False else -x[3])
for k, r, near, dk in sorted(rows, key=lambda x: -x[3]):
    print('  %-24s %-16s [%s] Sh%+d Mid%+d Hi%+d 对比%+d 锐%+d 曝光%s | 与 C4 保留两格最近 %3d | 全表最近 %s(%d)' % (
        cards[k]['n'][:24], cards[k]['a'][:16], '/'.join(cards[k]['tags'])[:22],
        r.get('shadows') or 0, r.get('midtones') or 0, r.get('highlights') or 0,
        r.get('contrast') or 0, r.get('sharpness') or 0, r.get('exposureCompensation'),
        dk, near[0][1], near[0][0]))
print()
print('（单独占档名单里的 %s 已排除）' % ', '.join('The Night Mayor', ))
print()
print('=== 若只保留 City Look + Q116，剩下两格的最优搭配 ===')
names = [x[0] for x in rows]
keep = [('city look', 'giuseppe ardica'), ('q116', 'robsoncabanas')]
best = []
for a, b in itertools.combinations(names, 2):
    four = keep + [a, b]
    pd = [d(x, y) for x, y in itertools.combinations(four, 2)]
    outside = min(d(x, v) for x in four for v in plan.values() if x not in keep)
    best.append((min(pd), sum(pd) / len(pd), outside, a, b))
best.sort(reverse=True)
for mn, avg, out, a, b in best[:10]:
    print('  %-22s + %-22s 组内最小 %3d 平均 %3d | 与其它档最近 %3d' % (
        cards[a]['n'][:22], cards[b]['n'][:22], mn, avg, out))
