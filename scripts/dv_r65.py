# -*- coding: utf-8 -*-
"""第 65 轮验收：53 个未用 `.cgi` 的参数表「没有编」。

本轮的产物是**一张表**，所以探针的核心就一件事：
**把 `SPEC-round65.md` §4 里所有反引号里的"参数片段"抠出来，逐条到 `dis.txt` 里找 —— 找不到就是编的。**

再加三条结构性检查：
  · `--list` 口径：68 个 `.cgi`，其中未用 53 个；
  · `--all` 覆盖：块数 > 53，且**没有一个**"索引里找不到"；
  · **App 零改动**：`app/base.html` md5 必须还是第 64 轮的 `3692725c…`（本轮只做分析，不许碰页面）。

跑法：python scripts/dv_r65.py
"""
import hashlib
import io
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
SPEC = os.path.join(ROOT, 'SPEC-round65.md')
DIS = os.path.join(ROOT, 'official_app', 'dis.txt')
TOOL = os.path.join(ROOT, 'official_app', 'oi_cgi.py')
PAGE = os.path.join(ROOT, 'app', 'base.html')
PAGE_MD5 = '3692725c82e022d643b69c465d77f474'      # 第 64 轮产物（v3.18 源码）
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


spec = io.open(SPEC, encoding='utf-8').read()
dis = io.open(DIS, encoding='utf-8', errors='replace').read()

print('=== A. 表里的参数片段必须能在 dis.txt 里找到 ===')
# 只验 §4「参数表」那一段（§2/§3/§5 里写的是方法名、类名，不是参数）
sec4 = spec[spec.index('## 4. 参数表'):spec.index('## 5. ')]
tokens = []
for m in re.finditer(r'`([^`]+)`', sec4):
    t = m.group(1).strip()
    if not t or not t.isascii():
        continue
    # 只挑"像参数/像取值/像 CGI 名"的：带 = 、或 .cgi 结尾、或是 /^[0-9a-z_]{3,}$/（取值词）
    if ('=' in t) or t.endswith('.cgi') or re.match(r'^[0-9a-z_]{3,}$', t):
        tokens.append(t)
tokens = list(dict.fromkeys(tokens))
miss = [t for t in tokens if t not in dis]
print('  （§4 里抠出 %d 个参数/取值/CGI 名片段）' % len(tokens))
A(not miss, '全部 %d 个片段都在 dis.txt 里逐字出现过（编的会是：%s）' % (len(tokens), miss[:8] if miss else '无'))
A(len(tokens) >= 60, '参数片段数量像样（%d ≥ 60）—— 不是空表' % len(tokens))

# CGI 名本身必须都在 --list 的名单里
names = set(m.group(1) for m in re.finditer(r'`([a-z_0-9]+\.cgi)`', sec4))
r = subprocess.run([sys.executable, TOOL, '--list'], capture_output=True, text=True,
                   encoding='utf-8', errors='ignore')
listed = set(re.findall(r'^\s+([a-z_0-9]+\.cgi)\s', r.stdout, re.M))
A(names and names <= listed, '§4 提到的 CGI 名（%d 个）都在 --list 的 68 个里（不在的：%s）'
  % (len(names), sorted(names - listed) or '无'))

print('=== B. 工具口径 + 覆盖（表里不许漏、不许编） ===')
tail = [x for x in (r.stdout or '').strip().splitlines() if x.startswith('（共')]
A(bool(tail) and '共 68 个' in tail[0] and '没碰过的 55 个' in tail[0],
  '--list 口径正确：%s' % (tail[0] if tail else '（没输出）'))
A(len(listed) == 68, '--list 列出 68 个 CGI（实为 %d）' % len(listed))
# 未用名单：--list 里没有 ★在用 的那些
unused = set()
for line in (r.stdout or '').splitlines():
    m = re.match(r'\s+([a-z_0-9]+\.cgi)\s+\d+(\s+★在用)?\s*$', line)
    if m and not m.group(2):
        unused.add(m.group(1))
A(len(unused) == 55, '算出来的"未用"是 55 个（实为 %d）' % len(unused))
A(unused == names, '§4 表里的 CGI 名与"未用名单"**完全相等**（漏：%s / 多：%s）'
  % (sorted(unused - names) or '无', sorted(names - unused) or '无'))

r2 = subprocess.run([sys.executable, TOOL, '--all'], capture_output=True, text=True,
                    encoding='utf-8', errors='ignore')
blocks = r2.stdout.count('=== ')
A(blocks >= 55, '--all 出了 %d 个块（≥ 55）' % blocks)
A('索引里找不到' not in r2.stdout, '没有一个 CGI 是"索引里找不到"（都能定位到引用它的方法）')
A(r2.stdout.count('参数键候选') >= 20, '多数块给出了"参数键候选"（%d 块）' % r2.stdout.count('参数键候选'))

print('=== C. §3 的"共享助手"结论可复现 ===')
r3 = subprocess.run([sys.executable, TOOL, '--body', 'Lc2/s;', 'a'], capture_output=True, text=True,
                    encoding='utf-8', errors='ignore')
A('Landroid/util/Log;.d' in r3.stdout, 'c2/s.a 就是 Log.d（"c2/s 只是日志"这条判读有据）')
r4 = subprocess.run([sys.executable, TOOL, '--body', 'Lc2/s;', 'g'], capture_output=True, text=True,
                    encoding='utf-8', errors='ignore')
A('Log;.isLoggable' in r4.stdout, 'c2/s.g() 是 Log.isLoggable（不是"相机连没连"）')
r5 = subprocess.run([sys.executable, TOOL, '--body', 'Lc2/k;', 'c'], capture_output=True, text=True,
                    encoding='utf-8', errors='ignore')
A('Ljava/util/ArrayList;.iterator' in r5.stdout, 'c2/k.c(url) 是查命令表（ArrayList 遍历比较）')

print('=== D. 本轮没有碰 App / APK ===')
# 第 67 轮起页面又改了（连接链），所以"第 65 轮没碰 App"这条要拿**第 65 轮当时那版页面**做对照：
# `app/base.before_r67.html` = 第 64 轮产物、也正是第 65/66 两轮没动过的状态（第 65 轮纯静态、第 66 轮只出方案）。
# 判据没放松（仍是"md5 逐位相同"），只是把被测文件换成那一版。
SNAP = os.path.join(ROOT, 'app', 'base.before_r67.html')
hs = hashlib.md5(io.open(SNAP, 'rb').read()).hexdigest() if os.path.exists(SNAP) else '(缺快照)'
A(hs == PAGE_MD5, '第 65 轮当时的页面（base.before_r67.html）md5 == 第 64 轮产物 %s（实为 %s）'
  % (PAGE_MD5[:12], hs[:12]))
A('App 一个字节都没动' in spec, '规格里显式写了"App 零改动"（§1 后置条件 / §6 第 5 条）')
A(os.path.exists(os.path.join(ROOT, 'official_app', 'cgi_table.txt')), '工具产物 cgi_table.txt 还在（可重生成）')

print()
print('第 65 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
