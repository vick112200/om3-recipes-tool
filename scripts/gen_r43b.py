# -*- coding: utf-8 -*-
"""第 43 轮 · 步骤 A+B+C（一次做完，幂等）

  A) 修 3 个 r42 留下的真 bug：卡片 id 重复 / 索引死锚点 / 目录死链
  B) 录入新配方「日常挂机」（小红书 momo（已黑化））
     卡片 + __OM3RECIPES__ + IDX + __OM3PHOTOS__ + __OM3PHOTOTAGS__ + 场景对比 + 图片文件
  C) 全站配方改名（中文名（English））+ 清掉配方合集侧残留的「C? 档 · 槽 n」

真源：
  scripts/recipe_names.py   —— 名字对照表
  scripts/recipe_wheel.py   —— 色轮 SVG 渲染器（自检 50/50 逐字节一致）

执行顺序（关键）：改名**先做**，再重新解析数据块、再插新配方 ——
否则新数据块里会带着旧名覆盖回去，或者新名里的旧名片段被二次替换。
"""
import io
import json
import os
import re
import shutil
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recipe_names import NAME_MAP, KEEP               # noqa: E402
import recipe_wheel as W                              # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
IMGDIR = os.path.join(ROOT, 'apk', 'assets', 'images')
NEWSRC = os.path.join(ROOT, '新', '🎞 分享一个奥巴EP7色轮参数（含样片）_2_momo（已黑化）_来自小红书网页版.jpg')
D = json.JSONDecoder()
LOG = []
NEDIT = [0]

KEYS = ['n', 'a', 'slug', 't', 'v', 'hi', 'sh', 'mid', 'con', 'shp', 'eff',
        'wb', 'wbt', 'wba', 'wbg', 'monoColor', 'monoStr', 'grain', 'hue']
NEW = {
    'n': '日常挂机', 'a': 'momo（已黑化）· 小红书', 'slug': 'momo_everyday', 't': 'COLOR',
    'v': [1, 2, 0, -1, -1, 0, 1, 1, 1, 0, -1, 0],
    'hi': -1, 'sh': 1, 'mid': 0, 'con': 0, 'shp': 0, 'eff': 0,
    'wb': 'Auto', 'wbt': None, 'wba': 0, 'wbg': 0,
    'monoColor': '', 'monoStr': None, 'grain': '', 'hue': '',
}
NEW_IMG = 'momo_everyday__s01.jpg'
NEW_TAGS = ['街拍', '城市', '日常']


