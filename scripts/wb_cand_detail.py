# -*- coding: utf-8 -*-
"""候选配方的细节：原文描述 + 12 色轮 + 曲线参数 + 已有的补充说明（画面感觉/适合/避开）。"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
h = open(BASE + r'\app\base.html', encoding='utf-8').read()
recipes = json.load(open(BASE + r'\all_recipes.json', encoding='utf-8'))['results']
by_key = {(r['recipeName'].strip().lower(), r['authorName'].strip().lower()): r for r in recipes}
# 卡片补充说明
card_notes = {}
for m in re.finditer(r'<div class="card" id="r-([^"]+)">', h):
    nxt = h.find('<div class="card" id="r-', m.end())
    blk = h[m.start():nxt if nxt > 0 else m.start() + 20000]
    nm = re.search(r'<span class="cname">(.*?)</span>', blk)
    au = re.search(r'<span class="cauth">(.*?)</span>', blk)
    rows = re.findall(r'<span class="mk">(.*?)</span><span class="mv[^"]*">(.*?)</span>', blk, re.S)
    key = ((nm.group(1).strip().lower(), au.group(1).strip().lower()) if nm and au else None)
    if key:
        card_notes[key] = dict((re.sub(r'<[^>]+>', '', k).strip(),
                                re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', v)).strip()) for k, v in rows)
    # 有哪些对比场景图
    scenes = re.findall(r'data-im="[^"]*__cmp__([a-z\-]+)\.jpg"', blk)
    if key:
        card_notes[key]['_scenes'] = sorted(set(scenes))

WANT = [('CityEurope', 'Robson Cabanas'), ('The Night Mayor', 'Burak Yilmaz'), ('PNW', 'Ian Will'),
        ('Nostalgic Summer', 'Kyler Steele'), ('Default - 4', 'OM System'), ('Fuji Eterna', 'ibd'),
        ('Paul Clark recipe', 'Paul Clark'), ('Portra 160', 'Isaac Mitropoulos')]

for name, auth in WANT:
    r = by_key.get((name.lower(), auth.lower()))
    nt = card_notes.get((name.lower(), auth.lower()), {})
    if not r:
        print('## %s / %s  —— 不在 all_recipes.json' % (name, auth))
        continue
    ch = ['yellow', 'orange', 'orangeRed', 'red', 'magenta', 'violet', 'blue', 'blueCyan',
          'cyan', 'greenCyan', 'green', 'yellowGreen']
    print('## %s / %s   wb=%s%s' % (name, auth, r.get('whiteBalance2'),
                                    ('(%sK)' % r['whiteBalanceTemperature']) if r.get('whiteBalanceTemperature') else ''))
    print('   12色: ', ' '.join('%s%+d' % (k[:2], r[k] or 0) for k in ch))
    print('   曲线: Sh%+d Mid%+d Hi%+d 对比%+d 锐度%+d 曝光%+s' % (
        r.get('shadows') or 0, r.get('midtones') or 0, r.get('highlights') or 0,
        r.get('contrast') or 0, r.get('sharpness') or 0, r.get('exposureCompensation')))
    d = ' '.join((r.get('description') or '').split())
    print('   原文:', d[:220])
    for k in ['画面感觉', '色彩重点', '影调', '适合', '避开', '提示']:
        if nt.get(k):
            print('   %s: %s' % (k, nt[k][:150]))
    print('   对比场景图:', nt.get('_scenes'))
    print()
