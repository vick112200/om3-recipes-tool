# -*- coding: utf-8 -*-
"""生成 App / 网页版 HTML：换图 + 场景对比 + 全屏看图 + 档位切换。"""
import json, os, re, sys, html

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'C:\Users\82302\Desktop\OM-3色彩配方手册.html'
OUTDIR = os.path.join(BASE, 'app')
os.makedirs(OUTDIR, exist_ok=True)

SCENES = [('marathon', '人群 / 暖光石拱'), ('peace-memorial', '中性白 / 蓝天绿树'),
          ('redbud', '花卉 / 粉红与绿'), ('rosslyn-dusk', '夜景 / 混光车流'),
          ('misty-mountains', '冷调 / 雾与远景'), ('moss', '绿意 / 暗部细节')]
CARD_SCENES = ['marathon', 'peace-memorial']
CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮'

man = json.load(open(os.path.join(BASE, 'imgs960.json'), encoding='utf-8'))
imap = json.load(open(os.path.join(BASE, 'imgmap.json'), encoding='utf-8'))
doc2slug = {}
for cid, slug, files in imap['mapping']:
    doc2slug[cid] = slug

_recipes = json.load(open(os.path.join(BASE, 'search.json'), encoding='utf-8'))['results']
name2slug = {}
for _r in _recipes:
    name2slug.setdefault((_r['recipeName'].strip().lower(), _r['authorName'].strip().lower()), _r['slug'])

h = open(SRC, encoding='utf-8').read()
log = []


def find_div(s, start):
    depth, i = 0, start
    while True:
        m = re.compile(r'<div\b|</div>').search(s, i)
        if not m:
            return None
        if m.group(0) == '</div>':
            depth -= 1
            if depth == 0:
                return m.end()
        else:
            depth += 1
        i = m.end()


def exif_short(s):
    p = []
    if s.get('focal'):
        p.append(str(s['focal']))
    if s.get('aperture'):
        p.append('f/' + str(s['aperture']))
    if s.get('shutter'):
        p.append(str(s['shutter']) + 's')
    if s.get('iso'):
        p.append('ISO ' + str(s['iso']))
    return ' '.join(p)


def sample_caption(i, s):
    e = exif_short(s)
    return '作者样片 ' + CIRCLED[i] + (('　·　' + e) if e else '')


def figs_for(slug, docid):
    e = man.get(slug)
    if not e:
        return None
    out = []
    for sc in CARD_SCENES:
        f = e['cmp'].get(sc)
        if not f:
            continue
        label = dict(SCENES)[sc]
        out.append('<figure><img loading="lazy" data-im="%s"><figcaption>对比场景 · %s（%s）</figcaption></figure>' % (f, sc, label))
    for i, s in enumerate(e['samples']):
        out.append('<figure><img loading="lazy" data-im="%s"><figcaption>%s</figcaption></figure>'
                   % (s['file'], sample_caption(i, s)))
    return ''.join(out) if out else None


EXIF_NOTE = ('样片来源 om-recipes.com：<b>对比场景</b>为本站统一拍摄（6 个场景可在「场景对比」页签按场景横向比较），'
             '<b>作者样片</b>为作者实拍，EXIF 见图注。')

# ---------- 1. 原版卡片 / 优化版槽位换图 ----------
reps = []
cards = [(m.group(1), m.start()) for m in re.finditer(r'<div class="card" id="r-([^"]+)">', h)]
for i, (cid, pos) in enumerate(cards):
    end = cards[i + 1][1] if i + 1 < len(cards) else h.find('<footer', pos)
    block = h[pos:end]
    figs = figs_for(doc2slug.get(cid, cid), cid)
    if not figs:
        log.append('%-42s 无图' % cid[:42])
        continue
    s = block.find('<div class="shots">')
    if s < 0:
        s = block.find('<div class="cright">') + len('<div class="cright">')
        e = s
    else:
        e = find_div(block, s)
    nb = block[:s] + '<div class="shots">' + figs + '</div>' + block[e:]
    ex = re.search(r'<div class="exif">.*?</div>', nb, re.S)
    if ex:
        nb = nb[:ex.start()] + '<div class="exif">' + EXIF_NOTE + '</div>' + nb[ex.end():]
    reps.append((pos, end, nb))
    log.append('%-42s %d 图' % (cid[:42], figs.count('<img')))

