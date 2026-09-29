# -*- coding: utf-8 -*-
"""第 43 轮验收：录「日常挂机」+ 全站中英名 + 清档位残留 + 修 r42 的 3 个 bug
跑法：python scripts/dv_r43.py"""
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recipe_names import NAME_MAP                      # noqa: E402
from recipe_wheel import wheel_svg                     # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'D:\workspace\om3-handbook'
TMP = r'C:\Users\82302\AppData\Local\Temp'
src = io.open(SRC + r'\app\base.html', encoding='utf-8').read()
IMG = SRC + r'\apk\assets\images'
DEC = json.JSONDecoder()
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


def blk(key):
    i = src.find(key)
    p = src.index('=', i) + 1
    while src[p].isspace():
        p += 1
    return DEC.raw_decode(src, p)[0]


print('=== ① 数据体量 + 三处一致 ===')
REC = blk('window.__OM3RECIPES__')
IDX = blk('var IDX')
PH = blk('window.__OM3PHOTOS__')
PT = blk('window.__OM3PHOTOTAGS__')
SC = blk('window.__OM3SC__')
cards = re.findall(r'<div class="card" id="r-([^"]+)">', src)
A(len(REC) == 80, '配方 80 条（原站 78 + 日常挂机 + 第 55 轮的 Porta 400 Print；实测 %d）' % len(REC))
A(len(cards) == 77, '卡片 77 张（58 + 第 55 轮 19；实测 %d）' % len(cards))
A(len(IDX) == 129, '搜索索引 129 条（100 + 10 个候选档槽位 + 第 55 轮 19 条；实测 %d）' % len(IDX))
A(len(PH) == 77 and len(PT) == 534,
  '图库 %d / 标签 %d（期望 77 / 534 = 60/431 + 第 55 轮补的 17 条配方 / 103 张图）' % (len(PH), len(PT)))
A(len(SC) == 18, '场景 18 个（雨天并入「雾 / 阴天 / 雨天」；第 57 轮删了「婚礼聚会 / 儿童亲子」（没实拍 → 改成搜索找风格）；实测 %d）' % len(SC))

print('=== ② 修掉的 3 个 r42 bug ===')
dupc = [k for k in set(cards) if cards.count(k) > 1]
A(not dupc, '卡片 id 无重复（重复：%s）' % (dupc or '无'))
ids = set(re.findall(r'\bid="([^"]+)"', src))
A('r-ian-will_kinda-portra' not in ids, '旧锚点 r-ian-will_kinda-portra 已不存在')
k = [x for x in IDX if x['h'] == 'r-ian-will_kinda-portra-v2']
A(len(k) == 1, '索引里 Kinda Portra 指向 …-v2（%d 条）' % len(k))
A('#plan' not in src, '已无 #plan（目录/jumpbar 的死链都清了）')

print('=== ③ 锚点一致性（一个死的都不能有）===')
A(not [x['h'] for x in IDX if x['h'].startswith('r-') and x['h'] not in ids],
  '索引锚点全在：%s' % ([x['h'] for x in IDX if x['h'].startswith('r-') and x['h'] not in ids] or '无'))
A(not [x['h'] for x in IDX if not x['h'].startswith(('r-', 'k-', 'oC'))],
  '索引里没有来路不明的锚点')
A(not [it['i'] for x in SC for it in x['items'] if it['i'] not in ids], '场景 i 锚点全在')
A(not [it['os'] for x in SC for it in x['items'] if it.get('os') and it['os'] not in ids], '场景 os 锚点全在')
dead = sorted(l for l in set(re.findall(r'href="#([^"]+)"', src)) if l not in ids and "'" not in l)
A(not dead, '目录链接无死链（%s）' % (dead or '无'))

print('=== ④ 改名（中文名（English））===')
R = dict((r['slug'], r) for r in REC)
# 旧名从"动手前的快照"里取（唯一真源），避免跟新名里的英文尾巴混起来
_bak = SRC + r'\app\base.before_r43b.html'
OLD = {}
if os.path.exists(_bak):
    _bs = io.open(_bak, encoding='utf-8').read()
    _i = _bs.find('window.__OM3RECIPES__')
    _p = _bs.index('=', _i) + 1
    while _bs[_p].isspace():
        _p += 1
    for _r in DEC.raw_decode(_bs, _p)[0]:
        OLD[_r['slug']] = _r['n']
