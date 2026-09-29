# -*- coding: utf-8 -*-
"""C4 换配方选型：白平衡一致性 + 风格是否与优化版其它槽位同质化。

指标：
- 12 色轮绝对值差 + 影调曲线差 + 对比/锐度差 → 风格距离（越小越像）
- 卡片自带的三词标签（浓度 · 色偏 · 影调）完全相同 → 直接判同质
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
h = open(BASE + r'\app\base.html', encoding='utf-8').read()
recipes = json.load(open(BASE + r'\all_recipes.json', encoding='utf-8'))['results']
by_key = {(r['recipeName'].strip().lower(), r['authorName'].strip().lower()): r for r in recipes}
CH = ['yellow', 'orange', 'orangeRed', 'red', 'magenta', 'violet',
      'blue', 'blueCyan', 'cyan', 'greenCyan', 'green', 'yellowGreen']

# ---- 优化版已占用的 21 个槽位（含风格距离用的数值）----
plan = {}
for m in re.finditer(r'<div class="oslot" id="(oC\d-\d)">(.*?)(?=<div class="oslot"|\Z)', h, re.S):
    b = m.group(2)
    nm = re.search(r'<span class="osname">(.*?)</span>', b)
    au = re.search(r'<span class="osauth">(.*?)</span>', b)
    if not (nm and au):
        continue
    n_, a_ = nm.group(1).strip(), au.group(1).strip()
    r = by_key.get((n_.lower(), a_.lower()))
    if r:
        plan[m.group(1)] = (n_, a_, r)

# ---- 58 张卡：名字/作者/标签/12 色/曲线 ----
cards = {}
for m in re.finditer(r'<div class="card" id="r-([^"]+)">', h):
    nxt = h.find('<div class="card" id="r-', m.end())
    blk = h[m.start():nxt if nxt > 0 else m.start() + 25000]
    nm = re.search(r'<span class="cname">(.*?)</span>', blk)
    au = re.search(r'<span class="cauth">(.*?)</span>', blk)
    tg = re.findall(r'<div class="tags">(.*?)</div>', blk, re.S)
    tags = re.findall(r'<span>(.*?)</span>', tg[0]) if tg else []
    key = (nm.group(1).strip().lower(), au.group(1).strip().lower())
    row = by_key.get(key)
    if row:
        cards[key] = {'n': nm.group(1).strip(), 'a': au.group(1).strip(), 'tags': tags, 'r': row}


def vec(r):
    return [r.get(k, 0) or 0 for k in CH]


def curve(r):
    return [r.get('shadows', 0) or 0, r.get('midtones', 0) or 0, r.get('highlights', 0) or 0,
            r.get('contrast', 0) or 0, r.get('sharpness', 0) or 0]


def dist(x, y):
    v = sum(abs(a - b) for a, b in zip(vec(x), vec(y)))
    c = sum(abs(a - b) for a, b in zip(curve(x), curve(y)))
    return v + 2 * c


print('=== 优化版现有 21 个槽位（风格基准） ===')
for k, (n_, a_, r) in plan.items():
    tags = cards.get((n_.lower(), a_.lower()), {}).get('tags', [])
    print('  %-7s %-24s %-16s %s  曲线 Sh%+d Mid%+d Hi%+d 对比%+d | %s' % (
        k, n_[:24], a_[:16], '/'.join('%-3s' % t for t in tags)[:26],
        r.get('shadows', 0) or 0, r.get('midtones', 0) or 0, r.get('highlights', 0) or 0,
        r.get('contrast', 0) or 0, r.get('whiteBalance2')))

print()
print('=== 候选：原生 Auto / Auto(暖色调关)、未被优化版占用 ===')
used = {(n_.lower(), a_.lower()) for n_, a_, _ in plan.values()}
rows = []
for key, c in cards.items():
    r = c['r']
    wb2 = r.get('whiteBalance2') or ''
    if wb2 not in ('Auto', 'Auto (Keep Warm Color Off)'):
        continue
    if key in used:
        continue
    near = sorted(((dist(r, pr), k, pn) for k, (pn, pa, pr) in plan.items()))[:2]
    sat = sum(vec(r))
    rows.append({'c': c, 'r': r, 'near': near, 'sat': sat, 'wb2': wb2})

rows.sort(key=lambda x: -x['near'][0][0])
for x in rows:
    r, c = x['r'], x['c']
    print('  %-24s %-15s [%s] Sh%+d Hi%+d 对比%+d 锐%+d 曝光%s 色轮和%+d | 最像: %s(%.0f) %s(%.0f)' % (
        c['n'][:24], c['a'][:15], '/'.join(c['tags'])[:24],
        r.get('shadows', 0) or 0, r.get('highlights', 0) or 0, r.get('contrast', 0) or 0,
        r.get('sharpness', 0) or 0, r.get('exposureCompensation'), x['sat'],
        x['near'][0][2][:18], x['near'][0][0], x['near'][1][2][:18], x['near'][1][0]))
print()
print('候选数', len(rows))