slots = [(m.group(1), m.start()) for m in re.finditer(r'<div class="oslot" id="(oC[^"]+)">', h)]
for i, (sid, pos) in enumerate(slots):
    nxt = slots[i + 1][1] if i + 1 < len(slots) else h.find('<div class="omode"', pos)
    block = h[pos:nxt]
    nm = re.search(r'<span class="osname">(.*?)</span>', block)
    au = re.search(r'<span class="osauth">(.*?)</span>', block)
    slug = doc2slug.get(sid)
    if not slug and nm and au:
        slug = name2slug.get((nm.group(1).strip().lower(), au.group(1).strip().lower()))
    figs = figs_for(slug, sid) if slug else None
    if not figs:
        log.append('%-42s 自配，保持占位' % sid)
        continue
    s = block.find('<div class="osshots">')
    if s < 0:
        s = block.find('<div class="osinfo">') + len('<div class="osinfo">')
        e = s
    else:
        e = find_div(block, s)
    nb = block[:s] + '<div class="osshots">' + figs + '</div>' + block[e:]
    ex = re.search(r'<div class="osline exif">.*?</div>', nb, re.S)
    if ex:
        nb = nb[:ex.start()] + '<div class="osline exif">' + EXIF_NOTE + '</div>' + nb[ex.end():]
    reps.append((pos, nxt, nb))
    log.append('%-42s %d 图' % (sid, figs.count('<img')))

for s, e, t in sorted(reps, key=lambda x: x[0], reverse=True):
    h = h[:s] + t + h[e:]

# ---------- 2. 优化版档位切换条 ----------
MT = '<div class="modetabs" id="modetabs">' + ''.join(
    '<button type="button" data-m="oC%d">C%d %s</button>' % (i, i, t)
    for i, t in enumerate(['人像', '街拍纪实', '风光旅行', '夜景 / 混光', '胶片'], 1)) + '</div>\n'
anchor = '<div class="omode" id="oC1">'
assert h.count(anchor) == 1
h = h.replace(anchor, MT + anchor, 1)
log.append('已插入 C1–C5 切换条')

# ---------- 3. 第三个顶层页签 ----------
old = '<button type="button" data-p="B">优化版</button>'
assert h.count(old) == 1
h = h.replace(old, old + '<button type="button" data-p="C">场景对比</button>', 1)
log.append('已加「场景对比」页签')

# ---------- 4. 场景对比数据 ----------
idx = {}
m = re.search(r'var IDX=(\[.*?\]);', h, re.S)
if m:
    for it in json.loads(m.group(1)):
        idx[it['h']] = it

order = [cid for cid, _ in cards]
SC = []
for sc, label in SCENES:
    items = []
    for cid in order:
        slug = doc2slug.get(cid)
        e = man.get(slug) if slug else None
        if not e or sc not in e['cmp']:
            continue
        it = idx.get('r-' + cid, {})
        items.append({'f': e['cmp'][sc], 'n': e['name'],
                      'a': e['author'], 't': it.get('t', ''), 'd': it.get('f', '')})
    SC.append({'k': sc, 'label': label, 'items': items})
    log.append('场景 %-16s %d 个配方' % (sc, len(items)))

bar = ''.join('<button type="button" data-i="%d">%s<span>%s</span></button>' % (i, s['k'], s['label'])
              for i, s in enumerate(SC))
PANE_C = ('<div id="paneC" class="pane hide"><div class="wrap">\n'
          '<h1>场景对比</h1>\n'
          '<p class="sub">同一个场景、同一个构图，%d 个配方各出一张 —— 挑场景，左右滑动，直接比色</p>\n'
          '<div class="scbar" id="scbar">%s</div>\n'
          '<div class="scpager" id="scpager"></div>\n'
          '<div class="scnav"><button type="button" id="scprev">‹</button>'
          '<span class="scpos" id="scpos"></span><button type="button" id="scnext">›</button></div>\n'
          '<p class="onote">手机一屏一张，左右滑动切换；平板横屏一屏三张，一次翻三张。点图片可全屏放大（双指缩放 / 左右滑动）。</p>\n'
          '</div></div>\n') % (len(order), bar)
tail = h.rfind('<script>')
h = h[:tail] + PANE_C + h[tail:]
log.append('已插入「场景对比」页签内容')

# ---------- 5. 注入 CSS / JS ----------
css = open(os.path.join(BASE, 'app_extra.css'), encoding='utf-8').read()
js = open(os.path.join(BASE, 'app_extra.js'), encoding='utf-8').read()
i = h.rfind('</style>')
h = h[:i] + css + h[i:]
log.append('已注入 CSS %d 字节' % len(css))

scjson = json.dumps(SC, ensure_ascii=False, separators=(',', ':'))
i = h.rfind('</body>')
h = h[:i] + '<script>window.SC=' + scjson + ';</script>\n<script>' + js + '</script>\n' + h[i:]
log.append('已注入 JS %d 字节，场景数据 %d 字节' % (len(js), len(scjson)))

OUT = os.path.join(OUTDIR, 'index.html')
open(OUT, 'w', encoding='utf-8', newline='').write(h)
print('\n'.join(log))
print()
print('输出 %s  %.0f KB' % (OUT, len(h.encode('utf-8')) / 1024))