pairs = [(_r['n'], NAME_MAP[_r['slug']]) for _r in REC
         if _r['slug'] in NAME_MAP and _r['slug'] in OLD and OLD[_r['slug']] != _r['n']]
A(bool(pairs), '从快照里取到 %d 条旧→新对照' % len(pairs))
tmp = src
for _a, _b in pairs:
    tmp = tmp.replace(_b, '\x00')
leftover = []
for _a, _b in pairs:
    n = len(re.findall(r'(?<![A-Za-z0-9])%s(?![A-Za-z0-9])' % re.escape(_a), tmp))
    if n:
        leftover.append('%s×%d' % (_a, n))
A(not leftover, '旧名残留 0 处（%s）' % (leftover[:4] or '无'))
missing = [r['slug'] for r in REC if r['slug'] in NAME_MAP and r['n'] != NAME_MAP[r['slug']]]
A(not missing, '数据里的名字都换成了新名（没换：%s）' % (missing or '无'))
# 卡片标题 == 数据名字
bad = []
for cid in set(cards):
    if cid not in R:
        bad.append(cid + '(数据里没有)')
        continue
    i0 = src.find('id="r-%s"' % cid)
    m = re.search(r'<span class="cname">([^<]*)</span>', src[i0:i0 + 400])
    if not m or m.group(1) != R[cid]['n']:
        bad.append('%s:%r≠%r' % (cid, m and m.group(1), R[cid]['n']))
A(not bad, '每张卡标题 = 数据名字（%d 张；不一致 %s）' % (len(set(cards)), bad[:3] or '无'))
A(src.count('真实（Real）') > 0 and src.count('日常挂机') > 0, '中英名已生效（真实（Real） / 日常挂机）')

print('=== ⑤ 新配方「日常挂机」六处齐全 ===')
NEW = dict((r['slug'], r) for r in REC).get('momo_everyday')
A(bool(NEW), '数据里有 momo_everyday')
if NEW:
    A(NEW['v'] == [1, 2, 0, -1, -1, 0, 1, 1, 1, 0, -1, 0], '色轮 12 值 = 图上原文（%s）' % NEW['v'])
    A(NEW['wba'] == 0 and NEW['wbg'] == 0 and NEW['wb'] == 'Auto', '白平衡 Auto A0 G0')
    A(max(abs(x) for x in NEW['v']) <= 5, '取值在库内量程 [−5,5] 内')
A('id="r-momo_everyday"' in src, '① 卡片在')
A('r-momo_everyday' in [x['h'] for x in IDX], '② 搜索索引在')
A(PH.get('momo_everyday') == ['momo_everyday__s01.jpg'], '③ 图库登记在（%s）' % PH.get('momo_everyday'))
A('momo_everyday__s01.jpg' in PT, '④ 图标签登记在（%s）' % PT.get('momo_everyday__s01.jpg'))
A(os.path.exists(os.path.join(IMG, 'momo_everyday__s01.jpg')), '⑤ 图片文件在 assets/images 里')
A(any(it['i'] == 'r-momo_everyday' for it in SC[0]['items']),
  '⑥ 场景对比「%s」里有它' % SC[0]['label'])
i0 = src.find('id="r-momo_everyday"')
sec = re.findall(r'<details class="sec" id="([^"]+)"', src[:i0])[-1]
A(sec == 'mode-C1', '卡片落在不偏移分区（实际 #%s）' % sec)

print('=== ⑥ 色轮渲染 / 白平衡徽标 ===')
by_slug = dict((r['slug'], r) for r in REC)
okn = failn = 0
deltas, nowheel = [], []
for cid in set(cards):
    r = by_slug.get(cid)
    if not r:
        continue
    k0 = src.find('id="r-%s"' % cid)
    k1 = src.find('<div class="card" id="r-', k0 + 10)
    seg = src[k0:(k1 if k1 > 0 else src.find('</details>', k0))]
    # ⚠ 只能在**本卡范围**里找 SVG：写成 src[k0:] 会让"没轮子的卡"抓到下一张卡的 SVG，
    #    把"没有轮子"误判成"轮子和数据不一致"（2026-09-25 我自己踩过这个坑）
    m = re.search(r'<svg viewBox="0 0 270 270" class="wheel">.*?</svg>', seg, re.S)
    if m is None:
        nowheel.append(cid)
        continue
    if m.group(0) == wheel_svg(r['v']):
        okn += 1
    else:
        failn += 1
        deltas.append((cid, r['t']))
