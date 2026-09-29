# -*- coding: utf-8 -*-
"""推演用：把「连接相机」页（#paneD）里的折叠块 / 按钮，按**用户看不看得见**列出来。
只读，不改任何文件。用法：python scripts/map_paneD.py
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()
i = s.index('<div id="paneD"')
j = s.index('<div id="paneT"')
seg = s[i:j]

TOK = re.compile(r'<details\b([^>]*)>|<summary\b[^>]*>(.*?)</summary>|<button\b([^>]*)>(.*?)</button>|</details>', re.S)
depth = 0
hidden = 0          # 处于"关闭的折叠块"里 = 用户看不见
rows = []
for m in TOK.finditer(seg):
    if m.group(0).startswith('<details'):
        is_open = 'open' in (m.group(1) or '')
        depth += 1
        if not is_open:
            hidden += 1
        rows.append(('  ' * depth + ('▾ ' if is_open else '▸ ') + '『折叠块』%s'
                     % ('（默认展开）' if is_open else '（默认收起 → 里面全都看不见）'), is_open))
    elif m.group(0).startswith('</details'):
        depth -= 1
        if depth < hidden:
            hidden -= 1
    elif m.group(2) is not None:
        txt = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        rows.append(('  ' * depth + '  标题：' + txt[:70], hidden == 0))
    else:
        mid = re.search(r'id="([A-Za-z0-9_]+)"', m.group(3) or '')
        lab = re.sub(r'<[^>]+>', '', m.group(4) or '').strip()
        vis = (hidden == 0)
        rows.append(('  ' * depth + '  ● %-18s %s' % (mid.group(1) if mid else '(无id)', lab[:46])
                     + ('' if vis else '   ← 藏在收起块里，得先展开'), vis))

print('=== #paneD（连接相机页）里"用户能直接看到"的东西 ===')
for txt, vis in rows:
    print(('[看得见] ' if vis else '[看不见] ') + txt)
print()
vis_btn = [r for r, v in rows if v and r.strip().startswith('●')]
print('不用展开任何折叠块就能点的按钮：%d 个' % len(vis_btn))
for r in vis_btn:
    print('   ' + r.strip())
