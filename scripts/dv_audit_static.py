# -*- coding: utf-8 -*-
"""静态体检：重复 id / 悬空引用 / 空 catch / TODO / 页面里可见的日期

用法：python scripts/dv_audit_static.py
"""
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
src = open(P, encoding='utf-8').read()

# ---------- 1) 静态声明的 id ----------
static_ids = re.findall(r'<[a-zA-Z][^>]*\bid="([^"]+)"', src)
dup = {k: v for k, v in Counter(static_ids).items() if v > 1}
print('1) 静态 id 共 %d 个，重复的 %d 个' % (len(static_ids), len(dup)))
for k, v in list(dup.items())[:15]:
    print('   !! 重复 id "%s" × %d' % (k, v))

# ---------- 2) JS 动态生成的 id ----------
dyn = set(re.findall(r'\.id\s*=\s*[\'"]([^\'"]+)[\'"]', src))
dyn |= set(re.findall(r'id\s*=\s*"([A-Za-z][\w-]*)"\s*\+\s*', src))       # id="mpw' + idx
dyn_prefix = set(re.findall(r'\bid\s*=\s*[\'"]([A-Za-z][\w-]*)[\'"]\s*\+', src))
firstwords = set(re.findall(r'\bid\s*=\s*[\'"]([A-Za-z][\w-]*)', src))
print('2) JS 里赋值/拼接出的 id：字面量 %d 个，带前缀拼接 %s' % (len(dyn), sorted(dyn_prefix)[:12]))

# ---------- 3) 代码里查找的 id ----------
look = set(re.findall(r'\$\(\s*[\'"]([^\'"]+)[\'"]\s*\)', src))
look |= set(re.findall(r'getElementById\(\s*[\'"]([^\'"]+)[\'"]\s*\)', src))
known = set(static_ids) | dyn
suspect = []
for i in sorted(look):
    if i in known:
        continue
    # 允许 "前缀 + 变量" 形式（如 'mpw' + idx、'camV' + k）
    if any(i and p.startswith(i) for p in dyn_prefix) or any(i.startswith(f) for f in firstwords):
        continue
    # 允许 'of' + i 这类
    if re.fullmatch(r'[A-Za-z]+', i) and any(i == p for p in dyn_prefix):
        continue
    suspect.append(i)
print('3) 代码里查找的 id 共 %d 个；静态/DOM 里找不到的（需人工看）%d 个：' % (len(look), len(suspect)))
for i in suspect:
    # 出现次数 + 上下文
    n = len(re.findall(r'[\'"]' + re.escape(i) + r'[\'"]', src))
    print('   ? %-22s 出现 %d 次' % (i, n))

# ---------- 4) 空 catch（完全吞错）----------
ec = re.findall(r'catch\s*\([^)]*\)\s*\{\s*\}', src)
print('4) 完全空的 catch：%d 个' % len(ec))

# ---------- 5) TODO / FIXME / 调试输出 ----------
for pat in ('TODO', 'FIXME', 'XXX', 'console.log'):
    print('5) %-12s %d 处' % (pat, src.count(pat)))

# ---------- 6) 会显示在页面上的日期/时间字样 ----------
print('6) 页面上可见区域的日期（去掉 <script>/<style> 后再找）：')
body = re.sub(r'<script\b.*?</script>', ' ', src, flags=re.S)
body = re.sub(r'<style\b.*?</style>', ' ', body, flags=re.S)
for m in re.finditer(r'20\d{2}[-/年]\s?\d{1,2}[-/月]\s?\d{1,2}', body):
    a = max(0, m.start() - 90)
    print('   !! %r … 上下文: %s' % (m.group(0), body[a:m.end() + 30].replace('\n', ' ')[-140:]))
