# -*- coding: utf-8 -*-
"""修复搜索/目录面板：
   1) 把被我搬走的那一段（<nav id="toc2"> + 标题）从顶层放回它原来的位置（paneB 里、目录内容之前）
   2) 标题改回“搜索 / 目录”
   3) 用运行时 appendChild 把整个 nav 搬到 body（安全，不会切一半）
   4) 打印诊断，便于核对
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# 1) 取回被我搬到顶层的那一段
m = re.search(r'<!-- 搜索 / 目录面板（提到顶层[^>]*-->\s*<nav id="toc2">\s*<div class="t2head">[^<]*</div>', h)
if not m:
    m = re.search(r'<nav id="toc2">\s*<div class="t2head">[^<]*</div>', h)
assert m, '顶层那段没找到'
chunk = m.group(0)
print('取回的一段 =', repr(chunk[:80]))

# 2) 从顶层移除（连同注释）
h = h[:m.start()] + h[m.end():]

# 3) 找 paneB 里"目录内容"的起点：优先找搜索输入框/列表容器
cands = ['id="tocq"', 'class="t2search"', 'class="t2list"', 'class="t2body"', 'class="tg"', 'class="tgh"']
paneB = h.find('id="paneB"')
assert paneB > 0, 'paneB 没找到'
blank = h.find('id="paneD"')
anchor = -1
which = ''
for c in cands:
    p = h.find(c, paneB, blank if blank > paneB else len(h))
    if p > 0 and (anchor < 0 or p < anchor):
        anchor = p; which = c
print('目录内容起点锚点 =', which, '位置', anchor)

if anchor > 0:
    ins = h.rfind('<', 0, anchor)
else:
    # 兜底：插在 paneB 结束前
    ins = h.rfind('</div>', paneB, blank if blank > paneB else len(h))
assert ins > 0, '插入点没找到'

# 4) 拼回：把 nav 开头 + 标题放回原位，标题改成“搜索 / 目录”
title = '<div class="t2head">搜索 / 目录</div>'
h = h[:ins] + '\n' + '<nav id="toc2">' + '\n' + title + '\n' + h[ins:]

# 5) 运行时把整个 nav 搬到 body（安全搬家）—— 加在现有 toc 逻辑块后面
anchor_js = "    window.__om3tocToggle = toggle;"
assert h.count(anchor_js) == 1, h.count(anchor_js)
h = h.replace(anchor_js, anchor_js + '''
    /* 安全搬家：把整个 #toc2 子树挂到 body（避免它在某个隐藏页签里看不见） */
    try{
      var p2 = document.getElementById('toc2');
      if(p2 && p2.parentElement !== document.body) document.body.appendChild(p2);
      if(p2 && !p2.querySelector('.t2head')) { var t = document.createElement('div'); t.className = 't2head'; t.textContent = '搜索 / 目录'; p2.insertBefore(t, p2.firstChild); }
    }catch(e){ log('搜索面板搬家失败：' + (e && e.message ? e.message : e), 'err'); }''', 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('已拼回并改标题（%+d 字节）' % (len(h) - n0))
