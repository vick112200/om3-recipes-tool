# -*- coding: utf-8 -*-
"""扫「async 函数被当同步调用」的坑：

  try{ await 或者 return 都没写，直接 doAsyncThing(); }catch(e){ 提示 }
  → async 函数的失败会变成 unhandledrejection，try/catch 抓不到
  → **操作失败却什么都不提示**（用户看到的就是"点了没反应/没变化"）

用法：python scripts/dv_asyncguard.py
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
src = open(P, encoding='utf-8').read()

asyncs = set(re.findall(r'async\s+function\s+([A-Za-z_$][\w$]*)', src))
arrow_asyncs = set(re.findall(r'([A-Za-z_$][\w$]*)\s*=\s*async\s*\(', src))
names = sorted(asyncs | arrow_asyncs)
print('async 函数共 %d 个：%s' % (len(names), ', '.join(names[:24]) + (' …' if len(names) > 24 else '')))
print()

bad = []
for nm in names:
    for m in re.finditer(r'(?<![\w$.])' + re.escape(nm) + r'\s*\(', src):
        # 往前看 30 字符判断是不是 await / return / = / .then / Promise
        pre = src[max(0, m.start() - 34):m.start()]
        if re.search(r'(await\s*|return\s*|=\s*|\.\s*)$', pre):
            continue
        ln = src[:m.start()].count('\n') + 1
        # 看这一行 / 上一行是不是 try{
        line_start = src.rfind('\n', 0, m.start()) + 1
        line = src[line_start:src.find('\n', m.start())]
        prev = src[max(0, line_start - 200):line_start]
        bad.append((ln, nm, 'try{' in prev[-120:] or 'try{' in line, line.strip()[:96]))

print('%-7s %-22s %-8s %s' % ('行', '被调用', '在 try 里?', '代码'))
for ln, nm, inTry, line in bad:
    print('%-7d %-22s %-8s %s' % (ln, nm, '★是' if inTry else '否', line))
print()
print('共 %d 处；带 ★ 的是"try/catch 抓不到失败"的危险写法（其余多为 fire-and-forget，需人看）。' % len(bad))
