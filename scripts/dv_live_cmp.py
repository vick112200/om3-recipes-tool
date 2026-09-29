# -*- coding: utf-8 -*-
"""跑 live_check.py，但把被测真源换成指定的备份（做"改前/改后逐字段一致"的对照）。"""
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
target = sys.argv[1] if len(sys.argv) > 1 else 'base.before_r64.html'
tag = sys.argv[2] if len(sys.argv) > 2 else 'before64'

src = io.open(os.path.join(ROOT, 'scripts', 'live_check.py'), encoding='utf-8').read()
old = "src = open(SRC + r'\\app\\base.html', encoding='utf-8').read()"
new = "src = open(SRC + r'\\app\\%s', encoding='utf-8').read()" % target
assert old in src, '没找到真源那一行'
v = src.replace(old, new)
v = v.replace('dv_live.html', 'dv_live_%s.html' % tag).replace("r'\\olive'", "r'\\olive_%s'" % tag)
p = os.path.join(TMP, '_live_%s.py' % tag)
io.open(p, 'w', encoding='utf-8').write(v)
r = subprocess.run([sys.executable, p], capture_output=True, text=True, encoding='utf-8')
print('--- 被测：%s ---' % target)
print((r.stdout or '').strip()[-700:])
if r.returncode != 0:
    print('(exit %d) %s' % (r.returncode, (r.stderr or '')[-300:]))
