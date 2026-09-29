# -*- coding: utf-8 -*-
"""把 app/index.html 复制成 apk/assets/index.html，并注入「这是 app 版」标记。"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))          # ...\om3-handbook\apk
ROOT = os.path.dirname(HERE)                               # ...\om3-handbook
src = os.path.join(ROOT, 'app', 'index.html')
dst = os.path.join(HERE, 'assets', 'index.html')
h = open(src, encoding='utf-8').read()
flag = '<script>window.__OM3_APP__=1;</script>\n'
i = h.find('<body')
j = h.find('>', i) + 1
h = h[:j] + flag + h[j:]
open(dst, 'w', encoding='utf-8', newline='').write(h)
print('assets/index.html %.1f MB（已注入 app 标记）' % (len(h.encode()) / 1048576))
