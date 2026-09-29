# -*- coding: utf-8 -*-
"""第 54 轮生成器（幂等）· v3.8 —— 门面图改「作者优先」

用户 2026-09-27 的观察 + 拍板：「原站主图往往是作者亲自拍的，比较能展现适合场景和风格；
我们 app 用的图不太合适」→「全做」「图片 1200px，接受 app ≤100MB」。

实测到的原站规则（抓 /recipes/<slug> 现页面，8/8 命中，见 SPEC-round54 §0）：
  · 有 `sampleImages[].isPrimary=true` → 那张就是主图（og:image）
  · 没有 isPrimary → **样片列表第一张**
  · 一张作者样片都没有 → 原站连 og:image 都没有（正文就是统一对比场景）

本轮做四件事：
  A. `__OM3PHOTOS__` 顺序改成「主图 → 其余作者样片 → 对比场景」（原来按文件名字典序，
     `__cmp__…` 排在 `__s…` 前面 → 场景挑图 87% 选中对比图）
  B. 卡片 `.shots`：主图排第一 + 图注「作者主图」+ `class="hero"`；对比场景挪到后面
  C. 优化版槽位 `.osshots`：同规则（主图 + 作者样片最多 2 + 对比场景最多 2，≤5 张）
  D. `__OM3SC__[].f` 263 条按「标签优先、作者优先、对比图兜底」重挑
  E. 删掉从未被调用的死函数 `pickPhoto()`

**不改**：`window.SC`（实拍对比的 6 个统一场景 —— 同构图横比就该用对比图）、
配方数、场景成员、参数解读/提示文案、相机链路、任何用户数据。

幂等：重复跑结果相同（重排到规范顺序 + 图注规范化；`__OM3PHOTOS__` 由 gen_phototags 整块重建）。
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
BAK = os.path.join(ROOT, 'app', 'base.before_r54.html')
IMG = os.path.join(ROOT, 'apk', 'assets', 'images')
SRC = os.path.join(ROOT, 'all_recipes.json')

# 场景 → 期望画面标签（与页面里的 SEL_TAGS 一致；用来给「按场景找配方」挑图）
SEL_TAGS = {
    'portrait': ['人像'], 'wedding': ['人像'], 'kids': ['人像'], 'mono': ['人像'],
    'flower': ['花卉'], 'sunset': ['花卉'], 'forest': ['绿意'], 'autumn': ['绿意'],
    'night': ['夜景'], 'skywater': ['天空水面'], 'snow': ['高调'], 'mist': ['雾'],
    'arch': ['中性白'], 'still': ['中性白'], 'street': ['人群'], 'travel': ['人群'],
    'backlight': ['人群'], 'rain': ['日常'], 'food': ['日常'], 'indoor': ['夜景'], 'film': ['日常'],
}
CIRCLED = '①②③④⑤⑥⑦⑧⑨'

s = io.open(P, encoding='utf-8').read()
if not os.path.exists(BAK):
    io.open(BAK, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r54.html')

by_slug = {r['slug']: r for r in json.load(io.open(SRC, encoding='utf-8'))['results']}


def grab(var, start=0):
    """抠出 window.<var> = ... 的 JSON（gen_r53 同款）"""
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


def find_div(text, start):
    depth, i = 0, start
    while True:
        m = re.compile(r'<div\b|</div>').search(text, i)
        if not m:
            return None
        if m.group(0) == '</div>':
            depth -= 1
            if depth == 0:
                return m.end()
        else:
            depth += 1
        i = m.end()


FIG_RE = re.compile(r'<figure[^>]*>.*?</figure>', re.S)


def slug_of_fig(fig):
    m = re.search(r'data-im="([^"]+?)__', fig)
    return m.group(1) if m else ''


def fname_of_fig(fig):
    m = re.search(r'data-im="([^"]+)"', fig)
    return m.group(1) if m else ''


# ---------- 主图表：slug → 主图文件名 ----------
def hero_map():
    have = set(os.listdir(IMG))
    hm = {}
    for slug, r in by_slug.items():
        ss = r.get('sampleImages') or []
        pick = ''
        for i, x in enumerate(ss):                       # ① 原站 isPrimary
            if x.get('isPrimary'):
                pick = '%s__s%02d.jpg' % (slug, i + 1)
                break
        if not pick and ss:                              # ② 没有就取列表第一张（原站 og:image 就是这么来的）
            pick = '%s__s%02d.jpg' % (slug, 1)
        if pick and pick in have:
            hm[slug] = pick
    return hm


HERO = hero_map()


def normalize(fig):
    """把 figure 还原成「未标注」状态，便于幂等重排"""
    fig = fig.replace('<figure class="hero">', '<figure>')
    return fig.replace('作者主图', '作者样片')


def mark_hero(fig):
    fig = fig.replace('<figure>', '<figure class="hero">', 1)
    return fig.replace('作者样片', '作者主图', 1)


def reorder(figs, cap=None):
    """规范顺序：[主图] + [其余作者样片] + [对比场景]；cap=(最多作者, 最多对比) 时截断"""
    figs = [normalize(f) for f in figs]
    slug = slug_of_fig(figs[0]) if figs else ''
    hero = HERO.get(slug, '')
    authors = [f for f in figs if '__cmp__' not in fname_of_fig(f)]
    cmps = [f for f in figs if '__cmp__' in fname_of_fig(f)]
    h = [f for f in authors if fname_of_fig(f) == hero]
    rest = [f for f in authors if fname_of_fig(f) != hero]
    if cap:
        rest = rest[:cap[0]]
        cmps = cmps[:cap[1]]
    out = h + rest + cmps
    if h and out:
        out[0] = mark_hero(out[0])
    assert hero or not h
    return out


# ================= A. 图片清单顺序（交给 gen_phototags.py，它整块重建） =================
import gen_phototags  # noqa: E402

gen_phototags.HERO = HERO          # 让 tags/photos 生成器用同一张主图表
gen_phototags.main()
s = io.open(P, encoding='utf-8').read()
print('A. __OM3PHOTOS__ 已按「主图 → 作者样片 → 对比场景」重建（主图 %d 条）' % len(HERO))

# ================= B. 卡片 .shots =================
cards = [(m.group(1), m.start()) for m in re.finditer(r'<div class="card" id="r-([^"]+)">', s)]
reps = []
nhero = 0
for i, (cid, pos) in enumerate(cards):
    end = cards[i + 1][1] if i + 1 < len(cards) else s.find('<footer', pos)
    block = s[pos:end]
    a = block.find('<div class="shots">')
    if a < 0:
        continue
    b = find_div(block, a)
    inner = block[a + len('<div class="shots">'):b - len('</div>')]
    figs = FIG_RE.findall(inner)
    if not figs:
        continue
    new = reorder(figs)
    if new[0] != figs[0]:
        nhero += 1
    reps.append((pos + a + len('<div class="shots">'), pos + b - len('</div>'), ''.join(new)))
for a, b, txt in reversed(reps):
    s = s[:a] + txt + s[b:]
print('B. 卡片 .shots 重排：%d 张（首图变了 %d 张）' % (len(reps), nhero))

# ================= C. 优化版槽位 .osshots =================
slots = [(m.group(1), m.start()) for m in re.finditer(r'<div class="oslot" id="(oC[^"]+)">', s)]
reps = []
for i, (sid, pos) in enumerate(slots):
    nxt = slots[i + 1][1] if i + 1 < len(slots) else s.find('<div class="omode"', pos)
    block = s[pos:nxt]
    a = block.find('<div class="osshots">')
    if a < 0:
        continue
    b = find_div(block, a)
    inner = block[a + len('<div class="osshots">'):b - len('</div>')]
    figs = FIG_RE.findall(inner)
    if not figs:
        continue
    new = reorder(figs, cap=(2, 2))
    reps.append((pos + a + len('<div class="osshots">'), pos + b - len('</div>'), ''.join(new)))
for a, b, txt in reversed(reps):
    s = s[:a] + txt + s[b:]
print('C. 槽位 .osshots 重排：%d 个' % len(reps))

# ================= D. __OM3SC__[].f 重挑 =================
SC, sc_i, sc_j = grab('__OM3SC__')
PH, _, _ = grab('__OM3PHOTOS__')
PT, _, _ = grab('__OM3PHOTOTAGS__')


PREFIX_RE = re.compile(r'^图按画面自动归类：[^（]*（自动判断，偶尔会看错）')
# 这两个标签**只有那两张统一对比图会有**（自动归类根本不产出它们，是 SCENE_TAG 硬给的）：
#   人群 = `__cmp__marathon.jpg`，中性白 = `__cmp__peace-memorial.jpg`。
# 所以对「城市街拍 / 旅行日常 / 逆光大光比 / 建筑几何 / 静物极简」这 5 个场景，
# 「要求这个标签」等于「只能显示站点测试图」—— 那不是对**画面内容**的要求，
# 而是标签系统的产物。本轮把这两个从筛选条件里去掉 → 这 5 个场景改成作者优先。
# 其余标签（雾 / 夜景 / 人像 / 绿意 / 花卉 / 天空水面 / 高调 / 日常）是分类器真能看出来的
# 内容，保留「对题优先」：雾/阴天/雨天仍用雾照、暖光/灯光下仍用夜景照（第 52 轮的要求）。
CMP_ONLY_TAGS = {'人群', '中性白'}


def new_prefix(f):
    return '图按画面自动归类：%s（自动判断，偶尔会看错）' % ' / '.join(PT.get(f) or [])


def pick(slug, want, used):
    """对题优先 + 作者优先（见上面对 CMP_ONLY_TAGS 的说明）。同一场景内不重复用同一张图。

    打分：**画面标签对题 +2**；作者图 +1（`__OM3PHOTOS__` 已是「主图 → 其余作者样片 →
    对比场景」，同分组内主图/靠前的优先）。
      · 对题的作者图 3 > 对题的对比图 2 > 不对题的作者图 1 > 不对题的对比图 0

    ⚠ 为什么"对题"必须压在"作者"上面（第一版我写反了，被 dv_r52 当场抓出来）：
    夜景霓虹 / 雪景 / 森林绿意 / 雾与阴天 / 暖光灯光下 这几个场景的 want 标签
    （夜景 / 高调 / 绿意 / 雾）是**对画面内容的要求**。改成"作者绝对优先"后实测：
    夜景霓虹里挂上「人像」「绿意」照、雪景里挂上「夜景」照、雾与阴天里 6/8 张不是雾照 ——
    第 52 轮特意配好的"这些场景用夜景池 / 雾池照片"等于白做。
    所以：**对题是前提**，对题集合内部作者图永远排在对比图前面。
    """
    want = [t for t in want if t not in CMP_ONLY_TAGS]
    cands = list(PH.get(slug) or [])
    best, bs = '', -1
    for f in cands:
        if f in used:
            continue
        sc = (2 if any(t in (PT.get(f) or []) for t in want) else 0)
        sc += (0 if '__cmp__' in f else 1)
        if sc > bs:
            best, bs = f, sc
    if best and bs > 0:
        return best
    # 一张对题的都没有（want 为空，或该配方确实没有对题的图）→ 作者优先、对比图兜底
    for f in cands:
        if f not in used and '__cmp__' not in f:
            return f
    left = [f for f in cands if f not in used]                # 全被本场景用过了 → 允许重复
    return left[0] if left else (cands[0] if cands else '')



stat = [0, 0]          # [作者图条数, 总条数]
missing = []
npre = 0
for sc in SC:
    want = SEL_TAGS.get(sc['k'], [])
    used = set()
    for it in sc['items']:
        slug = re.sub(r'^[rk]-', '', it.get('i') or '')
        f = pick(slug, want, used)
        if not f:
            missing.append((sc['k'], it.get('n')))
            continue
        it['f'] = f
        used.add(f)
        stat[1] += 1
        if '__cmp__' not in f:
            stat[0] += 1
        # ⚠ 描述里那行「图按画面自动归类：<标签>」是**跟着旧图写死的**。
        #    换了图就得重算，否则文字和图不一致（第 50 轮"写着避开阴天却出现在阴天场景"就是这类不一致）。
        pre = new_prefix(f)
        for kk in ('d', 'dd'):
            v = it.get(kk) or ''
            if PREFIX_RE.match(v):
                nv = PREFIX_RE.sub(pre, v, count=1)
                if nv != v:
                    it[kk] = nv
                    npre += 1
_si = s.index('window.__OM3SC__ = ')
_sj = _si + s[_si:].index('];') + 1
s = s[:_si] + 'window.__OM3SC__ = ' + json.dumps(SC, ensure_ascii=False, separators=(',', ':')) + s[_sj:]
print('D. 场景挑图重挑：作者图 %d / %d 条（改前 34/263）；「图按画面自动归类」描述跟着重算 %d 处；挑不到图的条目 %d'
      % (stat[0], stat[1], npre, len(missing)))
if missing:
    print('   ⚠ 挑不到：%s' % missing[:6])

# ================= E. 删死代码 pickPhoto + 主图样式 =================
def cut_js_function(text, name):
    """按**花括号配对**删掉一个函数（不能用正则非贪婪 —— 踩过：`.*?\\n *\\}\\n`
    会停在 for 循环那个 `}` 上，留下 `return {...};` 和孤立的 `}` → 整块 JS 语法错误）。"""
    m = re.search(r'\n[ \t]*function ' + re.escape(name) + r'\s*\(', text)
    if not m:
        return text, False
    k = text.index('{', m.end())
    depth, j, q = 0, k, ''
    while j < len(text):
        c = text[j]
        if q:
            if c == '\\':
                j += 2
                continue
            if c == q:
                q = ''
        elif c in '"\'`':
            q = c
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                e = j + 1
                while e < len(text) and text[e] in ' \t':
                    e += 1
                if e < len(text) and text[e] == '\n':
                    e += 1
                return text[:m.start()] + '\n' + text[e:], True
        j += 1
    return text, False


s, cut = cut_js_function(s, 'pickPhoto')
if cut:
    print('E1. 已删除死函数 pickPhoto()（从未被调用；SPEC-round54 §0.1 认账那条）')
else:
    print('E1. pickPhoto 已经不在（跳过）')
assert 'pickPhoto' not in s, '删完还有 pickPhoto 残留'

# ================= E0. 页面里的 SEL_TAGS 与第 52 轮的口径对齐 =================
# 第 39 轮的表把「暖光 / 灯光下」写成 indoor: ['日常']，而第 52 轮重建这个场景时用的是
# 「夜景 / 混光」那批照片（`gen_r52.py` 里 want = ['夜景']）。两处口径不一致 → 本轮统一成
# ['夜景']（否则本生成器按页面表挑图，会把第 52 轮特意配的夜景照又挑掉 —— dv_r52 抓到的就是这个）。
OLD_SEL = "rain: ['日常'], food: ['日常'], indoor: ['日常'], film: ['日常']"
NEW_SEL = "rain: ['日常'], food: ['日常'], indoor: ['夜景'], film: ['日常']"
if OLD_SEL in s:
    s = s.replace(OLD_SEL, NEW_SEL)
    print('E0. SEL_TAGS 的 indoor 口径已与第 52 轮对齐（日常 → 夜景）')
else:
    assert NEW_SEL in s, 'SEL_TAGS 那行既不是旧写法也不是新写法'
    print('E0. SEL_TAGS 口径已对齐（跳过）')

CSS = ('/* 第 54 轮：作者主图（原站 isPrimary / 样片第一张）在列表里排第一并描一圈，' 
       '和「对比场景」区分开 */\n'
       '.shots figure.hero img,.osshots figure.hero img{border-color:#c9a227;'
       'box-shadow:0 0 0 1px rgba(201,162,39,.55)}\n')
if '第 54 轮：作者主图' not in s:
    anchor = s.index('.shots figcaption{')
    s = s[:anchor] + CSS + s[anchor:]
    print('E2. 已加 .hero 描边样式')
else:
    print('E2. .hero 样式已在（跳过）')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n已写入 app/base.html（%.2f MB）' % (len(s.encode('utf-8')) / 1048576.0))
