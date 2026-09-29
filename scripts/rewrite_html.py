# -*- coding: utf-8 -*-
"""把文档里内嵌的 base64 样片换成站点 1200px 真图（相对路径 images/xxx.jpg）。

- 每张卡片：2 个统一对比场景（marathon / peace-memorial）+ 最多 3 张作者样片
- 同时把旧 figcaption / EXIF 换成站点真实数据
"""
import json, re, os, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
DOC = r'C:\Users\82302\Desktop\OM-3色彩配方手册.html'
OUTHTML = os.path.join(BASE, 'apk', 'assets', 'index.html')

SCENE_LABEL = {
    'cmp1': '对比场景 A · marathon（人群 / 暖光石拱）',
    'cmp2': '对比场景 B · peace-memorial（中性白 / 蓝天绿树）',
}
CIRCLED = '①②③④⑤⑥⑦⑧⑨'

imgs = json.load(open(os.path.join(BASE, 'imgmap.json'), encoding='utf-8'))
seen = imgs['seen']
doc2slug = {a: b for a, b, c in imgs['mapping']}
data = json.load(open(os.path.join(BASE, 'search.json'), encoding='utf-8'))
recipe_by_slug = {r['slug']: r for r in data['results']}


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


def exif_line(recipe):
    s = (recipe.get('sampleImages') or [])
    if not s:
        return '样片：本站统一拍摄的对比场景（本页取 marathon / peace-memorial），无单张 EXIF'
    x = s[0]

    def g(k):
        v = x.get(k)
        return str(v).strip() if v not in (None, '', '.') else None

    parts = []
    for k in ('camera', 'lens'):
        if g(k):
            parts.append(g(k))
    if g('shutterSpeed'):
        parts.append(g('shutterSpeed') + 's')
    if g('aperture'):
        parts.append('f/' + g('aperture'))
    if g('focalLength'):
        parts.append(g('focalLength'))
    if g('iso'):
        parts.append('ISO ' + g('iso'))
    return '样片：' + ' • '.join(parts) if parts else '样片：作者原图，无 EXIF'


def build_figs(slug):
    m = seen.get(slug)
    if not m:
        return None
    fig = []
    for key in ('cmp1', 'cmp2', 's1', 's2', 's3'):
        if key not in m:
            continue
        if key.startswith('cmp'):
            cap = SCENE_LABEL[key]
        else:
            cap = '作者样片 ' + CIRCLED[int(key[1:]) - 1]
        fig.append('<figure><img src="images/%s"/><figcaption>%s</figcaption></figure>'
                   % (m[key], cap))
    return ''.join(fig) if fig else None


h = open(DOC, encoding='utf-8').read()
h0len = len(h)
log = []
reps = []          # (start, end, newtext)

# ---------- 1. 原版卡片（先全部算好，再倒序替换） ----------
cards = [(m.group(1), m.start()) for m in re.finditer(r'<div class="card" id="r-([^"]+)">', h)]
for i, (cid, pos) in enumerate(cards):
    end = cards[i + 1][1] if i + 1 < len(cards) else h.find('<footer', pos)
    block = h[pos:end]
    slug = doc2slug.get(cid, cid)
    figs = build_figs(slug)
    if not figs:
        log.append('%-42s 无图可用' % cid[:42])
        continue
    s = block.find('<div class="shots">')
    if s < 0:
        s = block.find('<div class="cright">') + len('<div class="cright">')
        e = s
    else:
        e = find_div(block, s)
    nb = block[:s] + '<div class="shots">' + figs + '</div>' + block[e:]
    r = recipe_by_slug.get(slug)
    if r:
        ex = re.search(r'<div class="exif">.*?</div>', nb, re.S)
        if ex:
            nb = nb[:ex.start()] + '<div class="exif">' + exif_line(r) + '</div>' + nb[ex.end():]
    reps.append((pos, end, nb))
    log.append('%-42s %d 图' % (cid[:42], figs.count('<img')))

# ---------- 2. 优化版槽位 ----------
name2slug = {}
for slug, r in recipe_by_slug.items():
    name2slug.setdefault((r['recipeName'].strip().lower(), r['authorName'].strip().lower()), slug)

slots = [(m.group(1), m.start()) for m in re.finditer(r'<div class="oslot" id="(oC[^"]+)">', h)]
for i, (sid, pos) in enumerate(slots):
    nxt = slots[i + 1][1] if i + 1 < len(slots) else h.find('<div class="omode"', pos)
    block = h[pos:nxt]
    nm = re.search(r'<span class="osname">(.*?)</span>', block)
    au = re.search(r'<span class="osauth">(.*?)</span>', block)
    if not nm or not au:
        log.append('%-42s 跳过' % sid)
        continue
    slug = name2slug.get((nm.group(1).strip().lower(), au.group(1).strip().lower())) or doc2slug.get(sid)
    figs = build_figs(slug) if slug else None
    s = block.find('<div class="osshots">')
    if not figs:
        log.append('%-42s 自配 / 无图，保持占位' % sid)
        continue
    if s < 0:
        # 之前没有图：插到 osinfo 开头
        s = block.find('<div class="osinfo">') + len('<div class="osinfo">')
        e = s
    else:
        e = find_div(block, s)
    nb = block[:s] + '<div class="osshots">' + figs + '</div>' + block[e:]
    r = recipe_by_slug.get(slug)
    ex = re.search(r'<div class="osline exif">.*?</div>', nb, re.S)
    if ex and r:
        nb = nb[:ex.start()] + '<div class="osline exif">' + exif_line(r) + '</div>' + nb[ex.end():]
    reps.append((pos, nxt, nb))
    log.append('%-42s %d 图' % (sid, figs.count('<img')))

for s, e, t in sorted(reps, key=lambda x: x[0], reverse=True):
    h = h[:s] + t + h[e:]

# ---------- 3. 说明文字 ----------
for a, b in [
    ('样片为固定的一套 14 个标准参考场景，各配方共用同一批场景以便横向对比。',
     '样片分两种：<b>对比场景</b>（marathon / peace-memorial 两个固定场景，全站同一场景拍摄，便于横向比较）'
     '与<b>作者样片</b>（各位作者的实拍原图）。两者均取自 om-recipes.com，1200px。'),
    ('每格下方的<b>样片</b>取自站上该作者的原图，与「原版方案」页签里的是同一批（同一套标准场景）；',
     '每格下方的<b>样片</b>取自 om-recipes.com（1200px）：前两张是全站统一的对比场景，后面是该作者的实拍样片；'),
]:
    if h.count(a) == 1:
        h = h.replace(a, b, 1)
        log.append('说明文字已更新')

open(OUTHTML, 'w', encoding='utf-8', newline='').write(h)
print('\n'.join(log))
print()
print('剩余 base64 图片: %d' % h.count('base64,'))
print('体积 %.2f MB -> %.2f MB' % (h0len / 1048576, len(h) / 1048576))
print('输出 ->', OUTHTML)
