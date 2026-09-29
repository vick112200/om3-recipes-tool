# -*- coding: utf-8 -*-
"""第 39 轮（B4）：① 真正删掉场景对比页顶部的大标题/小标题（上一版忘了这步）
   ② 修探针里被 shell 吃坏的控制字符路径"""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\workspace\om3-handbook'
P = BASE + r'\app\base.html'
s = io.open(P, encoding='utf-8').read()

ipc = s.find('<div id="paneC"')
assert ipc > 0
head = s[ipc:ipc + 3000]
m = re.search(r'<h1>[^<]*</h1>', head)
m2 = re.search(r'<p class="sub">.*?</p>', head, re.S)
print('  paneC 顶部 h1 = %r' % (m.group(0)[:40] if m else None))
print('  paneC 顶部 sub = %r' % (m2.group(0)[:60] if m2 else None))
if m:
    s = s[:ipc + m.start()] + s[ipc + m.start() + len(m.group(0)):]
    off = len(m.group(0))
    ipc2 = ipc
    head2 = s[ipc2:ipc2 + 3000]
    m2 = re.search(r'<p class="sub">.*?</p>', head2, re.S)
    if m2:
        s = s[:ipc2 + m2.start()] + s[ipc2 + m2.start() + len(m2.group(0)):]
    io.open(P, 'w', encoding='utf-8', newline='').write(s)
    print('  ✅ 已删掉 paneC 顶部大标题/小标题（%d + %d 字符）' % (off, len(m2.group(0)) if m2 else 0))

# ② 探针路径
q = BASE + r'\scripts\dv_scene39.py'
t = io.open(q, encoding='utf-8').read()
lines = t.split('\n')
for i, ln in enumerate(lines):
    if '_probe_scene39.html' in ln and ln.strip().startswith('p ='):
        lines[i] = "p = SRC + '\\\\app\\\\_probe_scene39.html'   # 必须放在 app/ 下：页面里的图是相对路径 images/"
        print('  ✅ 探针第 %d 行已修：%s' % (i + 1, lines[i]))
io.open(q, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
