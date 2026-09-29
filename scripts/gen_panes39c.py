# -*- coding: utf-8 -*-
"""第 39 轮（A3）：页签清单有**两处**（`PANES` 在旧切换、`PS` 在新的 switchPane），
两边都要含 'F' —— 只改一处的话点「本站设计」会静默无反应（switchPane 第一行就 return）。"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(p, encoding='utf-8').read()
old = "var PS = ['A','B','C','D','E'];"
new = "var PS = ['A','F','B','C','D','E'];   /* 第 39 轮：加 'F' 本站设计（另一处清单 PANES 也要加，两处都是真源） */"
assert s.count(old) == 1, 'PS 锚点不唯一：%d' % s.count(old)
s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print("✅ PS 已加 'F'")