# ---------------------------------------------------------------- 工具
def dumped(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


def blocks(s):
    """一次取出所有数据块（顺序敏感：解析 → 改名 → 重解析）"""
    out = {}
    for key, name in (('window.__OM3RECIPES__', 'REC'), ('var IDX', 'IDX'),
                      ('window.__OM3PHOTOS__', 'PH'), ('window.__OM3PHOTOTAGS__', 'PT'),
                      ('window.__OM3SC__', 'SC')):
        i = s.find(key)
        if i < 0:
            raise RuntimeError('找不到数据块：' + key)
        p = s.index('=', i) + 1
        while s[p].isspace():
            p += 1
        obj, e = D.raw_decode(s, p)
        out[name] = obj
        out[name + '_span'] = (p, e)
    return out


def find_div_end(s, start):
    depth, i = 0, start
    while True:
        m = re.compile(r'<div\b|</div>').search(s, i)
        if not m:
            raise RuntimeError('div 不闭合')
        if m.group(0) == '</div>':
            depth -= 1
            if depth == 0:
                return m.end()
        else:
            depth += 1
        i = m.end()


def wbsig(r):
    """卡片「白平衡签名」：与 r43a 给卡片徽标算的同一套（A=琥珀/B=蓝，G=绿/M=品红）。"""
    a, g = r.get('wba') or 0, r.get('wbg') or 0
    left = ('A+%d' % a) if a > 0 else (('B%d' % abs(a)) if a < 0 else 'A0')
    right = ('G+%d' % g) if g > 0 else (('M%d' % abs(g)) if g < 0 else 'G0')
    return '%s %s' % (left, right)


def rep1(s, old, new, label, must=True):
    if old not in s:
        if must:
            LOG.append('  ⚠ 没找到：%s' % label)
        return s
    NEDIT[0] += 1
    LOG.append('  ✅ %s' % label)
    return s.replace(old, new, 1)


# ---------------------------------------------------------------- 读入
s = io.open(P, encoding='utf-8').read()
B0 = blocks(s)
REC0 = B0['REC']
print('读入：REC %d · IDX %d · PHOTOS %d · PHOTOTAGS %d · SC %d 场景'
      % (len(REC0), len(B0['IDX']), len(B0['PH']), len(B0['PT']), len(B0['SC'])))

bak = os.path.join(ROOT, 'app', 'base.before_r43b.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r43b.html')

# ================================================================ A) 修 3 个 bug
print('\n=== A) 修 r42 留下的 3 个 bug ===')
dup = '<div class="card" id="r-ian-will_kinda-portra-v2">'
i1, i2 = s.find(dup), s.find(dup, s.find(dup) + 10 if s.find(dup) >= 0 else 0)
if i1 >= 0 and i2 > i1:
    before = [x for x in re.findall(r'<div class="card" id="r-([^"]+)">', s[:i1])][-1]
    assert before == 'andrew-gow_rose-gold', '重复卡定位不对，前一张是 %r' % before
    e = find_div_end(s, i1)
    seg = s[i1:e]
    assert 'Kinda Portra' in seg and seg.count('<div class="card"') == 1, '待删段不是单张卡'
    s = s[:i1] + s[e:]
    LOG.append('  ✅ 删掉 #mode-C4 里的重复卡（%d 字符）' % (e - i1))
    NEDIT[0] += 1
elif i2 <= i1:
    LOG.append('  · 重复卡已不存在，跳过')
s = rep1(s, '<a class="lv2" href="#plan">推荐方案总表</a>\n', '', '目录：删「推荐方案总表」(#plan)')
s = rep1(s, '<a href="#plan" data-goto="plan">推荐总表</a>', '', 'jumpbar：删「推荐总表」(#plan)')
s = rep1(s, '<a class="lv3" href="#r-ian-will_kinda-portra">3. Kinda Portra</a>\n', '',
         '目录：删重复卡的「3. Kinda Portra」')

# ================================================================ C1) 先改名
print('\n=== C-1) 全站改名（中文名（English））===')
pairs = []
for r in REC0:
    old = r['n']
    new = NAME_MAP.get(r['slug'])
    if new and new != old:
        pairs.append((old, new))
        if "'" in old:                      # HTML 里可能是 &#x27;
            pairs.append((old.replace("'", '&#x27;'), new.replace("'", '&#x27;')))
pairs = sorted(set(pairs), key=lambda x: -len(x[0]))
mp = dict(pairs)
pat = re.compile('(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])' % '|'.join(re.escape(a) for a, _ in pairs))
hit = {}


def _sub(m):
    hit[m.group(0)] = hit.get(m.group(0), 0) + 1
    return mp[m.group(0)]


s = pat.sub(_sub, s)
print('  改名 %d 条 / 共替换 %d 处' % (len([1 for a, _ in pairs if '&#' not in a]), sum(hit.values())))
for old, new in sorted(((a, b) for a, b in pairs if '&#' not in a), key=lambda x: -hit.get(x[0], 0)):
    print('    %-46s → %-48s %3d 处' % (old, new, hit.get(old, 0)))
LOG.append('  ✅ 改名 %d 条 / %d 处' % (len([1 for a, _ in pairs if '&#' not in a]), sum(hit.values())))
# 残留检查：先把「新名」整体挖掉再找旧名（否则旧名正好是新名括号里那截，会假报残留）
_tmp = s
for _a, _b in pairs:
    _tmp = _tmp.replace(_b, '\x00')
left = [(a, len(re.findall(r'(?<![A-Za-z0-9])%s(?![A-Za-z0-9])' % re.escape(a), _tmp)))
        for a, _ in pairs if '&#' not in a]
left = [x for x in left if x[1]]
LOG.append('  %s 旧名残留检查：%s' % ('✅' if not left else '⚠', left or '0 处'))

# ================================================================ 重新解析（数据块已带新名）
B = blocks(s)
REC, IDX, PH, PT, SC = B['REC'], B['IDX'], B['PH'], B['PT'], B['SC']
by_slug = dict((r['slug'], r) for r in REC)
assert len(REC) == len(REC0), 'REC 条数变了：%d → %d' % (len(REC0), len(REC))
# 数据里的名字必须全等于表里的新名
bad = [(r['slug'], r['n'], NAME_MAP.get(r['slug'])) for r in REC
       if r['slug'] in NAME_MAP and r['n'] != NAME_MAP[r['slug']]]
assert not bad, '数据名字没跟上：%s' % bad

# ================================================================ B) 录入新配方
print('\n=== B) 录入「日常挂机」===')
if 'r-momo_everyday' in s:
    LOG.append('  · 新配方已存在，跳过录入')
else:
    NEWREC = dict((k, NEW[k]) for k in KEYS)
    REC.append(NEWREC)
    by_slug[NEW['slug']] = NEWREC
    if not os.path.exists(os.path.join(IMGDIR, NEW_IMG)):
        shutil.copyfile(NEWSRC, os.path.join(IMGDIR, NEW_IMG))
        LOG.append('  ✅ 图片入 assets：%s（%.0f KB）' % (NEW_IMG, os.path.getsize(os.path.join(IMGDIR, NEW_IMG)) / 1024.0))
    else:
        LOG.append('  · 图片已存在，跳过')
    PH[NEW['slug']] = [NEW_IMG]
    PT[NEW_IMG] = list(NEW_TAGS)
    IDX.append({
        'h': 'r-' + NEW['slug'], 'n': NEW['n'], 'a': NEW['a'], 'sl': wbsig(NEWREC),
        't': '中性 · 冷暖中性 · 平顺',
        'g': '万能挂机：街拍、旅拍、海边、室内窗光、明暗混合的日常',
        'v': '想要强风格化、颜色要"响"的场合（这套是省心底子，不走偏不漂移）',
        'f': '干净自然的挂机底子，只在黄橙和蓝青上各推一点；天空水面更透，红绿基本不动',
    })
    CARD = (
        '<div class="card" id="r-%(slug)s"><div class="chd">'
        '<span class="cname">%(n)s</span><span class="slot">%(wb)s</span>'
        '<span class="cauth">%(a)s</span></div>'
        '<div class="tags"><span>中性</span><span>冷暖中性</span><span>平顺</span></div>'
        '<div class="cbody"><div class="cleft">%(svg)s'
        '<div class="vals">%(vals)s</div><div class="vlegend">1黄 → 12嫩黄绿 · 顺时针</div></div>'
        '<div class="cright"><div class="shots">'
        '<figure><img loading="lazy" data-im="%(img)s">'
        '<figcaption>作者样片 ①　·　小红书 momo（已黑化）</figcaption></figure></div>'
        '<details class="fold fnote"><summary>原文 · 作者自述 '
        '<span style="font-weight:400;opacity:.7">（点击展开）</span></summary>'
        '<div class="foldbody">从外网找到了一套非常省心的挂机色轮参数。核心理念：'
        '保持奥巴直出的干净自然，只加一点点胶片味，不走偏、不漂移。<br>'
        '色轮（从 0 点开始顺时针）：+1 +2 0 −1 −1 0 +1 +1 +1 0 −1 0；'
        '白平衡偏移 A0 / G0（保持原汁原味）。<br>'
        '对红色、绿色与蓝天做了轻微的 chrome effect，但调整幅度较轻，不会出现奇怪偏色。<br>'
        '这套参数最大的优点就是：几乎不用想 —— 亮光、阴影、街拍、海边、室内都能 hold 住，'
        '随手一拍就是舒服的质感。</div></details>'
        '<details class="fold fmine"><summary>补充 · 画面感觉：干净自然的挂机底子，'
        '只在黄橙和蓝青上各推一点… <span style="font-weight:400;opacity:.7">（展开看全 6 项）</span></summary>'
        '<div class="foldbody">'
        '<div class="row"><span class="mk">画面感觉</span><span class="mv">干净自然的挂机底子，'
        '只在黄橙和蓝青上各推一点，红色、绿色基本不动，整体不偏色也不漂移。</span></div>'
        '<div class="row"><span class="mk">色彩重点</span><span class="mv">往上推的是 橙 +2、黄 +1、'
        '蓝 +1、浅蓝 +1、青 +1；往下收的是 品红 −1、紫 −1、黄绿 −1。天空和水面更透，'
        '肤色暖而不红（红轴没动）。</span></div>'
        '<div class="row"><span class="mk">影调</span><span class="mv">暗部略提（Sh +1）；高光略压（Hi −1）。'
        '反差平顺，亮光到阴影都能接住。</span></div>'
        '<div class="row"><span class="mk">适合</span><span class="mv good">万能挂机：街拍、旅拍、海边、'
        '室内窗光、明暗混合的日常</span></div>'
        '<div class="row"><span class="mk">避开</span><span class="mv avoid">想要强风格化、'
        '颜色要"响"的场合（这套就是"不偏不漂"的省心底子）</span></div>'
        '<div class="row"><span class="mk">提示</span><span class="mv tip">作者只给了色轮和白平衡；'
        '本卡的 <b>Sh +1 / Hi −1</b> 是按"挂机场景"补的（高光压 1 挡保天空、暗部提 1 挡保室内），'
        '中间调 / 对比 / 锐度 / 阴影补偿 / 曝光都保持中性 0。白平衡记得设 AUTO 并关闭「保持暖色调」。'
        '</span></div></div></details>'
        '<div class="params">色调曲线 <i>Sh 1 / Mid 0 / Hi -1</i>'
        '<span class="psep">　｜　</span>阴影补偿 <i>0</i> · 锐度 <i>0</i> · 对比 <i>0</i> · 曝光 <i>0</i></div>'
        '<div class="exif">样片来源：小红书 <b>momo（已黑化）</b>《分享一个奥巴EP7色轮参数（含样片）》；'
        '非本站标准场景，是作者实拍。色轮数值已按相机屏幕逐点核对。</div>'
        '</div></div></div>'
    ) % {'slug': NEW['slug'], 'n': NEW['n'], 'a': NEW['a'], 'wb': wbsig(NEWREC),
         'svg': W.wheel_svg(NEW['v']), 'vals': W.vals_line(NEW['v'])[18:-6], 'img': NEW_IMG}
    i = s.find('<details class="sec" id="mode-C1"')
    j = s.find('<details class="sec" id="mode-C2"')
    assert 0 < i < j, '找不到 #mode-C1'
    end = s.rfind('</div></details>', i, j)
    assert end > i, '#mode-C1 结尾定位失败'
    s = s[:end] + CARD + s[end:]
    LOG.append('  ✅ 新卡片插进 #mode-C1 末尾（%d 字符）' % len(CARD))
    SC[0]['items'].append({
        'i': 'r-' + NEW['slug'], 'n': NEW['n'], 'a': NEW['a'], 'sl': wbsig(NEWREC),
        't': '中性 · 冷暖中性 · 平顺', 'f': NEW_IMG,
        'd': '图按画面自动归类：街景 / 城市（自动判断，偶尔会看错）｜ '
             '干净自然的挂机底子，天空蓝得透、砖地暖而不艳，不偏色也不漂移',
        'os': '', 'osl': '',
    })
    LOG.append('  ✅ 场景对比「%s」+1 条（现 %d 条）' % (SC[0]['label'], len(SC[0]['items'])))

# ================================================================ C2) 清残留
print('\n=== C-2) 清掉配方合集侧残留的档位字样 ===')
n_idx = 0
for x in IDX:
    h = x.get('h') or ''
    if h == 'r-ian-will_kinda-portra':            # A2：索引死锚点
        x['h'] = 'r-ian-will_kinda-portra-v2'
        h = x['h']
        LOG.append('  ✅ 修索引死锚点 r-ian-will_kinda-portra → …-v2')
    if h.startswith('r-'):
        r = by_slug.get(h[2:])
        if r:
            if x.get('sl') != wbsig(r):
                n_idx += 1
            x['sl'] = wbsig(r)
LOG.append('  ✅ IDX 里 %d 条 paneA 条目的 sl → 白平衡签名' % n_idx)
n_sc = 0
for sc in SC:
    for it in sc['items']:
        h = it.get('i') or ''
        r = by_slug.get(h[2:]) if h.startswith('r-') else None
        if r:
            if it.get('sl') != wbsig(r):
                n_sc += 1
            it['sl'] = wbsig(r)
LOG.append('  ✅ SC 里 %d 条 sl → 白平衡签名' % n_sc)
for n in '12345':
    s = rep1(s, '<a class="lv2" href="#mode-C%s">C%s 档 · ' % (n, n),
             '<a class="lv2" href="#mode-C%s">' % n, '目录 C%s 去「C%s 档 ·」' % (n, n), must=False)
s = rep1(s, '（C1 档位）', '（不偏移档）', '保持暖色调表：C1 档位 → 不偏移档')
s = rep1(s, '按白平衡偏移分档', '按白平衡签名找', '页首副标题：按白平衡偏移分档 → 按白平衡签名找')

# 顶栏跳转条：「C1..C5」改成新分区标题（id 不动，只改可见文字）
for n, lbl in (('1', '不偏移'), ('2', 'A2 G1'), ('3', 'A1 G1'), ('4', 'A4 M1'), ('5', 'A3 G1')):
    s = rep1(s, '<a href="#mode-C%s" data-goto="mode-C%s">C%s</a>' % (n, n, n),
             '<a href="#mode-C%s" data-goto="mode-C%s">%s</a>' % (n, n, lbl), '跳转条 C%s → %s' % (n, lbl))
# 「备选池」→「更多配方」
s = rep1(s, '<div class="tgh">备选池（按白平衡偏移）</div>', '<div class="tgh">更多配方（按白平衡偏移）</div>',
         '目录分组标题：备选池 → 更多配方')
s = rep1(s, '<a href="#pool" data-goto="pool">备选池</a>', '<a href="#pool" data-goto="pool">更多配方</a>',
         '跳转条：备选池 → 更多配方')
# 「偏移 A0 G0 可换进 C1 · 14 个」/「可替换进 C1 · 14 个」→ 去掉档位指代
s, k = re.subn(r'(偏移 [A-Z0-9 ]+?) ?(?:可换进|可替换进) C\d · ', r'\1 · ', s)
LOG.append('  ✅ 去掉「可换进/可替换进 C?」（%d 处）' % k)
s, k = re.subn(r'(偏移 [A-Z0-9 ]+?) &nbsp;<span style="color:#7ed3bd;font-size:12px">(?:可替换进 C\d )?· ',
               r'\1 &nbsp;<span style="color:#7ed3bd;font-size:12px">· ', s)
LOG.append('  ✅ 池分组标题去掉档位指代（%d 处）' % k)

# ================================================================ 写回数据块
print('\n=== 写回数据块 ===')
N = blocks(s)
# 从后往前替换：先替后面的，前面块的偏移才不会被搅动
todo = []
for name, key in (('REC', 'window.__OM3RECIPES__'), ('IDX', 'var IDX'),
                  ('PH', 'window.__OM3PHOTOS__'), ('PT', 'window.__OM3PHOTOTAGS__'),
                  ('SC', 'window.__OM3SC__')):
    obj = {'REC': REC, 'IDX': IDX, 'PH': PH, 'PT': PT, 'SC': SC}[name]
    p, e = N[name + '_span']
    todo.append((p, e, key, obj))
for p, e, key, obj in sorted(todo, key=lambda x: -x[0]):
    s = s[:p] + dumped(obj) + s[e:]
    LOG.append('  ✅ %s 写回（%d 条）' % (key, len(obj)))

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n'.join(LOG))
print('\n写出 app/base.html：%.2f MB（%d 处编辑）' % (len(s.encode('utf-8')) / 1048576.0, NEDIT[0]))

# ================================================================ 自检
print('\n=== 自检 ===')
S = io.open(P, encoding='utf-8').read()
R2 = blocks(S)
cards = re.findall(r'<div class="card" id="r-([^"]+)">', S)
dup2 = [k for k, v in Counter(cards).items() if v > 1]
print('配方卡 %d 张（唯一 %d）· 重复 id：%s' % (len(cards), len(set(cards)), dup2 or '无'))
print('数据 %d 条 · 索引 %d 条 · 图库 %d 条 · 场景 %d' % (len(R2['REC']), len(R2['IDX']), len(R2['PH']), len(R2['SC'])))
ids = set(re.findall(r'\bid="([^"]+)"', S))
print('索引死锚点：', [x['h'] for x in R2['IDX'] if x['h'].startswith('r-') and x['h'] not in ids] or '无')
print('场景死锚点：', [it['i'] for x in R2['SC'] for it in x['items'] if it['i'] not in ids] or '无')
deadlink = sorted(l for l in set(re.findall(r'href="#([^"]+)"', S))
                  if l not in ids and "'" not in l)
print('目录死链：', deadlink or '无')
for kw in ('C1 档', 'C2 档', 'C3 档', 'C4 档', 'C5 档'):
    print('  paneA 残留「%s」：%d' % (kw, S.count(kw)))
print('  残留「C? · 槽」：%d' % len(re.findall(r'C\d · 槽', S)))
R = dict((r['slug'], r) for r in R2['REC'])
miss, seen = [], set()
for cid in cards:
    if cid in seen:
        continue
    seen.add(cid)
    if cid not in R:
        miss.append(cid)
        continue
    i0 = S.find('id="r-%s"' % cid)
    m = re.search(r'<span class="cname">([^<]*)</span>', S[i0:i0 + 400])
    if not m or m.group(1) != R[cid]['n']:
        miss.append('%s 卡片=%r 数据=%r' % (cid, m and m.group(1), R[cid]['n']))
print('卡片标题 ≠ 数据名字：', miss or '无')