A(failn == 0, '有轮子的卡 100%% 与数据一致（一致 %d 张，不一致 %d 张 %s）' % (okn, failn, deltas[:2] or ''))
A(len(nowheel) == 8 and all(by_slug[c]['t'] in ('MONO', 'BASIC_COLOR') for c in nowheel),
  '无轮卡 %d 张，全是 MONO / BASIC_COLOR（%s）' % (len(nowheel), ','.join(by_slug[c]['t'] for c in nowheel)))
bad = [c for c in nowheel if 'class="nomon"' not in src[src.find('id="r-%s"' % c):src.find('id="r-%s"' % c) + 400]]
A(not bad, '无轮卡都带「不走色轮」占位（缺 %s）' % (bad or '无'))


def wbsig(r):
    a, g = r.get('wba') or 0, r.get('wbg') or 0
    left = ('A+%d' % a) if a > 0 else (('B%d' % abs(a)) if a < 0 else 'A0')
    right = ('G+%d' % g) if g > 0 else (('M%d' % abs(g)) if g < 0 else 'G0')
    return '%s %s' % (left, right)


bad, nobadge = [], []
for cid in set(cards):
    r = by_slug.get(cid)
    if not r:
        continue
    k0 = src.find('id="r-%s"' % cid)
    m = re.search(r'<span class="slot">([^<]*)</span>', src[k0:k0 + 400])
    in_sec = re.findall(r'<details class="sec" id="([^"]+)"', src[:k0])[-1] in (
        'mode-C1', 'mode-C2', 'mode-C3', 'mode-C4', 'mode-C5')
    if m:
        if m.group(1) != wbsig(r):
            bad.append('%s:%r≠%r' % (cid, m.group(1), wbsig(r)))
    elif in_sec:
        bad.append('%s: 分区卡却没徽标' % cid)
    else:
        nobadge.append(cid)
A(not bad, '分区卡的白平衡徽标 = 数据签名（不一致 %s）' % (bad[:3] or '无'))
A(True, '池里的卡不挂徽标（靠分组标题「偏移 A0 G0」），共 %d 张' % len(nobadge))
bad = [x['h'] for x in IDX if x['h'].startswith('r-') and x.get('sl') != wbsig(by_slug[x['h'][2:]])]
A(not bad, '索引里 paneA 条目的 sl = 白平衡签名（不一致 %s）' % (bad[:3] or '无'))

print('=== ⑦ 配方合集侧不再有「档位」残留 ===')
pa = src[src.find('<div id="paneA"'):src.find('<div id="paneB"')]
pb = src[src.find('<div id="paneB"'):]
for kw in ('C1 档', 'C2 档', 'C3 档', 'C4 档', 'C5 档', '备选池', 'C1–C5'):
    A(kw not in pa, '配方合集里无「%s」（%d 处）' % (kw, pa.count(kw)))
A(not re.findall(r'C\d · 槽', pa), '配方合集里无「C? · 槽」')
tiers = sorted(set(re.findall(r'<div class="omode" id="(oC\d+)"', pb)))
slots = sorted(set(re.findall(r'<div class="oslot" id="(oC[^"]+)"', pb)))
A(len(tiers) == 10, '档位推荐侧 10 个候选档（实测 %d：%s）' % (len(tiers), tiers))
A(len(slots) == 31, '档位推荐侧 31 个槽位（实测 %d）' % len(slots))
A('档位推荐' in pb, '档位推荐侧仍叫「档位推荐」')

print('=== ⑨ 「怎么挑这 5 个」一览表 ===')
A('id="opick"' in src and 'data-goto="opick"' in src, '第 45 轮加的一览节 #opick 在，跳转条也指得到')
rows = re.findall(r'<tr><td class="og"><a href="#(oC\d+)">([^<]*)</a></td>'
                  r'<td class="mono"><b>([^<]*)</b></td>', src)
