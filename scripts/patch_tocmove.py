# -*- coding: utf-8 -*-
"""把 #toc2（搜索/目录面板）从它现在所在的容器里提到 body 顶层 —— 这样在任何页签都能显示"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

i = h.find('id="toc2"')
assert i > 0, 'toc2 not found'
# 找它所在元素的起始 '<'
st = h.rfind('<', 0, i)
tag_end = h.find('>', i)
# 用 div 计数找到块尾
seg = h[st:]
depth = 0
j = 0
while j < len(seg):
    m = re.compile(r'</?div\b', re.I).search(seg, j)
    if not m:
        break
    if seg[m.start():m.start()+2] == '</':
        depth -= 1
        if depth == 0:
            close = seg.find('>', m.start())
            j = close + 1
            break
    else:
        depth += 1
    j = m.end()
assert j > 0, 'block end not found'
block = seg[:j]

# 位置诊断
order = []
for pid in ['id="paneA"', 'id="paneB"', 'id="paneC"', 'id="paneD"', 'id="paneE"', 'id="top"', 'id="foldbar"']:
    p = h.find(pid)
    if p >= 0:
        order.append((p, pid))
order.sort()
owner = 'body 顶层'
for k in range(len(order)):
    a = order[k][0]
    b = order[k+1][0] if k+1 < len(order) else len(h)
    if a < st < b:
        owner = order[k][1]
        break
print('移动前：toc2 位于 [%s] 之内（块长 %d 字符）' % (owner, len(block)))

# 提到 </body> 前
h2 = h[:st] + h[st:st+j].replace(block, '', 1) if False else h[:st] + h[st+j:]
mB = h2.rfind('</body>')
assert mB > 0
h2 = h2[:mB] + '\n<!-- 搜索 / 目录面板（提到顶层，保证任何页签都能显示） -->\n' + block + '\n' + h2[mB:]

# 顶层显示需要的样式（面板自身用 .open 控制，这里确保它脱离任何隐藏容器）
k2 = h2.find('</style>')
h2 = h2[:k2] + """
#toc2{position:fixed;left:0;right:0;top:0;bottom:0;z-index:9600;overflow:auto;background:#121212}
""" + h2[k2:]

open(P, 'w', encoding='utf-8', newline='').write(h2)
print('已把 toc2 提到 body 顶层 + 设为全屏浮层（%+d 字节）' % (len(h2) - n0))
