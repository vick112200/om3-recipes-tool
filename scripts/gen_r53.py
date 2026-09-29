# -*- coding: utf-8 -*-
"""第 53 轮生成器（幂等）· v3.7 —— 摄影师意见落地

用户拍板「你做吧」，按我给的判断做三件：
  ① 雨天并进「雾 / 阴天 / 雨天」（场景 21 → 20）—— 实测雨天的 6 条与雾/阴天的 8 条**一条不重合**，
     而雨/雾/阴天是**同一类光**（柔、平、低对比、偏冷），配方本就该同一套；素材里 `雨` 标签 0 张。
  ② 暖光 / 灯光下：**不收窄**（8 条方向都对），改为给这 8 条各加一行**现场提示**
     「先设 AUTO + 关『保持暖色调』；偏色压不住就按 M 方向拨 1 格」。
  ③ 参数解读**不加长**（这条是"不做"，只在文档里记一句）。
配套：把断言里的场景数 21 → 20、下拉项 27 → 26、以及引用旧场景名的断言一起更新
（dv_r42 / dv_r43 / dv_scene39 / dv_r50 / dv_r51 / dv_r52）。
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
from om3_profile import gen6, profile   # noqa: E402

ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r53.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r53.html（= v3.6 源码）')

NEWLAB = '雾 / 阴天 / 雨天'
WARM_HINT = ('<div class="row"><span class="mk">暖光现场</span><span class="mv tip">'
             '先设 <b>AUTO + 关「保持暖色调」</b>；偏色压不住就按 <b>M 方向拨 1 格</b>'
             '（钨丝 / 廉价 LED 偏黄绿，品红能救肤色）</span></div>')


def grab(var, start=0):
    i = s.index('window.%s' % var, start)
    j = s.index('=', i) + 1
    while s[j] in ' \n':
        j += 1
    oc = s[j]
    cc = {'[': ']', '{': '}'}[oc]
    d = 0
    k = j
    while k < len(s):
        if s[k] == '"':
            k += 1
            while k < len(s):
                if s[k] == chr(92):
                    k += 2
                    continue
                if s[k] == '"':
                    break
                k += 1
        elif s[k] == oc:
            d += 1
        elif s[k] == cc:
            d -= 1
            if d == 0:
                return json.loads(s[j:k + 1])
        k += 1
    raise SystemExit('抠不出来：' + var)


SC = grab('__OM3SC__')
SCENES = grab('__OM3SCENES__')

# ---------------- ① 合并雨天 ----------------
n_rain = 0
new_sc = []
for sc in SC:
    if sc['k'] == 'rain':
        n_rain = len(sc['items'])
        continue
    if sc['k'] == 'mist':
        sc['label'] = NEWLAB
    new_sc.append(sc)
SC = new_sc
SCENES = [x for x in SCENES if x['k'] != 'rain']
for x in SCENES:
    if x['k'] == 'mist':
        x['label'] = NEWLAB
        x['kw'] = sorted(set(list(x.get('kw') or []) + ['雨', '雨后', '水汽', '玻璃反光']))

s = s.replace('21 个场景，图按画面自动归类', '20 个场景，图按画面自动归类')
s = s.replace('<option value="s:rain">雨天</option>', '')
s = s.replace('<option value="s:mist">雾与阴天</option>', '<option value="s:mist">%s</option>' % NEWLAB)
print('  ✓ ① 雨天 (%d 条) 并入「%s」；场景 21 → %d；下拉选项已改' % (n_rain, NEWLAB, len(SC)))

# ---------------- ② 暖光 8 条：加一行"暖光现场" ----------------
n_hint = 0
for sc in SC:
    if sc['label'] != '暖光 / 灯光下':
        continue
    for it in sc['items']:
        fd = it.get('fd') or ''
        if '暖光现场' in fd or not fd:
            continue
        it['fd'] = fd.replace('</div></details>', WARM_HINT + '</div></details>', 1)
        n_hint += 1
print('  ✓ ② 暖光场景 %d 条各加了一行「暖光现场」提示' % n_hint)

# ---------------- 写回两个数据段（现算偏移，别用过期索引） ----------------
for var, data in (('__OM3SCENES__', SCENES), ('__OM3SC__', SC)):
    i0 = s.index('window.%s = ' % var)
    j0 = i0 + s[i0:].index('];') + 1
    s = s[:i0] + 'window.%s = ' % var + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + s[j0:]
print('  ✓ 数据段已写回（SCENES %d 个场景 / SC %d 个场景）' % (len(SCENES), len(SC)))

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))

# ---------------- 配套：更新断言里的场景数 / 旧场景名 ----------------
FIX = [
    ('scripts/dv_r43.py', "A(len(SC) == 21, '场景 21 个（实测 %d）' % len(SC))",
     "A(len(SC) == 20, '场景 20 个（雨天已并入「雾 / 阴天 / 雨天」；实测 %d）' % len(SC))"),
    ('scripts/dv_r42.py', "A(len(SC) == 21, '③ __OM3SC__ 仍 21 个场景（%d）' % len(SC))",
     "A(len(SC) == 20, '③ __OM3SC__ 20 个场景（雨天已并入雾/阴天；%d）' % len(SC))"),
    ('scripts/dv_scene39.py', "A(len(SC) == 21, '④ __OM3SC__ 有 21 个场景（实测 %d）' % len(SC))",
     "A(len(SC) == 20, '④ __OM3SC__ 有 20 个场景（实测 %d）' % len(SC))"),
    ('scripts/dv_scene39.py', "ok(sel.options.length === 27, '① 下拉 27 项（6 实拍 + 21 场景，实测 ' + sel.options.length + '）');",
     "ok(sel.options.length === 26, '① 下拉 26 项（6 实拍 + 20 场景，实测 ' + sel.options.length + '）');"),
    ('scripts/dv_r50.py', "A(len(SC) == 21, '__OM3SC__ 仍是 21 个场景（%d）' % len(SC))",
     "A(len(SC) == 20, '__OM3SC__ 20 个场景（雨天并入雾/阴天；%d）' % len(SC))"),
    ('scripts/dv_r51.py', "    if sc['label'] not in ('雾与阴天', '雨天', '雪景', '日落晚霞', '夜景霓虹', '室内暖光', '逆光大光比'):",
     "    if sc['label'] not in ('雾 / 阴天 / 雨天', '雪景', '日落晚霞', '夜景霓虹', '暖光 / 灯光下', '逆光大光比'):"),
    ('scripts/dv_r51.py', "        if sc['label'] == '雾与阴天' and sw in ('清淡', '寡淡'):",
     "        if sc['label'] == '雾 / 阴天 / 雨天' and sw in ('清淡', '寡淡'):"),
    ('scripts/dv_r51.py', "        if sc['label'] == '室内暖光' and d >= 8:",
     "        if sc['label'] == '暖光 / 灯光下' and d >= 8:"),
    ('scripts/dv_r51.py', "mist = [it['n'] for sc in SC if sc['label'] == '雾与阴天' for it in sc['items']]",
     "mist = [it['n'] for sc in SC if sc['label'] == '雾 / 阴天 / 雨天' for it in sc['items']]"),
    ('scripts/dv_r51.py', "  '「避开阴天」的还在雾与阴天外面（现在：%s）' % '、'.join(mist[:5]))",
     "  '「避开阴天」的还在雾/阴天外面（现在：%s）' % '、'.join(mist[:5]))"),
    ('scripts/dv_r51.py', "    ok(sl.length > 0, '雾与阴天有卡片（' + sl.length + ' 条）');",
     "    ok(sl.length > 0, '雾 / 阴天 / 雨天有卡片（' + sl.length + ' 条）');"),
    ('scripts/dv_r52.py', "want = {'雾与阴天': 8, '雨天': 6, '雪景': 6, '森林绿意': 8, '夜景霓虹': 10}",
     "want = {'雾 / 阴天 / 雨天': 8, '雪景': 6, '森林绿意': 8, '夜景霓虹': 10}"),
    ('scripts/dv_r52.py', "A(len(SC) == 21, '场景总数仍 21（雨天没并掉，避免牵动一堆断言；解法与雾/阴天一致）')",
     "A(len(SC) == 20, '场景总数 20（雨天已并入「雾 / 阴天 / 雨天」）')"),
    ('scripts/dv_r52.py', """rain_tag = sum(1 for i in (sc.get('雨天') or []) if '雾' in (PT.get(i['f']) or []))
A(rain_tag >= 3, '雨天优先用电雾池照片（%d/%d 张带「雾」标签）—— 照片库里`雨`标签 0 张，只能这么配' % (rain_tag, len(sc.get('雨天') or [])))""",
     """mist_tag = sum(1 for i in (sc.get('雾 / 阴天 / 雨天') or []) if '雾' in (PT.get(i['f']) or []))
A(mist_tag >= 4, '雾/阴天/雨天用的是雾池照片（%d/%d 张带「雾」标签）—— 照片库里`雨`标签 0 张' % (mist_tag, len(sc.get('雾 / 阴天 / 雨天') or [])))"""),
]
for f, a, b in FIX:
    fp = os.path.join(ROOT, f)
    t = io.open(fp, encoding='utf-8').read()
    if a not in t:
        print('    （跳过：%s 里没这句）' % f)
        continue
    io.open(fp, 'w', encoding='utf-8', newline='').write(t.replace(a, b))
    print('  ✓ 断言更新：%s' % f)
