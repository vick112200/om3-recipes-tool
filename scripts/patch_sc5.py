# -*- coding: utf-8 -*-
"""对比卡第二个按钮的文案修正：'2 优化版 →' → 'C2 优化版 →'。"""
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
P = BASE + r'\app\base.html'
h = open(P, encoding='utf-8').read()
i = h.find('window.SC=')
SC, end = json.JSONDecoder().raw_decode(h, i + len('window.SC='))
n = 0
for sc in SC:
    for it in sc['items']:
        if it.get('os'):
            it['osm'] = it['os'].split('-')[0][1:]
            n += 1
assert n > 0
h = h[:i + len('window.SC=')] + json.dumps(SC, ensure_ascii=False, separators=(',', ':')) + h[end:]
open(P, 'w', encoding='utf-8', newline='').write(h)
print('已修正 %d 条「优化版 →」按钮文案，例：%s' % (n, SC[0]['items'][4].get('osm')))
