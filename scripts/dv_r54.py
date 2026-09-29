# -*- coding: utf-8 -*-
"""第 54 轮验收：门面图改「作者优先」（原站 isPrimary → 首张 → 对比图兜底）+ 图片升 1200px

跑法：python scripts/dv_r54.py
断的东西（对 SPEC-round54 §8 的 10 条）：静态 8 组 + 运行时 2 组。
--runtime 时才起无头 Chrome（默认只跑静态，快）。
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r54.html')
IMG = os.path.join(ROOT, 'apk', 'assets', 'images')
SRC = os.path.join(ROOT, 'all_recipes.json')

src = io.open(P, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
by_slug = {r['slug']: r for r in json.load(io.open(SRC, encoding='utf-8'))['results']}
have = set(os.listdir(IMG))
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


def grab(s, var):
    i = s.index('window.%s' % var)
    j = s.index('=', i) + 1
    while s[j] in ' \n':
        j += 1
    oc, cc = s[j], {'[': ']', '{': '}'}[s[j]]
    d, k = 0, j
    while k < len(s):
        if s[k] == '"':
            k += 1
            while s[k] != '"' or s[k - 1] == chr(92):
                k += 1
        elif s[k] == oc:
            d += 1
        elif s[k] == cc:
            d -= 1
            if d == 0:
                return json.loads(s[j:k + 1])
        k += 1
    raise SystemExit('no ' + var)


def cards(s):
    pos = [m.start() for m in re.finditer(r'<div class="card" id="r-', s)] + [len(s)]
    ids = re.findall(r'<div class="card" id="(r-[^"]+)"', s)
    out = {}
    for i, cid in enumerate(ids):
        blk = s[pos[i]:pos[i + 1]]
        a = blk.find('<div class="shots">')
        b = blk.find('</div>', a)
        out[cid] = re.findall(r'<figure[^>]*>.*?</figure>', blk[a:b], re.S)
    return out


def fname(fig):
    m = re.search(r'data-im="([^"]+)"', fig)
    return m.group(1) if m else ''


PH = grab(src, '__OM3PHOTOS__')
PT = grab(src, '__OM3PHOTOTAGS__')
SC = grab(src, '__OM3SC__')
SCN = grab(src, '__OM3SCENES__')
C = cards(src)
CO = cards(old)

# 第 55 轮往 app 里补了 19 条新配方（卡片 58 → 77、图片 431 → 534、场景条目也多了）。
# 本脚本只断**第 54 轮承诺的那批**：基线取 base.before_r55.html；新补的由 dv_r55.py 负责。
_P55 = os.path.join(ROOT, 'app', 'base.before_r55.html')
OLD55 = io.open(_P55, encoding='utf-8').read() if os.path.exists(_P55) else src
BASE_CARDS = set(re.findall(r'<div class="card" id="(r-[^"]+)"', OLD55))
BASE_SLUGS = set(x[2:] for x in BASE_CARDS)

# ---------- ① 主图表能不能算出来（原站 isPrimary → 首张） ----------
print('=== ① 主图表（原站 isPrimary → 无则取样片第一张）===')
HERO, nprim = {}, 0
for slug, r in by_slug.items():
    ss = r.get('sampleImages') or []
    pick = ''
    for i, x in enumerate(ss):
        if x.get('isPrimary'):
            pick, _ = '%s__s%02d.jpg' % (slug, i + 1), 0
            nprim += 1
            break
    if not pick and ss:
        pick = '%s__s%02d.jpg' % (slug, 1)
    if pick and pick in have:
        HERO[slug] = pick
A(nprim == 33, '源数据（源站 78 条）里 33 条有 isPrimary（实得 %d）' % nprim)
card_slugs = set(re.findall(r'<div class="card" id="r-([^"]+)">', src))
nprim_card = sum(1 for slug in card_slugs if any(x.get('isPrimary') for x in (by_slug.get(slug, {}).get('sampleImages') or [])))
nprim_base = sum(1 for slug in BASE_SLUGS
                 if any(x.get('isPrimary') for x in (by_slug.get(slug, {}).get('sampleImages') or [])))
A(nprim_base == 27, 'r54 那 58 张卡里 27 张带 isPrimary（实得 %d；现在全站是 %d）' % (nprim_base, nprim_card))
A(len([k for k in HERO if k in BASE_SLUGS]) == 37,
  'r54 那批能定出主图的配方 37 条（实得 %d；现在全站 %d）'
  % (len([k for k in HERO if k in BASE_SLUGS]), len(HERO)))
A('andrew-gow_rose-gold' in HERO and HERO['andrew-gow_rose-gold'].endswith('__s02.jpg'),
  '抽样：andrew-gow 主图 = s02（原站第 2 张 isPrimary）')
A('ian-will_ode-to-ansel' in HERO and HERO['ian-will_ode-to-ansel'].endswith('__s09.jpg'),
  '抽样：ian-will_ode-to-ansel 主图 = s09（原站第 9 张；验证 sNN 编号 = 原站顺序）')
A('ibd-fuji-velvia' in HERO and HERO['ibd-fuji-velvia'].endswith('__s01.jpg'),
  '抽样：没有 isPrimary 的 ibd-fuji-velvia 主图 = 首张 s01（原站 og:image 就是这么来的）')

# ---------- ② __OM3PHOTOS__ 顺序 ----------
print('=== ② __OM3PHOTOS__ = 主图 → 作者样片 → 对比场景 ===')
po = grab(old, '__OM3PHOTOS__')
A(all(k in PH and sorted(PH[k]) == sorted(po[k]) for k in po),
  'r54 那 %d 个配方的图清单没变（顺序仍是主图优先；现在全站 %d 个）' % (len(po), len(PH)))
A(all(sorted(po[k]) == sorted(PH[k]) for k in po), '每个配方的图集合都没变（只是顺序变了）')
A(all(('__cmp__' not in v[0]) for k, v in PH.items() if any('__cmp__' not in f for f in v)),
  '有作者样片的配方：数组第 1 个不是对比图')
A(all(v[0] == HERO[k] for k, v in PH.items() if k in HERO), '有主图的配方：数组第 1 个就是主图')
cmp_tail = all(all('__cmp__' not in f for f in v[:len(v) - sum(1 for x in v if '__cmp__' in x)])
               for v in PH.values())
A(cmp_tail, '对比图一律排在作者样片之后')
A(all(PH.get(k, [None])[0] == po[k][0] for k in po if not any('__cmp__' not in f for f in po[k])),
  '没有作者样片的配方：数组与改前一致')

# ---------- ③/④ 卡片 ----------
print('=== ③ 卡片首图 = 主图；④ 图集合守恒（只换顺序不换图）===')
bad_first, bad_set, nhero_cap = [], [], 0
for cid, figs in [(k, v) for k, v in C.items() if k in BASE_CARDS]:
    slug = cid[2:]
    names = [fname(f) for f in figs]
    if slug in HERO:
        if names[0] != HERO[slug]:
            bad_first.append(cid)
        if '作者主图' not in figs[0]:
            bad_first.append(cid + '(无标注)')
        else:
            nhero_cap += 1
    else:
        # 没有主图：顺序必须与改前一致
        if [fname(f) for f in CO.get(cid, [])] != names:
            bad_first.append(cid + '(无主图却动了)')
    if sorted(names) != sorted(fname(f) for f in CO.get(cid, [])):
        bad_set.append(cid)
    if names and '__cmp__' in names[0] and slug in HERO:
        bad_first.append(cid + '(对比图仍在首位)')
A(not bad_first, '有主图的卡首图 == 主图且图注标「作者主图」（异常 %d 个：%s）' % (len(bad_first), bad_first[:4]))
A(nhero_cap == 37, 'r54 那批带「作者主图」标注的卡 = 37（实得 %d）' % nhero_cap)
A(not bad_set, 'r54 那 58 张卡的图集合逐项守恒（异常 %d）' % len(bad_set))
n_auth_first = sum(1 for k, v in C.items() if k in BASE_CARDS and v and '__cmp__' not in fname(v[0]))
A(n_auth_first == 38, 'r54 那批首图是作者实拍的卡 = 38（37 张主图 + momo；实得 %d）' % n_auth_first)

# ---------- ⑤ 槽位 .osshots ----------
print('=== ⑤ 优化版槽位 .osshots ===')
oss = re.findall(r'<div class="osshots">(.*?)</div>', src, re.S)
A(len(oss) > 0, '槽位样片块 %d 个' % len(oss))
bad = []
for seg in oss:
    figs = re.findall(r'<figure[^>]*>.*?</figure>', seg, re.S)
    nm = [fname(f) for f in figs]
    if len(figs) > 5:
        bad.append('>5 张')
    if len(set(nm)) != len(nm):
        bad.append('有重复')
    slug = nm[0].split('__')[0] if nm else ''
    # 与卡片第一张一致
    cid = 'r-' + slug
    if cid in C and nm and fname(C[cid][0]) != nm[0] and slug in HERO:
        bad.append('%s 首图与卡片不一致' % slug)
A(not bad, '每个槽位：≤5 张 / 无重复 / 有主图时首图 == 卡片首图（异常：%s）' % bad[:4])

# ---------- ⑥ SC 挑图 ----------
print('=== ⑥ 场景挑图（作者优先）===')
_it54 = [it for sc in SC for it in sc['items'] if re.sub(r'^[rk]-', '', it['i']) in BASE_SLUGS]
n_auth = sum(1 for it in _it54 if '__cmp__' not in it['f'])
# 第 56 轮改了挑图口径：**没命中场景期望标签时改用站点统一对比图**（用户明确同意）
# → 用作者实拍的条数从 143 降到 60 上下（改前 r54 是 34）。这里守一条下限，避免又退回"一律对比图"。
A(n_auth >= 55, 'r54 那批 %d 条里用作者实拍的 = %d（r54 改前 34；第 56 轮起"没对题就换统一对比图"）'
  % (len(_it54), n_auth))
# 条件类场景必须仍"对题"（第 52 轮的要求不能被我改回去 —— 这条是被 dv_r52 抓出来后才加的）
# 第 57 轮：雾场景没有可靠画面判据 → 不再纳入「必须对题」的清单（其余 4 个照旧）
cond = {'night': '夜景', 'snow': '高调', 'forest': '绿意', 'indoor': '夜景'}
bad2, line = [], []
for k, tg in cond.items():
    sc = [x for x in SC if x['k'] == k][0]
    # 只统计 r54 那批配方（第 55 轮补的新配方里也有对题照片，会把可用数抬上去）
    items = [it for it in sc['items'] if re.sub(r'^[rk]-', '', it['i']) in BASE_SLUGS]
    hit = sum(1 for it in items if tg in (PT.get(it['f']) or []))
    avail = 0
    for it in items:
        slug = re.sub(r'^[rk]-', '', it['i'])
        if any(tg in (PT.get(f) or []) for f in (PH.get(slug) or [])):
            avail += 1
    line.append('%s %d/%d(可用%d)' % (k, hit, len(sc['items']), avail))
    if hit != avail:
        bad2.append(k)
A(not bad2, '条件类场景把**所有可用的对题照片都用上了**（%s）' % '，'.join(line))
A(all(it['f'] and it['f'] in have for sc in SC for it in sc['items']), '所有 f 都是裸文件名且文件存在')
A(all(os.path.isfile(os.path.join(IMG, it['f'])) for sc in SC for it in sc['items']), '所有 f 在磁盘上都在')
# 描述里那行「图按画面自动归类」必须与 f 的标签一致
badp = []
for sc in SC:
    for it in sc['items']:
        m = re.match(r'^图按画面自动归类：([^（]*)（自动判断，偶尔会看错）', it.get('d') or '')
        if not m:
            continue
        want = ' / '.join(PT.get(it['f']) or [])
        if m.group(1) != want:
            badp.append((sc['k'], it['n'], m.group(1), want))
A(not badp, '「图按画面自动归类：<标签>」与所配图的标签逐字一致（不一致 %d 处：%s）' % (len(badp), badp[:3]))

# ---------- ⑦ window.SC 没动 ----------
print('=== ⑦ 场景对比（统一对比图）一个字节没动 ===')
def _scblob(t):
    i = t.index('window.SC = [')
    return json.JSONDecoder().raw_decode(t, i + len('window.SC = '))[0]


def _shape(blob):
    return [(x['k'], x['label'], len(x['items']), [it['f'] for it in x['items']]) for x in blob]


_so, _sn = _scblob(old), _scblob(src)
def _itkey(x):
    # 只比"这条是谁、配的哪张图、签名、风格"——dd/fd 是机器生成的文案，v3.10 有意重写过
    # 第 56 轮有意给重名配方加了作者区分 → n 会变，这里不比对（名字由 dv_r56/dv_r55 盯）
    return (x.get('i'), x.get('f'), x.get('a'), x.get('sl'), x.get('t'))


_same = (len(_so) == len(_sn)
         and all(a['k'] == b['k'] and a['label'] == b['label']
                 and [_itkey(x) for x in a['items']]
                 == [_itkey(x) for x in b['items'][:len(a['items'])]]
                 for a, b in zip(_so, _sn)))
A(_same, 'window.SC 的 6 个场景、原有条目的配方/图/签名/风格逐条未变（现有 %d 条；第 55 轮只重写了 100 句'
  '机器文案并往后追加了新配方，见 dv_r55）'
  % sum(len(x['items']) for x in _sn))
A(all(k in json.dumps(_sn) for k in ('marathon', 'peace-memorial', 'redbud')), 'window.SC 仍是那 6 个统一对比场景')

# ---------- ⑧ 死代码 ----------
print('=== ⑧ 死函数 pickPhoto 已删 ===')
A(src.count('pickPhoto') == 0, 'grep pickPhoto = 0 次')
A(old.count('pickPhoto') == 1, '改前它确实只出现 1 次 = 只有函数定义、没有调用（实得 %d）' % old.count('pickPhoto'))

# ---------- ⑨ 图片库 ----------
print('=== ⑨ 图片库（1200px 升级）===')
try:
    from PIL import Image
    bad = []
    big = 0
    for f in sorted(have):
        if not f.lower().endswith('.jpg'):
            continue
        try:
            w, h = Image.open(os.path.join(IMG, f)).size
        except Exception as e:
            bad.append('%s(%s)' % (f, e))
            continue
        if max(w, h) >= 1200:
            big += 1
    A(not bad, '每张图都能被 PIL 打开（坏图 %d：%s）' % (len(bad), bad[:3]))
    A(big >= 160, '长边 ≥1200 的图 %d 张（改前 1 张；原图就到 1200 的都升上去了）' % big)
    A(not [f for f in have if f.endswith('.part')], '没有残留的 .part 半包')
except ImportError:
    print('  （无 PIL，跳过）')
mani = os.path.join(ROOT, 'scripts', '_r54_fetch.json')
if os.path.exists(mani):
    d = json.load(io.open(mani, encoding='utf-8'))
    A(not d.get('fail'), '下载记账：失败 0（%s）' % (d.get('fail') or '无'))
_base_img = set(os.listdir(IMG))
A(len([f for f in _base_img if f.endswith('.jpg')]) == 534,
  '图片总数 = 534（r54 那批 431 + 第 55 轮新补的 19 条配方的 103 张；实得 %d）'
  % len([f for f in _base_img if f.endswith('.jpg')]))

# ---------- 运行时 ----------
print('=== ⑩ 运行时（按场景找配方 + 点卡片）===')
if '--runtime' in sys.argv:
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'dv_clickall.py')],
                       capture_output=True, text=True, cwd=ROOT)
    tail = (r.stdout or '')[-400:]
    A(r.returncode == 0 and '0' in tail, 'dv_clickall 仍 0 报错：%s' % tail.replace('\n', ' ')[-160:])
else:
    print('  （加 --runtime 才跑）')

print('\n===== 第 54 轮验收：%d/%d 通过 =====' % (K - F, K))
sys.exit(1 if F else 0)
