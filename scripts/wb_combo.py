# -*- coding: utf-8 -*-
"""C4 四格组合的风格多样性打分：两两风格距离 + 与优化版其它 20 格的最近距离。"""
import itertools
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
CV = ['shadows', 'midtones', 'highlights', 'contrast', 'sharpness']

plan = {}
for m in re.finditer(r'<div class="oslot" id="(oC\d-\d)">(.*?)(?=<div class="oslot"|\Z)', h, re.S):
    b = m.group(2)
    nm = re.search(r'<span class="osname">(.*?)</span>', b)
    au = re.search(r'<span class="osauth">(.*?)</span>', b)
    if nm and au:
        k = (nm.group(1).strip().lower(), au.group(1).strip().lower())
        if k in by_key:
            plan[m.group(1)] = k


def d(x, y):
    rx, ry = by_key[x], by_key[y]
    v = sum(abs((rx.get(c) or 0) - (ry.get(c) or 0)) for c in CH)
    cv = 2 * sum(abs((rx.get(c) or 0) - (ry.get(c) or 0)) for c in CV)
    return v + cv


CAND = {
    'City Look': ('city look', 'giuseppe ardica'),
    'Q116': ('q116', 'robsoncabanas'),
    'The Night Mayor': ('the night mayor', 'burak yilmaz'),
    'Cool Spring': ('cool spring', 'ian will'),
    'CityEurope': ('cityeurope', 'robson cabanas'),
    'Fuji Eterna': ('fuji eterna', 'ibd'),
    'Estill Springs Green': ('estill springs green', 'kaleigh whitaker'),
    'OM-3 Tokyo-Wetzlar': ('om-3 tokyo-wetzlar', 'james bloomer'),
    'Cinematic Tundra': ('cinematic tundra', 'basi torre'),
    'PNW': ('pnw', 'ian will'),
    'Default - 4': ('default - 4', 'om system'),
    'Nostalgic Summer': ('nostalgic summer', 'kyler steele'),
}
print('=== 候选两两风格距离（越大越不像） ===')
names = list(CAND)
print('%-22s' % '' + ''.join('%6s' % n[:5] for n in names))
for a in names:
    print('%-22s' % a[:22] + ''.join('%6d' % d(CAND[a], CAND[b]) for b in names))

others = {k: v for k, v in plan.items() if not k.startswith('oC4')}
print()
print('=== 候选 vs 优化版其它 16 格：最近距离（越大越不容易同质） ===')
for n in names:
    near = sorted((d(CAND[n], v), k) for k, v in others.items())
    print('  %-22s 最近: %-8s %.0f | 次近: %-8s %.0f' % (n, near[0][1], near[0][0], near[1][1], near[1][0]))

print()
print('=== 四格组合打分（固定 City Look + Q116） ===')
keep = ['City Look', 'Q116']
rest = [n for n in names if n not in keep]
for a, b in itertools.combinations(rest, 2):
    four = keep + [a, b]
    pd = [d(CAND[x], CAND[y]) for x, y in itertools.combinations(four, 2)]
    outside = min(d(CAND[x], v) for x in four for v in others.values())
    print('  %-20s + %-20s 组内最小两两 %3d 平均 %3d | 与其它档最近 %3d' % (
        a[:20], b[:20], min(pd), sum(pd) / len(pd), outside))
