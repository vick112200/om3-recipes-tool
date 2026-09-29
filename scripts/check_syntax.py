# -*- coding: utf-8 -*-
"""语法自检：把 app/base.html 里所有内联 <script> 抽出来，逐个交给 node --check

改完代码必跑这个（HANDOVER 第 4 节：node --check 抽主脚本检查语法）。
"""
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'D:\workspace\om3-handbook\app\base.html'
src = open(SRC, encoding='utf-8').read()

# 逐个抓内联脚本（跳过带 src= 的外链）
blocks = []
for m in re.finditer(r'<script\b([^>]*)>(.*?)</script>', src, re.S):
    attrs, body = m.group(1), m.group(2)
    if 'src=' in attrs:
        continue
    if not body.strip():
        continue
    line0 = src[:m.start(2)].count('\n') + 1
    blocks.append((line0, body))

print('内联脚本块：%d 个' % len(blocks))
tmpd = tempfile.mkdtemp(prefix='om3chk')
bad = 0
for idx, (line0, body) in enumerate(blocks):
    p = os.path.join(tmpd, 'blk%02d.js' % idx)
    open(p, 'w', encoding='utf-8').write(body)
    r = subprocess.run(['node', '--check', p], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    tag = 'OK ' if r.returncode == 0 else '语法错误'
    print('  [%s] 块%02d 起于 base.html 第 %d 行（%d 字符）' % (tag, idx, line0, len(body)))
    if r.returncode != 0:
        bad += 1
        print(''.join('      ' + l + '\n' for l in (r.stderr or '').split('\n')[:12]))

print('结论：%s' % ('全部通过 ✅' if bad == 0 else '有 %d 个块语法错误 ❌' % bad))
sys.exit(1 if bad else 0)
