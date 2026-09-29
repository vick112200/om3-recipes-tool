# -*- coding: utf-8 -*-
"""结构自检：全代码扫描"函数体第一句就调用自己"的自递归（$ 那类批量替换事故）"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
src = open(r'D:\workspace\om3-handbook\app\base.html', encoding='utf-8').read()

pat = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{')
hits = []
for m in pat.finditer(src):
    name = m.group(1)
    body = src[m.end():m.end() + 320]
    # 只看**第一句**：第一句就调用自己 = 必然无限递归
    first = body.strip().split('\n')[0].strip()
    if re.search(r'(?<![\w$.])' + re.escape(name) + r'\s*\(', first):
        hits.append((name, first[:90]))

print('--- 疑似"定义后立刻调用自己"的函数（%d 个）---' % len(hits))
for n, f in hits:
    print('  %-20s 首句: %s' % (n, f))
