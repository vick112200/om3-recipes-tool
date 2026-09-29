# -*- coding: utf-8 -*-
"""把 patch_final1.py 里那段被写坏的备份提示替换代码修好（用 chr(10) 拼行，避免转义）。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = r'C:\Users\82302\AppData\Local\Temp\patch_final1.py'
lines = open(p, encoding='utf-8').read().split('\n')
start = [k for k, L in enumerate(lines) if L.startswith('A1 = "st(')]
end = [k for k, L in enumerate(lines) if L.startswith('h = h.replace(A2,')]
assert len(start) == 1 and len(end) == 1 and end[0] >= start[0], (start, end)
NL = "chr(10)"
block = [
    'A1 = "st(\'camStBak\', document.getElementById(\'camDl\').disabled ? \'备份：无\' : \'备份：已有\',"',
    'A2 = "document.getElementById(\'camDl\').disabled ? \'\' : \'ok\');"',
    'assert h.count(A1) == 1 and h.count(A2) == 1, (h.count(A1), h.count(A2))',
    'NEW1 = "var _b = null; try{ _b = JSON.parse(localStorage.getItem(BKEY) || \'null\'); }catch(e){ }" + ' + NL + ' + "    st(\'camStBak\', (_b && _b.text) ? (\'备份：\' + tstr(_b.t)) : \'备份：无\',"',
    'h = h.replace(A1, NEW1, 1)',
    'h = h.replace(A2, "(_b && _b.text) ? \'ok\' : \'\');", 1)',
]
lines[start[0]:end[0] + 1] = block
open(p, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
print('已修好 patch_final1.py 的备份提示替换段')
