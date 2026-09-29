# -*- coding: utf-8 -*-
"""按用户要求：重启选项固定为"自动开启"（写入后必须重启让数据生效），不再是一个可取消的勾选。"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# 1) 找到含 camReboot 的那个 label，整块替换为"已固定开启"的静态说明
m = re.search(r'<label[^>]*>[^<]*<input[^>]*id="camReboot"[^>]*>[^<]*</label>', h)
if not m:
    m = re.search(r'<input[^>]*id="camReboot"[^>]*>', h)
assert m, 'camReboot not found'
old = m.group(0)
if old.startswith('<label'):
    new = '<label style="opacity:.85"><input type="checkbox" id="camReboot" checked disabled>写入完成后自动重启相机（让新数据生效，已固定开启）</label>'
else:
    new = old.replace('>', ' checked disabled>', 1)
h = h[:m.start()] + new + h[m.end():]

# 2) 写入路径里保证一定带 reboot（幂等：已无条件重启则不动）
if "if(document.getElementById('camReboot').checked)" in h:
    h = h.replace("if(document.getElementById('camReboot').checked){", "if(true){", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('重启选项已固定开启（+%d 字节）' % (len(h) - n0))
