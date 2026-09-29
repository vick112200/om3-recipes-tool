# -*- coding: utf-8 -*-
"""C4 换配方后的自检。"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
h = open(r'C:\Users\82302\AppData\Local\Temp\app\base.html', encoding='utf-8').read()
i = h.find('<div class="omode" id="oC4">')
j = h.find('<div class="omode" id="oC5">')
blk = h[i:j]
print('C4 槽位：')
for m in re.finditer(r'<div class="oslot" id="(oC4-\d)">(.*?)(?=<div class="oslot"|\Z)', blk, re.S):
    b = m.group(2)
    nm = re.search(r'<span class="osname">(.*?)</span>', b).group(1)
    au = re.search(r'<span class="osauth">(.*?)</span>', b).group(1)
    print('  %s %-14s %-18s wheel=%s 色值=%d 图=%d 原文折=%s 补充折=%s 参数行=%s 白平衡行=%s' % (
        m.group(1), nm, au, '<svg' in b, b.count('class="ovc"'), b.count('<figure'),
        'fnote' in b, 'fmine' in b, 'osline prm' in b, 'osline wbok' in b))
print()
print('C4 里还提到 5300K 的次数：', blk.count('5300K'), '（应只在说明文字里出现）')
print('C4 头 chip：', re.findall(r'<span class="omchip kt">(.*?)</span>', blk))
print()
print('单独占档名单：')
k = h.find('id="osolo"')
seg = h[k:k + 30000]
for m in re.finditer(r'<div class="osoloh"><b>(.*?)</b>(<span class="osolowb">(.*?)</span>)?</div>', seg):
    print('  -', m.group(1), '|', m.group(3) or '')
print()
print('夜景人像表：')
seg2 = h[h.find('这一档拍夜景人像怎么用'):h.find('这一档拍夜景人像怎么用') + 3000]
for m in re.finditer(r'<tr><td>(.*?)</td><td class="og">(.*?)</td>', seg2):
    print('  %-24s → %s' % (m.group(1)[:24], m.group(2)))
print()
SC, _ = json.JSONDecoder().raw_decode(h, h.find('window.SC=') + len('window.SC='))
c = {}
for sc in SC:
    for it in sc['items']:
        if it.get('os'):
            c.setdefault(it['os'], c.get(it['os'], 0) + 1)
print('对比页「优化版 →」按钮指向：', dict(sorted(c.items())))
print('Cool Spring / PNW 的按钮：', [it.get('os') for it in SC[0]['items'] if it['n'] in ('Cool Spring', 'PNW')])
