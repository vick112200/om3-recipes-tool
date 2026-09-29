# -*- coding: utf-8 -*-
"""第 52 轮生成器（幂等）· v3.6 —— 摄影师视角的三件事

用户拍板：三条都改；「室内暖光」改名「暖光 / 灯光下」。

① 提示行：从"讲原理"改成**现场四句**（白平衡 / 曝光补偿方向 / 先动哪个 / 最容易翻车）
② 「暖光 / 灯光下」（原室内暖光）**重建**：选卡改成"中性或偏冷 + 品红倾向 + 反差别硬"，
   照片从`__OM3PHOTOS__`里挑**夜景/混光**那批（原来用的是雾景照，两头都不对）
③ 场景规模：
   · 雨天：照片库 `雨` 标签 0 张 → 与雾/阴天**同一套解法**，用雾池照片补到 6 条（场景数仍 21，避免牵动一堆断言）
   · 雪景 2→6、森林绿意 1→8、夜景霓虹 6→10（按"打法"分组：压光 / 暖黄霓虹 / 冷调蓝调 / 黑白夜）
   选取规则一律**配方按参数、照片按画面标签**，两边都用现有素材；不够就明说，不硬凑。

⚠ 幂等与破坏性：A 步重写 fgen 折页（可反复跑）；B/C 重写数据段（可反复跑）；
   但 C 会**重建**这 5 个场景的条目 —— 想回退用 `app/base.before_r52.html`。
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
from om3_profile import gen6, profile, wbtxt, sat_word, dir_word, con_word   # noqa: E402

ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r52.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r52.html（= v3.5 源码）')


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
                return json.loads(s[j:k + 1]), i, k + 1
        k += 1
    raise SystemExit('抠不出来：' + var)


REC, _, _ = grab('__OM3RECIPES__')
SC, _, _ = grab('__OM3SC__')
SCENES, snj1, snj2 = grab('__OM3SCENES__')
PH = grab('__OM3PHOTOS__')[0]
PT = grab('__OM3PHOTOTAGS__')[0]
byslug = dict((r['slug'], r) for r in REC)


def html6(g, summary, note=''):
    def row(mk, mv, cls=''):
        mv = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', mv)
        return ('<div class="row"><span class="mk">%s</span><span class="mv%s">%s</span></div>'
                % (mk, (' ' + cls) if cls else '', mv))
    body = (row('画面感觉', g['feel']) + row('色彩重点', g['key']) + row('影调', g['tone'])
            + row('适合', g['good'], 'good') + row('避开', g['bad'], 'avoid') + row('提示', g['tip'], 'tip'))
    if note:
        body += '<div class="row"><span class="mk">来源</span><span class="mv">%s</span></div>' % note
    return ('<details class="fold fgen"><summary>%s <span style="font-weight:400;opacity:.7">（展开看全 6 项）'
            '</span></summary><div class="foldbody">%s</div></details>') % (summary, body)


SUMM = lambda r: ('参数解读 · %s / %s / %s'
                  % (sat_word(profile(r)), dir_word(profile(r)), con_word(profile(r))))
NOTE = '按色轮（12 色轴）、色调曲线、白平衡偏移**从参数直接推导**，不是作者自述'

# ================================================================ A. 重写 58 张卡的 fgen 折页（提示行升级）
nA = 0
# ⚠ fgen 折页离卡片 id 可能很远（前面有样片那一堆 <figure>）→ 先列卡片位置，取"折页前面最近的那个"
_cid = [(m2.start(), m2.group(1)) for m2 in re.finditer(r'<div class="card" id="r-([^"]+)">', s)]


def _slug_at(pos):
    owner = None
    for st, sl in _cid:
        if st < pos:
            owner = sl
        else:
            break
    return owner


for m in list(reversed(list(re.finditer(r'<details class="fold fgen">.*?</details>', s, re.S)))):
    r = byslug.get(_slug_at(m.start()))
    if not r:
        continue
    s = s[:m.start()] + html6(gen6(r), SUMM(r), NOTE) + s[m.end():]
    nA += 1
print('  ✓ A：重写了 %d 张卡的「参数解读」（提示行升级成现场四句）' % nA)

# ================================================================ B. window.SC / __OM3SC__ 文案同步
SCL, _, lj2 = grab('SC')
nb = 0
for sc in SCL:
    for it in sc.get('items') or []:
        r = byslug.get(re.sub(r'^[rk]-', '', it.get('i') or ''))
        if not r:
            continue
        g = gen6(r)
        pre = (it.get('d') or '').split('｜')[0].strip()
        it['dd'] = (pre + '｜ ' + g['feel'] + g['key']) if '自动归类' in pre else (g['feel'] + g['key'])
        it['fs'] = '参数解读 · %s' % (it.get('t') or '')
        it['fd'] = html6(g, '参数解读（按参数推导）')
        it['pb'] = ''
        nb += 1
s = s[:s.index('window.SC')] + 'window.SC = ' + json.dumps(SCL, ensure_ascii=False, separators=(',', ':')) + s[lj2:]
print('  ✓ B：%d 条照片说明同步（含新提示行）' % nb)

# ================================================================ C. 场景：改名 + 重建 5 个场景
LAB = {'室内暖光': '暖光 / 灯光下'}
for sc in SC:
    if sc['label'] in LAB:
        sc['label'] = LAB[sc['label']]
for x in SCENES:
    if x['label'] in LAB:
        x['label'] = LAB[x['label']]
# 页面 #scsel 里的 option 文案也要跟着改（原生控件是逻辑源）
s = s.replace('>室内暖光</option>', '>暖光 / 灯光下</option>')


def photos_of(slug):
    return list(PH.get(slug) or [])


def pick_photo(slug, want_tags, used):
    """按照片标签挑一张没被这个场景用过的图；挑不到就退而取该配方任意一张"""
    ps = photos_of(slug)
    for f in ps:
        tg = PT.get(f) or []
        if any(t in tg for t in want_tags) and f not in used:
            return f
    for f in ps:
        if f not in used:
            return f
    return ps[0] if ps else ''


def slot_of(anchor):
    """这条配方在档位推荐里的位置（沿用现有索引，没有就留空）"""
    for sc in SC:
        for it in sc['items']:
            if it.get('i') == anchor and it.get('os'):
                return it['os'], it['osl']
    return '', ''


CARD_SLUGS = set(m.group(1) for m in re.finditer(r'<div class="card" id="r-([^"]+)">', s))


def cands(rule, want_tags_min=0):
    """按参数挑配方（只用**有卡片、有照片、12 轴数据齐**的 —— 没卡片的跳过去会让"看卡片"按钮跳空）"""
    out = []
    for r in REC:
        if r['slug'] not in CARD_SLUGS:
            continue
        if not photos_of(r['slug']):
            continue
        if len(r.get('v') or []) < 12:
            continue
        p = profile(r)
        if rule(r, p):
            out.append((r, p))
    return out


def mkitem(r, f, sc):
    g = gen6(r)
    it = {'i': 'r-' + r['slug'], 'n': r['n'], 'a': r['a'],
          'sl': (wbtxt(r['wba'], r['wbg']) if r['t'] != 'MONO' else 'A0 G0'),
          't': sc['items'][0]['t'] if sc['items'] else '', 'f': f,
          'd': (sc['items'][0]['d'].split('｜')[0] if sc['items'] else ''),
          'dd': '', 'fd': '', 'fs': '', 'pb': '',
          'os': '', 'osl': ''}
    pre = it['d']
    it['dd'] = (pre + '｜ ' + g['feel'] + g['key']) if pre else (g['feel'] + g['key'])
    it['fs'] = '参数解读 · %s' % it['t']
    it['fd'] = html6(g, '参数解读（按参数推导）')
    it['os'], it['osl'] = slot_of(it['i'])
    return it


def tag_short(sc, r):
    """这一条的三段式风格标签（和页面一致：饱和度 · 冷暖 · 反差）"""
    p = profile(r)
    return '%s · %s · %s' % (sat_word(p), dir_word(p), con_word(p))


def tag_of(sc):
    return sc['items'][0]['t'] if sc['items'] else ''


nC = {}
for sc in SC:
    lab = sc['label']
    if lab not in ('暖光 / 灯光下', '雾与阴天', '雨天', '雪景', '森林绿意', '夜景霓虹'):
        continue
    old = list(sc['items'])
    used = set(it.get('f') for it in old)
    keep, add = [], []

    def keep_or(it, r):
        return r is not None

    if lab in ('雾与阴天', '雨天'):
        # 平光湿冷：非低饱和 + 反差别硬；雨天同一套解法，只是照片用雾池那批
        rule = lambda r, p: sat_word(p) not in ('清淡', '寡淡') and con_word(p) != '硬朗'
        for it in old:
            r = byslug.get(re.sub(r'^[rk]-', '', it['i']))
            if r and rule(r, profile(r)):
                keep.append(it)
        if lab == '雨天':
            keep = []                      # 雨天重建（原来那条用的是雾景照、且没配图池）
            sc['label'] = '雨天'
    elif lab == '暖光 / 灯光下':
        # 中性/偏冷 + 品红倾向 + 反差别硬
        rule = lambda r, p: (p['eff_w'] - p['eff_c'] < 4) and p['wbg'] <= 0 and con_word(p) != '硬朗'
    elif lab == '雪景':
        rule = lambda r, p: (p['eff_w'] - p['eff_c'] < 4) and con_word(p) != '硬朗' \
            and sat_word(p) not in ('寡淡',)
    elif lab == '森林绿意':
        rule = lambda r, p: (p['g'] >= 5 or max(p['v'][8:12]) >= 3) and p['eff_w'] - p['eff_c'] < 8
    elif lab == '夜景霓虹':
        rule = lambda r, p: True

    if lab != '雾与阴天':
        want = {'雨天': ['雾'], '雪景': ['高调'], '森林绿意': ['绿意'],
                '暖光 / 灯光下': ['夜景'], '夜景霓虹': ['夜景']}[lab]
        pool = cands(rule)
        target = {'雨天': 6, '雪景': 6, '森林绿意': 8, '暖光 / 灯光下': 8, '夜景霓虹': 10}[lab]
        if lab == '夜景霓虹':
            # 夜景按"打法"分组，每组最多 3 条：压光 / 暖黄霓虹 / 冷调蓝调 / 黑白夜
            def bucket(r, p):
                if r['t'] == 'MONO':
                    return 'mono'
                d = p['eff_w'] - p['eff_c']
                if p['hi'] <= -3 or con_word(p) == '硬朗':
                    return 'hold'
                if d >= 4:
                    return 'warm'
                if d <= -4:
                    return 'cool'
                return 'neutral'
            seen = {}
            for r, p in sorted(pool, key=lambda rp: -sum(rp[1]['v'])):
                b = bucket(r, p)
                if seen.get(b, 0) >= 3:
                    continue
                seen[b] = seen.get(b, 0) + 1
                add.append((r, b))
                if sum(seen.values()) >= target:
                    break
        else:
            # 优先挑"有该场景标签照片"的配方（照片和场景要对味），没标签的往后排
            def _tagged(r):
                return sum(1 for f in photos_of(r['slug']) if any(x in (PT.get(f) or []) for x in want))
            add = sorted(pool, key=lambda rp: -_tagged(rp[0]))[:target]
        keep = []
        for r, p in add:
            f = pick_photo(r['slug'], want, used)
            if not f:
                continue
            used.add(f)
            it = mkitem(r, f, sc)
            it['t'] = tag_short(sc, r)
            keep.append(it)
    sc['items'] = keep
    nC[lab] = len(keep)

for x in SCENES:
    for sc in SC:
        if sc['k'] == x['k']:
            x['label'] = sc['label']
# ⚠ SCENES 的结束位置要在这里**现算**：A/B 步改过长度，开头 grab() 给的 snj2 已经过期（踩过）
_si = s.index('window.__OM3SCENES__ = ')
_sj = _si + s[_si:].index('];') + 1
s = s[:_si] + 'window.__OM3SCENES__ = ' + json.dumps(SCENES, ensure_ascii=False, separators=(',', ':')) + s[_sj:]
# 刷新**所有**场景条目的说明（没重建的那些场景也要用上新提示行）
for sc in SC:
    for it in sc['items']:
        r = byslug.get(re.sub(r'^[rk]-', '', it.get('i') or ''))
        if not r:
            continue
        g = gen6(r)
        pre = (it.get('d') or '').split('｜')[0].strip()
        it['dd'] = (pre + '｜ ' + g['feel'] + g['key']) if '自动归类' in pre else (g['feel'] + g['key'])
        it['fd'] = html6(g, '参数解读（按参数推导）')
        it['fs'] = '参数解读 · %s' % (it.get('t') or '')
        it['pb'] = ''

# 写回数据段：切到 JSON 的 `]` 为止（后面的 `;` 留着 —— 别弄成 `];;`，第 50 轮踩过）
# ⚠ 用带 ` =` 的锚点：`window.__OM3SC__` 是 `window.__OM3SCENES__` 的前缀，index 会先命中后者（踩过）
i0 = s.index('window.__OM3SC__ = ')
j0 = i0 + s[i0:].index('];') + 1
s = s[:i0] + 'window.__OM3SC__ = ' + json.dumps(SC, ensure_ascii=False, separators=(',', ':')) + s[j0:]
print('  ✓ C：场景重建 -> %s' % '、'.join('%s %d' % (k, v) for k, v in nC.items()))
print('     总条目 %d' % sum(len(x['items']) for x in SC))

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))