A(len(rows) == 10, '一览表 10 行（实测 %d）' % len(rows))
# 表里每行的签名必须 = 那一档卡片上的签名（C4 的 chip 带 "Auto "，比的时候抹掉）
bad = []
for tid, tname, wb in rows:
    i0 = src.find('<div class="omode" id="%s">' % tid)
    m = re.search(r'<span class="omchip wb">白平衡 <b>([^<]*)</b>', src[i0:i0 + 2500])
    chip = (m.group(1) if m else '').replace('Auto ', '')
    if chip != wb:
        bad.append('%s 表=%s 卡=%s' % (tid, wb, chip))
A(not bad, '表里的签名 = 档位卡上的签名（不一致 %s）' % (bad[:3] or '无'))
sig = dict((t, w) for t, _, w in rows)
A(sig.get('oC1') == sig.get('oC3'),
  '一览表点出的关键事实成立：C1 与 C3 同签名（%s / %s）' % (sig.get('oC1'), sig.get('oC3')))
A(len(set(sig.values())) == 9, '10 个候选档落在 %d 个不同签名上（期望 9）' % len(set(sig.values())))
# 「5 个档位」这种旧说法在 paneB 里必须消失
# （paneE「我的配方」里那句「不是所有机器都有 5 个档位」说的是相机事实，不算 —— 所以要把范围掐到 paneB 结尾）
_pb_only = src[src.find('<div id="paneB"'):src.find('<div id="paneC"')]
A('5 个档位' not in _pb_only and '5 个 C 档全部' not in _pb_only,
  '档位推荐页（只到 paneB 结尾）里已无「5 个档位 / 5 个 C 档全部」的旧说法')
A('10 个候选档（挑 5 个）' in src, '目录（toc2）里那条也改成了「10 个候选档（挑 5 个）」')
# 组合只在 #opick 里数（档位卡片里也有 .omwhy，别数进来）
op = src[src.find('id="opick"'):src.find('<details class="sec" id="oskin"')]
for k, combo in enumerate(re.findall(r'<div class="omwhy"><b>([^<]*?)：</b>(.*?)<br>', op, re.S)):
    cs = re.findall(r'href="#(oC\d+)"', combo[1])
    if len(cs) != 5 or len(set(cs)) != 5:
        bad.append('组合 %d：%s' % (k, cs))
A(not bad, '4 组「照着挑」都是 5 个不重复的档（%s）' % (bad[:2] or '无'))

print('=== ⑩ 第 46 轮：扫码失败的 out bug + 「想填满」折叠 ===')
# 每处 line(out, 都必须在 scanSay() 里面（外层拿不到 out 就是那个 bug）
_allout = [m.start() for m in re.finditer(r'line\(out,', src)]


def _in_comment(t, k):
    """k 是否落在注释里（避免把"修 bug 的说明文字"当成真代码）。"""
    a = t.rfind('/*', 0, k)
    b = t.rfind('*/', 0, k)
    if a > b:
        return True
    c = t.rfind('//', 0, k)
    return c > max(a, b) and '\n' not in t[c:k]


_code_out = [k for k in _allout if not _in_comment(src, k)]
dangling = [k for k in _code_out if 'function scanSay' not in src[max(0, k - 400):k]]
A(not dangling, '没有悬空的 line(out, …)（真代码 %d 处全在 scanSay 里；悬空 %d 处）'
  % (len(_code_out), len(dangling)))
A("scanSay('打不开摄像头" in src, '扫码失败回调改成走 scanSay()（页面提示 + 弹条 + 日志）')
ff = re.findall(r'<details class="fold ffill"><summary>([^<]*)</summary>(.*?)</details>', src, re.S)
A(len(ff) == 5, 'C6–C10 各一个「想填满」折叠（实测 %d）' % len(ff))
A(all('挪 ' in body and '<table' in body for _, body in ff), '每个折叠里都有「挪 N 格」表')
A(all(2 <= len(re.findall(r'<tr><td class="og">', body)) <= 6 for _, body in ff),
  '每张候选表 2–6 行')
