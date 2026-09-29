# -*- coding: utf-8 -*-
"""C4 换配方后，把页面上其它地方过时的说法一起改正。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

PAIRS = [
    # 1) 位移表 C4 行
    ('City Look / Q116 原生即 Auto，零位移；Paul Clark recipe / Portra 160 原生 5300K，要用原味需现场把色温拨到 5300K',
     'Cool Spring / PNW / City Look / Q116 原生都是 A0 G0，四格零位移，白平衡一个数都不用现场改'),
    # 2) 样片说明
    ('4 格没有样片：两格「白里透红」是本方案自配、站上不存在；Paul Clark recipe 与 Portra 160 在站上属于固定色温组，只登记参数、没有卡片。Ilford HP5 有原文但没有样片。',
     '2 格没有样片：两格「白里透红」是本方案自配，站上不存在。Ilford HP5 有原文但没有样片。'),
    ('站上没有卡片的 4 格（两格自配、两格固定色温）是按同一套口径补写的。',
     '站上没有卡片的那 2 格（两格自配）是按同一套口径补写的。'),
    # 3) 签名修正框里 5300K 那一对
    ('· <b>5300K A+0 G+0</b> → Portra 160、Paul Clark recipe（这两格最早就是照这一对合的 C4；现在 C4 改用 Auto，要在 Auto 下还原它们，得现场把色温拨到 5300K）',
     '· <b>5300K A+0 G+0</b> → Portra 160、Paul Clark recipe（这两卷现在挂在下面的「需单独占一档」里：'
     '想要原味就让它们合占一个 C 档、色温设 5300K，两格都不用改白平衡）'),
    # 4) 说明折标题
    ('<summary>为什么白平衡改成 Auto，而不是钉死 5300K：</summary>',
     '<summary>为什么白平衡是 Auto（不是钉死 5300K），四格又是怎么挑的：</summary>'),
    ('<b>为什么白平衡改成 Auto，而不是钉死 5300K：</b>',
     '<b>为什么白平衡是 Auto（不是钉死 5300K），四格又是怎么挑的：</b>'),
]
for old, new in PAIRS:
    n = h.count(old)
    assert n == 1, ('锚点命中 %d 次：%s' % (n, old[:46]))
    h = h.replace(old, new, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面其它过时说法已改正 %d 处，base.html %.1f KB' % (len(PAIRS), len(h.encode('utf-8')) / 1024))
