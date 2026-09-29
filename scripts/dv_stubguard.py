# -*- coding: utf-8 -*-
"""扫「$() 真值占位对象」这一类坑：

$() 取不到元素时返回的是**真值占位对象**（不是 null），所以下面两种写法都会静默失效：
  var x = $('id');  if(!x){ ...创建元素... }        ← 这个分支永远进不去
  var x = $('id');  if(x) x.addEventListener(...)   ← 事件绑到了占位对象上

用法：python scripts/dv_stubguard.py
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
src = open(P, encoding='utf-8').read()

static_ids = set(re.findall(r'<[a-zA-Z][^>]*\bid="([^"]+)"', src))
dyn_ids = set(re.findall(r"\.id\s*=\s*'([^']+)'", src))
dyn_ids |= set(re.findall(r'\.id\s*=\s*"([^"]+)"', src))
dyn_ids |= set(re.findall(r"\bid\s*=\s*'([A-Za-z][\w-]*)'\s*\+", src))

print('静态 id=%d 个；JS 动态创建/赋值的 id=%d 个' % (len(static_ids), len(dyn_ids)))
print()

pat = re.compile(r"([A-Za-z_$][\w$]*)\s*=\s*\$\('([^']+)'\)")
rows = []
for m in pat.finditer(src):
    var, eid = m.group(1), m.group(2)
    ln = src[:m.start()].count('\n') + 1
    win = src[m.end():m.end() + 500]
    bang = re.search(r'if\s*\(\s*!\s*' + re.escape(var) + r'\s*\)', win)
    existence = (eid in static_ids) or (eid in dyn_ids)
    if bang or not existence:
        rows.append((ln, var, eid, 'if(!%s)' % var if bang else '-', existence))

print('%-7s %-13s %-14s %-16s %s' % ('行', '变量', 'id', '紧跟着的判断', '该 id 是否会被创建'))
for ln, var, eid, kind, ok in rows:
    print('%-7d %-13s %-14s %-16s %s' % (ln, var, eid, kind, '会' if ok else '★不会 → 危险'))
print()
print('需要注意 %d 处。判据：' % len(rows))
print('  · 「★不会」= 代码里从没创建过这个 id，而 $() 又返回真值 → if(!var) 永不成立 / if(var) 永远成立')
print('  · 「if(!var)」= 这类"没有就创建"的写法，只要 $() 返回真值就永远不创建')
