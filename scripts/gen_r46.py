# -*- coding: utf-8 -*-
"""第 46 轮 · 两件事（幂等）

A) 修一个**真 bug**：扫码失败回调里 `line(out, …)` —— `out` 在 `scanSay()` 重构时被收进函数内部，
   外层回调没跟着改 ⇒ 打开摄像头失败时抛 `ReferenceError: out is not defined`
   （`dv_clickall` 里报的 `REJ out is not defined`，v2.34 之前就有，本轮修）。
   改成调用现成的 `scanSay()`（页面提示 + 弹条 + 日志，本来就是给扫码错误用的）。

B) 给 C6–C10 各加一个「想填满这两格？」折叠：**列出**最接近的候选（按白平衡位移升序），
   但**不替用户决定**——只是把"要挪几格"摊开，用户自己选。守住「新档 0 位移」这条底线。
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
D = json.JSONDecoder()
LOG = []

s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r46.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r46.html')


def blk(key):
    i = s.find(key)
    p = s.index('=', i) + 1
    while s[p].isspace():
        p += 1
    return D.raw_decode(s, p)[0]


REC = blk('window.__OM3RECIPES__')
cards = set(re.findall(r'<div class="card" id="r-([^"]+)"', s))


def sig(r):
    a, g = r['wba'] or 0, r['wbg'] or 0
    left = ('A+%d' % a) if a > 0 else (('B%d' % abs(a)) if a < 0 else 'A0')
    right = ('G+%d' % g) if g > 0 else (('M%d' % abs(g)) if g < 0 else 'G0')
    return '%s %s' % (left, right)


# ================================================================ A) 修 bug
print('=== A) 修扫码失败回调里的 out ===')
OLD = """      }, function(err){
        $('scanOut').innerHTML = '';
        line(out, '打不开摄像头：' + err.message, 'err');
        line(out, '检查：系统设置里给本 app 开「相机」权限；或直接用「手动填」。', 'warn');
        stopScan();
      });"""
NEW = """      }, function(err){
        $('scanOut').innerHTML = '';
        /* 2026-09-25 修：这里原来写的是 line(out, …)，但 out 在 scanSay() 里才是局部变量，
           外层拿不到 ⇒ 打开摄像头失败时抛 ReferenceError（日志里表现为 REJ out is not defined）。
           改用现成的 scanSay()：页面提示 + 弹条 + 日志三处一起给。 */
        scanSay('打不开摄像头：' + err.message, 'err');
        scanSay('检查：系统设置里给本 app 开「相机」权限；或直接用「手动填」。', 'warn');
        stopScan();
      });"""
if "line(out, '打不开摄像头" in s:
    s = s.replace(OLD, NEW, 1)
    LOG.append('  ✅ 扫码失败回调：line(out, …) → scanSay(…)')
elif 'scanSay(\'打不开摄像头' in s:
    LOG.append('  · 已修过，跳过')
else:
    LOG.append('  ⚠ 没匹配到扫码失败回调，需人工确认')
if 'line(out,' in s:
    LOG.append('  ⚠ 还有 %d 处悬空的 line(out, 需人工确认' % s.count('line(out,'))

# ================================================================ B) C6–C10「想填满这两格？」
print('\n=== B) 给 C6–C10 加「想填满这两格？」 ===')
by = dict((r['slug'], r) for r in REC)
added = 0
# 名字 → 已经占着的候选档（给「想填满」那列标「已在 Cn 档」用）
othertier = {}
for mm in re.finditer(r'<div class="oslot" id="(oC\d+)-[^"]+">.*?<span class="osname">([^<]*)</span>', s, re.S):
    othertier.setdefault(mm.group(2), mm.group(1)[2:])
# ⚠ 从后往前做：每加一个折叠都会让后面的偏移变，倒着做前面的位置才不受影响
for tag in ['10', '9', '8', '7', '6']:
    tid = 'oC' + tag
    i0 = s.find('<div class="omode" id="%s">' % tid)
    assert i0 > 0, '找不到 ' + tid
    j = s.find('<div class="omode" id="', i0 + 10)
    if j < 0:
        j = s.find('<details class="sec" id="opink"', i0)
    seg = s[i0:j]
    if 'class="fold ffill"' in seg:
        continue
    wbm = re.search(r'<span class="omchip wb">白平衡 <b>([^<]*)</b>', seg)
    ta, tg = None, None
    for r in REC:                              # 用第一个槽的原生签名当本档签名基准
        pass
    first = re.search(r'<div class="oslot" id="' + tid + r'-1">', seg)
    sid = re.search(r'<div class="oslot" id="' + tid + r'-1">(.*?)<span class="osname">', seg, re.S)
    # 直接看第 1 个槽的 osvals 反推签名不可靠，改用「该档 omchip + 数据里签名一致的配方」
    # omchip 里就是签名文字，直接用
    wbs = wbm.group(1).replace('Auto ', '') if wbm else ''
    # 反查 (a,g)
    def parse(sg):
        mm = re.match(r'([AB])([+-]?\d+)\s+([GM])([+-]?\d+)$', sg)
        if not mm:
            return None
        a = int(mm.group(2)) * (1 if mm.group(1) == 'A' else -1)
        g = int(mm.group(4)) * (1 if mm.group(3) == 'G' else -1)
        return (a, g)
    p = parse(wbs)
    assert p, '%s 解析签名失败：%r' % (tid, wbs)
    ta, tg = p
    inthis = set(re.findall(r'<span class="osname">([^<]*)</span>', seg))
    cands = []
    for r in REC:
        if r['t'] != 'COLOR':
            continue
        d = abs((r['wba'] or 0) - ta) + abs((r['wbg'] or 0) - tg)
        if 1 <= d <= 3 and r['n'] not in inthis:
            cands.append((d, r))
    cands.sort(key=lambda x: (x[0], x[1]['n']))
    # 「已经在别的候选档里」的，标出来 —— 免得建议一个别档已经占着的配方
    def note_of(r):
        if r['n'] in othertier and othertier[r['n']] != tid:
            return '已在 C%s 档' % othertier[r['n']]
        if r['slug'] in cards:
            return '配方合集里有卡片'
        return '只在固定色温表里'
    rows = ''.join('<tr><td class="og">%s</td><td class="mono">%s</td>'
                   '<td class="mono">挪 %d 格</td><td>%s</td></tr>'
                   % (r['n'], sig(r), d, note_of(r))
                   for d, r in cands[:6])
    empty = 4 - len(re.findall(r'<div class="oslot" id="' + tid + r'-[1-4]">', seg))
    FOLD = (
        '<details class="fold ffill"><summary>想要把这一档填满（还有 %d 格空着）？</summary>'
        '<div class="foldbody">'
        '<b>本档白平衡是 %s，原生签名只有 %d 卷 —— 要再塞，就得动白平衡。</b>'
        '下面这几卷是<b>离本档最近</b>的（按「挪几格」升序），<b>本方案没有替你塞进去</b>：'
        '一塞，它们的白平衡就不再是作者登记的那个数了。<br>'
        '真要用，把某个空槽的白平衡按本档设，录进去之后按表里的「挪 N 格」预计偏色方向，实拍再微调。'
        '<div class="tw"><table class="otbl"><thead><tr><th>配方</th><th>原生签名</th>'
        '<th>代价</th><th>说明</th></tr></thead><tbody>%s</tbody></table></div>'
        '<p class="onote">另一种更干净的做法：<b>这两格留空，把你自己调好的配方录进去</b> —— '
        '自配配方没有"作者原始白平衡"这回事，放在哪一档都不算改动别人。</p>'
        '</div></details>'
    ) % (empty, wbs, len(inthis), rows)
    k = seg.find('<div class="omwhy">')
    assert k > 0, '%s 找不到 omwhy' % tid
    pos = i0 + k
    s = s[:pos] + FOLD + s[pos:]
    added += 1
    LOG.append('  ✅ %s（%s，空 %d 格）：列出最近 %d 卷' % (tid, wbs, empty, min(6, len(cands))))
LOG.append('  ✅ 共加 %d 个「想填满」折叠' % added)

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n'.join(LOG))
print('写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))

# ================================================================ 自检
print('\n=== 自检 ===')
S = io.open(P, encoding='utf-8').read()
print('挂空的 line(out, ：', S.count('line(out,'))
print('scanSay 修好：', "scanSay('打不开摄像头" in S)
print('「想填满」折叠数：', len(re.findall(r'class="fold ffill"', S)))
ids = set(re.findall(r'\bid="([^"]+)"', S))
print('死链：', sorted(l for l in set(re.findall(r'href="#([^"]+)"', S)) if l not in ids and "'" not in l) or '无')
