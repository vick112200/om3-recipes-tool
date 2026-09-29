# -*- coding: utf-8 -*-
"""夜景档（优化版 C4）配方体检：
- 把原版方案 58 张卡按「原版 C1–C5」分组（原版就是按白平衡签名分组的）
- 与优化版 21 个槽位对照，看 C4 现在的 4 个槽原生白平衡是否与 Auto A0 G0 对齐
- 在「原生 Auto A0 G0」的卡里筛夜拍友好的（压高光 / 提暗部 / 低对比）
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
h = open(BASE + r'\app\base.html', encoding='utf-8').read()
recipes = json.load(open(BASE + r'\all_recipes.json', encoding='utf-8'))['results']
by_key = {}
for r in recipes:
    by_key[(r['recipeName'].strip().lower(), r['authorName'].strip().lower())] = r

# 原版 C1–C5 的白平衡签名
heads = [(m.start(), m.group(1), re.sub(r'\s+', ' ', m.group(2))) for m in
         re.finditer(r'<h2 id="mode-(C\d)">(.*?)</h2>', h)]

cards = list(re.finditer(r'<div class="card" id="r-([^"]+)">', h))
rows = []
for n, m in enumerate(cards):
    end = cards[n + 1].start() if n + 1 < len(cards) else h.find('<footer', m.start())
    blk = h[m.start():end]
    nm = re.search(r'<span class="cname">(.*?)</span>', blk)
    au = re.search(r'<span class="cauth">(.*?)</span>', blk)
    va = re.search(r'<div class="vals">(.*?)</div>', blk)
    pa = re.search(r'<div class="params">(.*?)</div>', blk, re.S)
    grp = ''
    for pos, cid, title in heads:
        if pos < m.start():
            grp = cid
    rows.append({
        'cid': m.group(1), 'grp': grp,
        'n': nm.group(1) if nm else '', 'a': au.group(1) if au else '',
        'vals': va.group(1).strip() if va else '',
        'params': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', pa.group(1))).strip() if pa else '',
    })

# 优化版已占用的槽位
used = {}
for m in re.finditer(r'<div class="oslot" id="(oC\d-\d)">(.*?)(?=<div class="oslot"|\Z)', h, re.S):
    b = m.group(2)
    nm = re.search(r'<span class="osname">(.*?)</span>', b)
    au = re.search(r'<span class="osauth">(.*?)</span>', b)
    if nm and au:
        used[(nm.group(1).strip().lower(), au.group(1).strip().lower())] = m.group(1)

print('原版 C1–C5 的白平衡签名：')
for pos, cid, title in heads[:5]:
    print('  ', cid, title[:60])
print()

print('原版各档卡片数：', {c: sum(1 for r in rows if r['grp'] == c) for c in ['C1', 'C2', 'C3', 'C4', 'C5']})
print()

print('=== C4（优化版·夜景）现在的 4 个槽：原生白平衡 vs 本档 Auto A0 G0 ===')
for m in re.finditer(r'<div class="oslot" id="(oC4-\d)">(.*?)(?=<div class="oslot"|\Z)', h, re.S):
    b = m.group(2)
    nm = re.search(r'<span class="osname">(.*?)</span>', b)
    au = re.search(r'<span class="osauth">(.*?)</span>', b)
    n_, a_ = nm.group(1).strip(), au.group(1).strip()
    r = by_key.get((n_.lower(), a_.lower()), {})
    print('  %s %-28s %-18s wb2=%s temp=%s | 曲线 Sh%+d Mid%+d Hi%+d 对比%+d' % (
        m.group(1), n_, a_, r.get('whiteBalance2'), r.get('whiteBalanceTemperature'),
        r.get('shadows', 0), r.get('midtones', 0), r.get('highlights', 0), r.get('contrast', 0)))
print()

print('=== 原生 Auto / Auto(暖色调关) 且不在优化版任何槽位里的卡（58 张卡内） ===')
cand = []
for r in rows:
    rec = by_key.get((r['n'].lower(), r['a'].lower()))
    if not rec:
        continue
    wb2 = rec.get('whiteBalance2') or ''
    if 'Auto' not in wb2:
        continue
    if (r['n'].lower(), r['a'].lower()) in used:
        continue
    score = (rec.get('shadows', 0) or 0) - (rec.get('highlights', 0) or 0) - (rec.get('contrast', 0) or 0)
    night_words = 0
    desc = (rec.get('description') or '').lower()
    for w in ['night', 'low light', 'neon', 'city', 'moody', 'dark']:
        if w in desc:
            night_words += 1
    cand.append((score, night_words, r, rec))
cand.sort(key=lambda x: (-x[0], -x[1]))
for score, nw, r, rec in cand[:14]:
    print('  %-26s %-16s 原版档=%-3s Sh%+d Mid%+d Hi%+d 对比%+d 饱和总和%+d 夜词%d' % (
        r['n'][:26], r['a'][:16], r['grp'], rec.get('shadows', 0), rec.get('midtones', 0),
        rec.get('highlights', 0), rec.get('contrast', 0),
        sum(rec.get(k, 0) or 0 for k in ['yellow', 'orange', 'orangeRed', 'red', 'magenta', 'violet',
                                         'blue', 'blueCyan', 'cyan', 'greenCyan', 'green', 'yellowGreen']), nw))
print()
print('候选数（Auto 原生、未占用）：', len(cand))
