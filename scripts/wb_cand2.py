# -*- coding: utf-8 -*-
"""夜间档候选细看：白平衡原文取值 + 作者原话 + 已有补充说明 + 与优化版的风格距离。"""
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

plan = {}
for m in re.finditer(r'<div class="oslot" id="(oC\d-\d)">(.*?)(?=<div class="oslot"|\Z)', h, re.S):
    b = m.group(2)
    nm = re.search(r'<span class="osname">(.*?)</span>', b)
    au = re.search(r'<span class="osauth">(.*?)</span>', b)
    if nm and au:
        r = by_key.get((nm.group(1).strip().lower(), au.group(1).strip().lower()))
        if r:
            plan[m.group(1)] = (nm.group(1).strip(), au.group(1).strip(), r)

notes = {}
tags = {}
for m in re.finditer(r'<div class="card" id="r-([^"]+)">', h):
    nxt = h.find('<div class="card" id="r-', m.end())
    blk = h[m.start():nxt if nxt > 0 else m.start() + 25000]
    nm = re.search(r'<span class="cname">(.*?)</span>', blk)
    au = re.search(r'<span class="cauth">(.*?)</span>', blk)
    tg = re.findall(r'<div class="tags">(.*?)</div>', blk, re.S)
    rows = re.findall(r'<span class="mk">(.*?)</span><span class="mv[^"]*">(.*?)</span>', blk, re.S)
    if nm and au:
        k = (nm.group(1).strip().lower(), au.group(1).strip().lower())
        notes[k] = dict((re.sub(r'<[^>]+>', '', a).strip(),
                         re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', b)).strip()) for a, b in rows)
        tags[k] = re.findall(r'<span>(.*?)</span>', tg[0]) if tg else []

WANT = [('The Night Mayor', 'Burak Yilmaz'), ('Cinematic Tundra', 'Basi Torre'),
        ('OM-3 Tokyo-Wetzlar', 'James Bloomer'), ('Cool Spring', 'Ian Will'),
        ('CityEurope', 'Robson Cabanas'), ('Kinda Portra', 'Ian Will'),
        ('Filmed', 'George Holden'), ('Fuji Classic Neg', 'ibd')]

for n, a in WANT:
    k = (n.lower(), a.lower())
    r = by_key.get(k)
    if not r:
        print('## %s / %s 不在库里\n' % (n, a))
        continue
    v = [r.get(c, 0) or 0 for c in CH]
    near = sorted((sum(abs(x - y) for x, y in zip(v, [pr.get(c, 0) or 0 for c in CH]))
                   + 2 * sum(abs(x - y) for x, y in zip(
                       [r.get('shadows', 0) or 0, r.get('midtones', 0) or 0, r.get('highlights', 0) or 0,
                        r.get('contrast', 0) or 0, r.get('sharpness', 0) or 0],
                       [pr.get('shadows', 0) or 0, pr.get('midtones', 0) or 0, pr.get('highlights', 0) or 0,
                        pr.get('contrast', 0) or 0, pr.get('sharpness', 0) or 0])), kk, pn)
                  for kk, (pn, pa, pr) in plan.items())[:3]
    print('## %s / %s' % (n, a))
    print('   白平衡原文=%r 温度=%s | 标签=%s' % (r.get('whiteBalance2'), r.get('whiteBalanceTemperature'), tags.get(k)))
    print('   12色: ' + ' '.join('%s%+d' % (c[:2], r.get(c, 0) or 0) for c in CH))
    print('   曲线: Sh%+d Mid%+d Hi%+d 对比%+d 锐度%+d 曝光%+s' % (
        r.get('shadows') or 0, r.get('midtones') or 0, r.get('highlights') or 0,
        r.get('contrast') or 0, r.get('sharpness') or 0, r.get('exposureCompensation')))
    print('   原文: ' + ' '.join((r.get('description') or '').split())[:300])
    for kk in ['画面感觉', '影调', '适合', '避开', '提示']:
        if notes.get(k, {}).get(kk):
            print('   %s: %s' % (kk, notes[k][kk][:130]))
    print('   最像优化版: ' + ', '.join('%s(%.0f)' % (x[2][:20], x[0]) for x in near))
    print()

# 纯 Auto(保持暖色调关) 的候选（严格匹配本档设置）
print('=== 严格匹配（原生 Auto + 保持暖色调关）且未被占用 ===')
for k, v in by_key.items():
    if v.get('whiteBalance2') != 'Auto (Keep Warm Color Off)':
        continue
    if k not in notes:
        continue
    if k in {(pn.lower(), pa.lower()) for pn, pa, _ in plan.values()}:
        continue
    print('  %-26s %-16s %s' % (v['recipeName'][:26], v['authorName'][:16], '/'.join(tags.get(k, []))))
