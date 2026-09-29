# -*- coding: utf-8 -*-
"""下一轮 1) toc2 在源码里直接搬到 body（不再依赖运行时搬家）+ 清掉底部空项
   2) 浮层(fixed)体检：列出每个浮层的 z-index / 是否有 !important 隐藏兜底
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- 1a) toc2：用 nav 配对（上次用 div 配对才切坏的）搬到 body ----------
i = h.find('<nav id="toc2"')
print('toc2 起点:', i)
if i > 0:
    seg = h[i:]
    depth = 0
    pos = 0
    end = -1
    for m in re.finditer(r'</?nav\b', seg):
        if seg[m.start():m.start()+5] == '</nav':
            depth -= 1
            if depth == 0:
                end = seg.find('>', m.start()) + 1
                break
        else:
            depth += 1
    print('nav 配对结束位置:', end, '块长', end)
    assert end > 0, 'nav 配对失败'
    block = seg[:end]
    h = h[:i] + seg[end:]
    mB = h.rfind('</body>')
    h = h[:mB] + '\n<!-- 搜索 / 目录面板（顶层，任何页签都能显示） -->\n' + block + '\n' + h[mB:]
    print('已静态搬到 body（块长 %d 字符）' % len(block))

# ---------- 1b) 清掉空 data-p 的脏按钮 ----------
for pat in [r'\n\s*<button[^>]*data-p=""[^>]*>[^<]*</button>', r'data-p=""']:
    for m in list(re.finditer(pat, h)):
        h = h[:m.start()] + h[m.end():]
        print('已清掉空 data-p 项')

# ---------- 2) 浮层体检 ----------
print()
print('=== 浮层（position:fixed）体检 ===')
rules = re.findall(r'([#.]?[\w-]+(?:\s*,\s*[#.]?[\w-]+)*)\{([^}]*position:\s*fixed[^}]*)\}', h)
seen = set()
for sel, body in rules:
    if sel in seen:
        continue
    seen.add(sel)
    z = re.search(r'z-index:\s*(\d+)', body)
    has_imp = ('%s.hide' % sel) in h and '!important' in h.split('%s.hide' % sel)[1][:80]
    print('  %-22s z=%-6s 有隐藏兜底: %s' % (sel[:22], z.group(1) if z else '-', '✓' if has_imp else '无'))

# 关键浮层是否都带“可关闭/不遮挡”的兜底
for cls in ['scanmask', 'taskmask', 'omask', 'toc2', 'gstatus', 'taskpill', 'foldbar', 'foldtip', 'top', 'lb']:
    hit = re.search(r'\.%s\b[^{]*\{[^}]*position:\s*fixed' % cls, h) or re.search(r'#%s\b[^{]*\{[^}]*position:\s*fixed' % cls, h)
    imp = ('%s.hide{display:none !important' % cls) in h or ('#%s.hide{display:none !important' % cls) in h
    print('  · %-10s fixed=%-5s 隐藏兜底=%s' % (cls, '是' if hit else '否', '有' if imp else '无'))

open(P, 'w', encoding='utf-8', newline='').write(h)
print()
print('改动完成（%+d 字节）' % (len(h) - n0))
