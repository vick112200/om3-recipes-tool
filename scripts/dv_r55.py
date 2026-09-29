# -*- coding: utf-8 -*-
"""第 55 轮验收：把站点现存的 19 条配方补成卡片（+ REC / IDX / 场景 / 计数）

跑法：python scripts/dv_r55.py            # 只跑静态（快）
      python scripts/dv_r55.py --runtime  # 额外跑运行时（无头 Chrome 点卡片 / 搜 porta）

断的东西见 SPEC-round55.md §8 的 12 条。
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from om3_profile import con_word, dir_word, gen6, profile, sat_word, wbtxt   # noqa: E402

P = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r55.html')
IMG = os.path.join(ROOT, 'apk', 'assets', 'images')
SNAP = os.path.join(ROOT, 'all_recipes.json')
EXTRA = os.path.join(HERE, '_r55_extra.json')

NEW = [
    'kaleigh-whitaker_bluegill-teal', 'alberto_torrejon_bleached', 'tom-jackson_porta-400-print',
    'isaac-mitropoulos_dreamy-white', 'ali_o_keefe_omtc_chrome', 'paul_clark_paul_clark_recipe',
    'chris-brogan_a-bit-more-vivid', 'kitty-marie_red-soda-pop', 'terry_mclaughlin_terry_mclaughlin_recipe',
    'stella-toul_carte-postal', 'isaac-mitropoulos_portra-160', 'isaac-mitropoulos_portra-400',
    'jerred_z_eternal_sunshine', 'luis-chavez_dirty-pop', 'karol-mizunia_vintage-teal',
    'emily_m4nerds_m4nerds', 'dave_herring_vibrant_chrome', 'burak-yilmaz_portside-chrome',
    'burak-yilmaz_asteroid-city',
]
AX = ['黄', '橙', '橙红', '红', '品红', '紫', '蓝', '浅蓝', '青', '绿青', '绿', '黄绿']

src = io.open(P, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
have = set(os.listdir(IMG))
by = {r['slug']: r for r in json.load(io.open(SNAP, encoding='utf-8'))['results']}
by[json.load(io.open(EXTRA, encoding='utf-8'))['slug']] = json.load(io.open(EXTRA, encoding='utf-8'))
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
    obj, _ = json.JSONDecoder().raw_decode(s, j)
    return obj


def grab_var(s, marker):
    j = s.index(marker) + len(marker)
    while s[j] in ' \n':
        j += 1
    obj, _ = json.JSONDecoder().raw_decode(s, j)
    return obj


def cut(s, slug):
    i = s.find('<div class="card" id="r-%s">' % slug)
    if i < 0:
        return None
    d, k = 0, i
    while True:
        m = re.compile(r'<div\b|</div>').search(s, k)
        d += -1 if m.group(0) == '</div>' else 1
        k = m.end()
        if d == 0:
            return s[i:k]


def sig_of(rec):
    return wbtxt(rec['wba'], rec['wbg'])


REC = grab(src, '__OM3RECIPES__')
IDX = grab_var(src, 'var IDX=')
SC = grab(src, '__OM3SC__')
SCENES = grab(src, '__OM3SCENES__')
PH = grab_var(src, 'window.__OM3PHOTOS__ = ')
PT = grab_var(src, 'window.__OM3PHOTOTAGS__ = ')
byr = {r['slug']: r for r in REC}

print('=== ① 卡片：19 张都在 #pool 里，且分组/计数正确 ===')
a = src.index('<details class="sec" id="pool">')
b = src.index('id="paneB"')
pool = src[a:b]
miss = []
for slug in NEW:
    c = cut(src, slug)
    if not c:
        miss.append(slug)
A(not miss, '19 条都有 r-<slug> 卡片（缺 %s）' % (miss or 0))
A(all(('<div class="card" id="r-%s">' % x) in pool for x in NEW), '19 张都挂在 #pool「更多配方」下')
heads = [(m.group(1), m.start()) for m in re.finditer(r'<h3 id="(pool-[^"]+)">', pool)]
heads.append(('(END)', pool.rindex('</div></details>')))
bad_cnt = []
for k in range(len(heads) - 1):
    nm, i = heads[k]
    blk = pool[i:heads[k + 1][1]]
    n = blk.count('<div class="card"')
    m = re.search(r'· (\d+) 个', blk)
    if not m or int(m.group(1)) != n:
        bad_cnt.append((nm, m.group(1) if m else '?', n))
A(not bad_cnt, '每个 >偏移组< 的「· N 个」都等于实际卡片数（不符 %s）' % (bad_cnt[:3] or 0))
n_grp = len(re.findall(r'<h3 id="pool-', src))
A(n_grp == 28, '#pool 组数 28（原 20 + 本轮新建 8）：实得 %d' % n_grp)

print('\n=== ② 新卡的签名 / 标签 / 折页与数据逐字一致 ===')
bad_sig, bad_tag, bad_fold, bad_en = [], [], [], []
for slug in NEW:
    c = cut(src, slug)
    rec = byr.get(slug)
    if not c or not rec:
        continue
    m = re.search(r'<span class="slot">([^<]*)</span>', c)
    if not m or m.group(1) != sig_of(rec):
        bad_sig.append((slug, m.group(1) if m else '?', sig_of(rec)))
    p = profile(rec)
    t3 = '<div class="tags"><span>%s</span><span>%s</span><span>%s</span></div>' % (
        sat_word(p), dir_word(p), con_word(p))
    if t3 not in c:
        bad_tag.append(slug)
    g = gen6(rec)
    for key in ('feel', 'key', 'tone', 'good', 'bad'):
        txt = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', g[key]).replace('&', '&amp;')
        if txt.replace('&amp;', '&') not in c.replace('&amp;', '&'):
            bad_fold.append((slug, key))
    if (by[slug].get('description') or '').strip():
        if 'English original' not in c or '中文为本手册翻译' not in c:
            bad_en.append(slug)
A(not bad_sig, '签名 chip == REC 的 wba/wbg（不一致 %s）' % (bad_sig[:3] or 0))
A(not bad_tag, '三段式标签与参数一致（不一致 %s）' % (bad_tag[:3] or 0))
A(not bad_fold, '参数解读六行与 gen6 逐字一致（不一致 %s）' % (bad_fold[:3] or 0))
A(not bad_en, '有站点原文的卡都带 English original + 「本站翻译」标注（缺 %s）' % (bad_en[:3] or 0))

print('\n=== ③ 色轮：19 张卡的 12 轴与数据一致 ===')
bad_wheel = []
for slug in NEW:
    c = cut(src, slug)
    rec = byr.get(slug)
    if not c or not rec:
        continue
    m = re.search(r'<div class="vals">([^<]*)</div>', c)
    want = ' '.join('%+d' % x for x in rec['v'])
    if not m or m.group(1) != want:
        bad_wheel.append((slug, m.group(1) if m else '?', want))
A(not bad_wheel, 'vals 行与 REC.v 逐字一致（不一致 %s）' % (bad_wheel[:3] or 0))

print('\n=== ④ REC / IDX / 计数 ===')
A(len(REC) == 80, '__OM3RECIPES__ = 80 条（原 79 + Porta 400 Print；实得 %d）' % len(REC))
A(all(x in byr for x in NEW), '19 个新 slug 全在 REC 里')
old_rec = grab(old, '__OM3RECIPES__')
# 第 56 轮：重名配方有意加了作者区分 → 那几条的 n 允许变，其余字段必须逐字节不变
RENAMED = {r['slug'] for r in old_rec if r['slug'] in byr and byr[r['slug']]['n'] != r['n']}
_changed = []
for r in old_rec:
    q = byr.get(r['slug'])
    if not q:
        _changed.append((r['slug'], '缺'))
        continue
    if any(q.get(k) != v for k, v in r.items() if k != 'n'):
        _changed.append((r['slug'], '字段变了'))
A(not _changed, '原 79 条记录未变（除第 56 轮 %d 条改名的 n；异常 %s）'
  % (len(RENAMED), _changed[:3] or 0))
A(len(IDX) == 129, 'IDX = 129 条（原 110 + 19；实得 %d）' % len(IDX))
A(sum(1 for x in IDX if x['h'].startswith('r-')) == 77, 'IDX 里 r- 条目 77 条（58+19；实得 %d）'
  % sum(1 for x in IDX if x['h'].startswith('r-')))


def sim_search(q):
    """按页面 search() 的口径模拟：SYN 展开 → 命中 F 里任一字段"""
    syn = re.search(r'var SYN=\{(.*?)\n \};', src, re.S)
    table = {}
    for m in re.finditer(r"'([^']+)':\[(.*?)\]", syn.group(1)):
        table[m.group(1)] = [x.strip().strip("'") for x in m.group(2).split(',') if x.strip()]
    qs = [q] + table.get(q, [])
    out = []
    for it in IDX:
        blob = ' '.join(str(it.get(f) or '') for f in ('n', 'a', 't', 'g', 'f')).lower()
        if any(x.lower() in blob for x in qs):
            out.append(it['n'])
    return out


A(len(sim_search('portra')) >= 7, '搜 portra 命中 ≥7（实得 %d）' % len(sim_search('portra')))
A(len(sim_search('porta')) >= 4,
  '搜 porta（站点拼法）也命中 ≥4 —— SYN 别名（实得 %d：%s）'
  % (len(sim_search('porta')), sim_search('porta')[:5]))
namehit = [x for x in NEW if not sim_search(byr[x]['n'].split('（')[0].lower()[:6])]
A(not namehit, '19 条新配方都能按名字搜到（搜不到 %s）' % (namehit[:3] or 0))
A('全站 80 条配方' in src and '全站 79 条配方' not in src, '计数文案 = 全站 80 条配方')

print('\n=== ⑤ 场景：每条至少进 1 个场景 + 结构一致 ===')
inrec = {}
for sc in SC:
    for it in sc['items']:
        s2 = (it.get('i') or '')[2:]
        inrec.setdefault(s2, []).append(sc['k'])
none = [x for x in NEW if x not in inrec]
A(not none, '19 条都进了 ≥1 个场景（没进的 %s）' % (none or 0))
dup = [sc['k'] for sc in SC
       if len({it['i'] for it in sc['items'] if (it.get('i') or '')[2:] in NEW}) !=
       len([it for it in sc['items'] if (it.get('i') or '')[2:] in NEW])]
A(not dup, '同一场景里没有重复的新配方（重复的 %s）' % (dup[:3] or 0))
badf = [it['f'] for sc in SC for it in sc['items']
        if (it.get('i') or '')[2:] in NEW and it.get('f') not in have]
A(not badf, '新条目的配图都在磁盘上（缺 %s）' % (badf[:3] or 0))
badtag = []
for sc in SC:
    for it in sc['items']:
        if (it.get('i') or '')[2:] not in NEW:
            continue
        tags = ' / '.join(PT.get(it.get('f')) or [])
        dd = it.get('d') or ''
        # 第 56 轮口径：命中场景期望 → 写「图按画面自动归类：<tags>」；没命中 → 写实兜底
        # （两种都算过，但**不许两边都不像**：见 dv_r56 的③）
        # 第 57 轮又多了两种合法说明：人工挑选（白名单）、本场景不挑题材（没检测依据）
        if tags and ('图按画面自动归类：%s（自动判断，偶尔会看错）' % tags) not in dd \
                and not dd.startswith(('本条没有对「', '本场景不挑题材', '人工挑选：')):
            badtag.append((it['n'], it['f'], dd[:30]))
A(not badtag, '第 55 轮那 19 条的说明不是"谎报"就是"实说兜底"（不一致 %s）' % (badtag[:3] or 0))
badkey = [it['n'] for sc in SC for it in sc['items']
          if any(x in (it.get('dd') or '') for x in ('把 无 推上去', '具体到画面：。'))]
A(not badkey, '场景描述里没有 gen6 的退化句子（还有 %s）' % (badkey[:3] or 0))

print('\n=== ⑤b 侧边目录与 #pool 一致 ===')
_toc = src[src.index('更多配方（按白平衡偏移）</div>'):src.index('固定色温（', src.index('更多配方（按白平衡偏移）</div>'))]
_toc_grp = re.findall(r'<a class="lv2" href="#(pool-[^"]+)">([^<]*)</a>', _toc)
_toc_card = set(re.findall(r'<a class="lv3(?: more)?" href="#r-([^"]+)"', _toc))   # 明链 + 「展开其余」里的隐藏链
_pool_grp = re.findall(r'<h3 id="(pool-[^"]+)">([^&<]*)', pool)
A([g for g, _ in _toc_grp] == [g for g, _ in _pool_grp],
  '目录里的签名组与 #pool 的组一一对应（目录 %d / 页面 %d）' % (len(_toc_grp), len(_pool_grp)))
_bad_cnt = []
for gid, txt in _toc_grp:
    i = pool.index('<h3 id="%s">' % gid)
    nxt = re.search(r'<h3 id="pool-', pool[i + 5:])
    blk = pool[i:(i + 5 + nxt.start()) if nxt else pool.rindex('</div></details>')]
    n = blk.count('<div class="card"')
    if ('· %d 个' % n) not in txt:
        _bad_cnt.append((gid, txt, n))
A(not _bad_cnt, '目录里每组「· N 个」== 实际卡片数（不符 %s）' % (_bad_cnt[:3] or 0))
_pool_card = set(re.findall(r'<div class="card" id="r-([^"]+)">', pool))
A(_pool_card == _toc_card,
  '目录里每张卡都能点到（缺 %s / 多 %s）' % (sorted(_pool_card - _toc_card)[:3], sorted(_toc_card - _pool_card)[:3]))

print('\n=== ⑤c 实拍对比（window.SC 的 6 个统一场景）也补进来了 ===')
_SC = grab_var(src, 'window.SC = ')
_have = set(os.listdir(IMG))
_sc_new, _sc_miss = 0, []
for sc in _SC:
    got = {it.get('i') for it in sc['items']}
    for slug in NEW:
        f = '%s__cmp__%s.jpg' % (slug, sc['k'])
        if f in _have:
            if ('r-' + slug) in got:
                _sc_new += 1
            else:
                _sc_miss.append((sc['k'], slug))
A(not _sc_miss, '有对比图的（统一场景 × 新配方）都进了实拍对比（缺 %d：%s）' % (len(_sc_miss), _sc_miss[:3] or 0))
_badf = [it['f'] for sc in _SC for it in sc['items']
         if (it.get('i') or '')[2:] in NEW and it['f'] not in _have]
A(not _badf, '实拍对比里新条目的图都在磁盘上（缺 %s）' % (_badf[:3] or 0))
_badd = [it['i'] for sc in _SC for it in sc['items']
         if (it.get('i') or '')[2:] in NEW and not (it.get('dd') or '').strip()]
A(not _badd, '实拍对比里新条目都带描述（缺 %s）' % (_badd[:3] or 0))
_dup = [sc['k'] for sc in _SC
        if len([it for it in sc['items'] if (it.get('i') or '')[2:] in NEW]) !=
        len({it['i'] for it in sc['items'] if (it.get('i') or '')[2:] in NEW})]
A(not _dup, '实拍对比里同一场景没有重复的新配方（%s）' % (_dup[:3] or 0))
A(_sc_new >= 90, '实拍对比新增条目 %d 条（统一场景 × 有对比图的新配方）' % _sc_new)

print('\n=== ⑥ 顺带修的旧文案 + 图片库 ===')
A('把 无 推上去' not in src and '具体到画面：。' not in src,
  '整页已无「色环把 无 推上去」「具体到画面：。」（顺带修 11 张卡 + 32 处场景条目）')
n_new = len([f for x in NEW for f in (PH.get(x) or [])])
A(n_new >= 100, '19 条的图已入库 ≥100 张（实得 %d）' % n_new)
oldph = grab_var(old, 'window.__OM3PHOTOS__ = ')
keep = {k: v for k, v in oldph.items() if k not in NEW}
A(all(PH.get(k) == v for k, v in keep.items()), '原有 60 个配方的图清单未变')
badimg, parts = [], [f for f in have if f.endswith('.part')]
try:
    from PIL import Image
    import warnings
    warnings.simplefilter('ignore')
    for x in NEW:
        for f in (PH.get(x) or []):
            Image.open(os.path.join(IMG, f)).size
except Exception as e:
    badimg.append(str(e))
A(not badimg and not parts, '新图都能打开、没有 .part 残留（坏 %s / .part %d）' % (badimg[:2] or 0, len(parts)))
A(len(keep) == len(oldph) - len([x for x in NEW if x in oldph]),
  'PHOTOS 里原有配方条目没被删（%d → %d，其中 %d 条是新的）'
  % (len(oldph), len(keep), len([x for x in NEW if x in oldph])))

if '--runtime' in sys.argv:
    print('\n=== ⑦ 运行时（无头 Chrome） ===')
    for name, args in (('dv_clickall', []), ('check_syntax', [])):
        r = subprocess.run([sys.executable, os.path.join(HERE, name + '.py')] + args,
                           capture_output=True, text=True, encoding='utf-8')
        tail = (r.stdout or '').strip().splitlines()[-1:] or ['']
        A(r.returncode == 0, '%s rc=%d：%s' % (name, r.returncode, tail[0][:90]))

print('\n===== 第 55 轮验收：%d/%d 通过 =====' % (K - F, K))
sys.exit(1 if F else 0)
