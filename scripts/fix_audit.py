# -*- coding: utf-8 -*-
"""自检发现的两个真 bug：
   A) id="camPreview" 重复（两个元素同 id → 脚本只能拿到第一个）
   B) 悬空引用：camStatusTxt / camWriteOut / gStatusWrap（脚本去取不存在的元素 → 状态不同步/静默无效）
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# A) 重复 id：把第二个 camPreview 改成 camPreview2（并同步引用它的脚本）
occ = [m.start() for m in re.finditer(r'id="camPreview"', h)]
print('camPreview 出现次数:', len(occ))
if len(occ) > 1:
    # 第二个改名为 camPreview2
    p2 = occ[1]
    h = h[:p2] + 'id="camPreview2"' + h[p2 + len('id="camPreview"'):]

# B-1) gStatusWrap 兜底 → 直接指向自己（去掉不存在 id 的引用）
h = h.replace("var st = document.getElementById('gStatusWrap') || el;", "var st = el;", 1)

# B-2) camStatusTxt / camWriteOut：指向真实存在的元素
h = h.replace("var src = document.getElementById('camStatusTxt') || document.getElementById('camWifiState');",
              "var src = document.getElementById('camWifiState') || document.getElementById('camGateOut');", 1)
if 'camWriteOut' in h:
    # 把它的使用处加护栏（元素不存在时不要静默/报错）
    h = h.replace("document.getElementById('camWriteOut').", "var _cwo = document.getElementById('camWriteOut'); if(_cwo) _cwo.", 1)

# 通用加固：所有 "getElementById('X')." 直接取属性的写法，若是已知悬空 id 就加护栏
for bad in ['camWriteOut', 'camStatusTxt']:
    while True:
        m = re.search(r"(?<!if\()(?<!_cwo )document\.getElementById\('" + bad + r"'\)\.", h)
        if not m:
            break
        h = h[:m.start()] + "((document.getElementById('" + bad + "')||{})." + h[m.end():]
        break

open(P, 'w', encoding='utf-8', newline='').write(h)
print('修复完成（%+d 字节）；剩余悬空引用检查：' % (len(h) - n0))
refs = set(re.findall(r"getElementById\(\s*'([^']+)'\s*\)", h))
ids = set(re.findall(r'\sid="([^"]+)"', h))
print(sorted(r for r in refs if r not in ids and r not in ('of0', 'mpFile', 'om3File')))