A(len(set(re.findall(r'已在 (C\d+) 档', src))) >= 3, '已在别档的配方被标出来了（%s）'
  % sorted(set(re.findall(r'已在 (C\d+) 档', src))))
A('本方案没有替你塞进去' in src, '明说"没有替你塞进去"（守住 0 位移）')

print('=== ⑧ 运行时 ===')
JS = r"""
setTimeout(function(){
  var o = [];
  function ok(c, m){ o.push((c ? '[OK ] ' : '[FAIL] ') + m); }
  function vis(id){ var e = document.getElementById(id); return e ? !e.classList.contains('hide') : false; }
  function tab(p){ return document.querySelector('#barABC button[data-p="' + p + '"]'); }
  setTimeout(function(){
    ok(window.__errs.length === 0, '① 首屏 0 JS 报错（' + window.__errs.length + '）');
    var c = document.getElementById('r-momo_everyday');
    ok(!!c, '② 新卡片在 DOM 里');
    ok(!!c && c.querySelector('.cname').textContent === '日常挂机', '② 新卡片标题正确');
    ok(!!c && c.querySelector('.slot').textContent === 'A0 G0', '② 新卡片徽标 A0 G0');
    var img = c && c.querySelector('img[data-im]');
    ok(!!img && /momo_everyday__s01\.jpg$/.test(img.getAttribute('src') || ''), '② 新卡片样片已解析出 src（' + (img && img.getAttribute('src')) + '）');
    ok(document.querySelectorAll('#paneA .card').length === 77, '③ 配方合集 77 张卡（58 + 第 55 轮 19）（' + document.querySelectorAll('#paneA .card').length + '）');
    /* 搜索「日常」→ 应能搜到新配方 */
    var q = document.getElementById('tocq');
    tab('A').click();
    setTimeout(function(){
      q.value = '日常';
      q.dispatchEvent(new Event('input', {bubbles: true}));
      setTimeout(function(){
        var res = document.getElementById('tocres');
        ok(res && res.textContent.indexOf('日常挂机') >= 0, '④ 搜索「日常」能搜到新配方');
        var hit = res && res.querySelector('[data-jump="r-momo_everyday"]');
        if (hit) { hit.click(); }
        setTimeout(function(){
          ok(!!document.getElementById('r-momo_everyday'), '④ 点搜索结果后卡片仍在（跳转没报错）');
          tab('B').click();
          setTimeout(function(){
            ok(vis('paneB'), '⑤ 能切到档位推荐');
            ok(document.querySelectorAll('#modetabs button').length === 10, '⑤ 档位推荐 10 个候选档切换（' + document.querySelectorAll('#modetabs button').length + '）');
            tab('C').click();
            setTimeout(function(){
              ok(vis('paneC'), '⑥ 场景对比页正常');
              var found = false;
              try { found = document.body.innerHTML.indexOf('日常挂机') >= 0; } catch(e){}
              ok(found, '⑥ 场景对比页里能找到「日常挂机」');
              ok(window.__errs.length === 0, '⑦ 全程 0 JS 报错（' + window.__errs.length + '）');
              var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
              document.body.appendChild(d);
            }, 700);
          }, 700);
        }, 700);
      }, 700);
    }, 700);
  }, 1500);
}, 2600);
"""
k = src.find('<body')
j = src.find('>', k) + 1
head = ('<script>window.__OM3_APP__=1;window.__errs=[];window.onerror=function(m,s2,l){window.__errs.push(m+" @"+l)};'
        'window.addEventListener("unhandledrejection",function(e){window.__errs.push("rej:"+e.reason)});</script>')
out = src[:j] + head + src[j:].replace('</body>', '<script>' + JS + '</script></body>', 1)
p = TMP + r'\dv_r43.html'
io.open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\omr43'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--hide-scrollbars', '--user-data-dir=' + ud, '--window-size=560,900',
                    '--virtual-time-budget=25000', '--dump-dom', 'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk < 0:
    print('  [FAIL] 探针没拿到输出')
    F += 1
else:
    body = dom[kk:].split('>', 1)[1].split('</pre>')[0]
    print(body)
    K += body.count('[')
    F += body.count('[FAIL]')
print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
