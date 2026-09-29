# -*- coding: utf-8 -*-
"""方案列表条目精简：名称 + 右侧"档位"标签 + 一行描述（去掉"点开看各槽位…"）"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

old = """      d.innerHTML = '<div class="t">' + (s.name || '未命名方案') + '</div>' +
        '<div class="s">' + (s.desc ? s.desc : (tierLabel(s.from || 'current') + ' · ' + used + ' 个槽位有内容')) + '</div>' +
        '<div class="s" style="opacity:.7">点开看各槽位 · 可单独导入相机</div>';"""
assert h.count(old) == 1, h.count(old)
new = """      d.innerHTML = '<div class="t">' + (s.name || '未命名方案') +
        '<span class="mpbadge">' + tierLabel(s.from || 'current') + '</span></div>' +
        '<div class="s">' + (s.desc ? s.desc : (used + ' / 4 个槽位有内容')) + '</div>';"""
h = h.replace(old, new, 1)

k = h.find('</style>')
assert k > 0
h = h[:k] + """
.mpitem .t .mpbadge{float:right;font-size:12px;font-weight:500;padding:2px 9px;border-radius:999px;background:#1e2636;border:1px solid #33507e;color:#cfe0ff}
""" + h[k:]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('列表条目已精简（%+d 字节）' % (len(h) - n0))
