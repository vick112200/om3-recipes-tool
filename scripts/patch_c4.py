# -*- coding: utf-8 -*-
"""优化版 C4（夜景/混光）改成「4 格全部原生 A0 G0」：
- 槽 1：Paul Clark recipe（5300K）→ Cool Spring（A0 G0，冷调蓝调时刻）
- 槽 2：Portra 160（5300K）      → PNW（A0 G0，青绿柔雾）
- 同步改：档位说明 / 去掉「现场拨 5300K」补丁 / 夜景人像表 / 对比图改夜景场景
- Paul Clark recipe 与 Portra 160 挪进「这些配方得单独占一档（5300K A0 G0）」
- 场景对比页里这两卷的「C4 优化版 →」按钮跟着改到新槽位
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
P = BASE + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(BASE + r'\app\base.before_c4.html', 'w', encoding='utf-8', newline='').write(h)

recs = {r['slug']: r for r in json.load(open(BASE + r'\all_recipes.json', encoding='utf-8'))['results']}
man = json.load(open(BASE + r'\imgs960.json', encoding='utf-8'))
CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮'
CH = ['yellow', 'orange', 'orangeRed', 'red', 'magenta', 'violet',
      'blue', 'blueCyan', 'cyan', 'greenCyan', 'green', 'yellowGreen']
CHNAME = ['黄', '橙', '红', '品红', '紫', '蓝紫', '蓝', '浅蓝', '青', '绿', '黄绿', '嫩黄绿']
CHCOLOR = ['#FCF750', '#DBA12A', '#CC1210', '#CD076B', '#970AA0', '#7710E8',
           '#3054E0', '#5392EB', '#83E7EB', '#87EE77', '#9DEE3A', '#CBEE3A']
SCENES = [('rosslyn-dusk', '夜景 / 混光车流'), ('marathon', '人群 / 暖光石拱')]


def card_of(cid):
    m = re.search(r'<div class="card" id="r-%s">' % re.escape(cid), h)
    assert m, cid
    nxt = h.find('<div class="card" id="r-', m.end())
    return h[m.start():nxt]


def sgn(v):
    return '%+d' % v if v else '0'


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


def build_slot(sid, num, slug, cid, style, wbnote):
    blk = card_of(cid)
    r = recs[slug]
    e = man[slug]
    nm = re.search(r'<span class="cname">(.*?)</span>', blk).group(1)
    au = re.search(r'<span class="cauth">(.*?)</span>', blk).group(1)
    wheel = re.search(r'<svg.*?</svg>', blk, re.S).group(0)
    fnote = re.search(r'<details class="fold fnote">.*?</details>', blk, re.S)
    en = re.search(r'<details class="en">.*?</details>', blk, re.S)
    fmine = re.search(r'<details class="fold fmine">.*?</details>', blk, re.S).group(0)

    figs = []
    for sc, label in SCENES:
        f = e['cmp'][sc]
        figs.append('<figure><img loading="lazy" data-im="%s"><figcaption>对比场景 · %s（%s）</figcaption></figure>'
                    % (f, sc, label))
    for i, s in enumerate(e['samples']):
        ex = exif_short(s)
        figs.append('<figure><img loading="lazy" data-im="%s"><figcaption>作者样片 %s%s</figcaption></figure>'
                    % (s['file'], CIRCLED[i], ('　·　' + ex) if ex else ''))
    shots = ''.join(figs)

    vals = ''.join('<span class="ovc" style="border-left-color:%s">%s<b>%s</b></span>'
                   % (c, n_, sgn(r[k] or 0)) for c, n_, k in zip(CHCOLOR, CHNAME, CH))
    prm = ('色调曲线 Sh %s / Mid %s / Hi %s　｜　阴影补偿 <b>%s</b>　｜　对比 %s　｜　锐度 %s　｜　作者曝光 %s'
           % (sgn(r['shadows'] or 0), sgn(r['midtones'] or 0), sgn(r['highlights'] or 0),
              sgn(r['shadingEffect'] or 0), sgn(r['contrast'] or 0), sgn(r['sharpness'] or 0),
              ('%.1f' % ((r['exposureCompensation'] or 0) / 10.0))))

    return (
        '<div class="oslot" id="%s"><div class="osh"><span class="osnum">槽 %d</span>'
        '<span class="osname">%s</span><span class="osauth">%s</span></div><div class="osbody">'
        '<div class="oswheel">%s</div><div class="osinfo">'
        '<div class="osshots">%s</div>'
        '<div class="osline exif">样片来源 om-recipes.com：<b>对比场景</b>为本站统一拍摄'
        '（6 个场景可在「场景对比」页签按场景横向比较），<b>作者样片</b>为作者实拍，EXIF 见图注。</div>'
        '<div class="osvals">%s</div>'
        '<div class="osline style">%s</div>'
        '%s%s%s'
        '<div class="osline prm">%s</div>'
        '<div class="osline wbok">%s</div></div></div></div>'
        % (sid, num, nm, au, wheel, shots, vals, style,
           fnote.group(0) if fnote else '', en.group(0) if en else '', fmine,
           prm, wbnote))


COOL = build_slot(
    'oC4-1', 1, 'ian-will_cool-spring', 'ian-will_cool-spring',
    '蓝调时刻的冷调饱和。紫 +4、蓝 +4、蓝紫 +4、品红 +3 全线往上推，青 +3、红 +2，绿和黄绿各 +1 —— '
    '暗部略压、中间调略抬、高光略压，出来是雨后湿街、冷白 LED 街、蓝调时刻那种通透的冷色。'
    '这一档缺的就是这份冷：另外三格分别是暖黄（City Look）、中性压光（Q116）、青绿柔雾（PNW）。',
    '白平衡：原配方即 <b>A0 G0</b>，与档位一致，零位移未改动')

SUBDUED = build_slot(
    'oC4-2', 2, 'ian-will_pnw', 'ian-will_pnw',
    '雾感青绿。绿 +3、黄绿 +3、青 +2、浅蓝 +1 往上推，橙 −1、紫 −1、品红 −1 略收；'
    '锐度 −2、高光压 2 格、暗部提 2 格、对比 0 —— 雨夜湿街、雾天、混光里带一层水汽的柔。'
    '这是四格里唯一"低反差 + 青绿底子"的一格，跟槽 1 的高饱和冷紫正好错开。',
    '白平衡：原配方即 <b>A0 G0</b>，与档位一致，零位移未改动')

# ---------- 1. 换掉槽 1 / 槽 2 ----------
for sid, new in (('oC4-1', COOL), ('oC4-2', SUBDUED)):
    i = h.find('<div class="oslot" id="%s">' % sid)
    assert i > 0, sid
    j = h.find('<div class="oslot" id="oC4-%d">' % (int(sid[-1]) + 1), i)
    if j < 0:
        j = h.find('<div class="omode" id="oC5">', i)
    assert j > i
    h = h[:i] + new + h[j:]

# ---------- 2. C4 四格的对比图改成夜景场景 ----------
c4i = h.find('<div class="omode" id="oC4">')
c4j = h.find('<div class="omode" id="oC5">')
blk = h[c4i:c4j]
for slug in ['videopic_city_look', 'robsoncabanas_q116']:
    old = ('<figure><img loading="lazy" data-im="%s__cmp__marathon.jpg">'
           '<figcaption>对比场景 · marathon（人群 / 暖光石拱）</figcaption></figure>'
           '<figure><img loading="lazy" data-im="%s__cmp__peace-memorial.jpg">'
           '<figcaption>对比场景 · peace-memorial（中性白 / 蓝天绿树）</figcaption></figure>') % (slug, slug)
    new = ('<figure><img loading="lazy" data-im="%s__cmp__rosslyn-dusk.jpg">'
           '<figcaption>对比场景 · rosslyn-dusk（夜景 / 混光车流）</figcaption></figure>'
           '<figure><img loading="lazy" data-im="%s__cmp__marathon.jpg">'
           '<figcaption>对比场景 · marathon（人群 / 暖光石拱）</figcaption></figure>') % (slug, slug)
    assert blk.count(old) == 1, (slug, blk.count(old))
    blk = blk.replace(old, new, 1)
h = h[:c4i] + blk + h[c4j:]

# ---------- 3. 去掉「现场拨 5300K」补丁 chip ----------
old_chip = '<span class="omchip kt">槽 1／2 想还原就现场拨 <b>5300K</b></span>'
assert h.count(old_chip) == 1
h = h.replace(old_chip, '<span class="omchip kt">4 格全部原生 <b>A0 G0</b> 零位移</span>', 1)

old_theme = '<p class="omtheme">大光比 · 混光 · 钠灯都市 · 深沉暗部　·　Auto · 琥珀 0 / 绿 0</p>'
assert h.count(old_theme) == 1
h = h.replace(old_theme, '<p class="omtheme">大光比 · 混光 · 钠灯暖黄 · 霓虹冷调 · 蓝调时刻　·　Auto · 琥珀 0 / 绿 0</p>', 1)

# ---------- 4. 改档位说明里过时的两段 ----------
old_exp = '夜景里它们最容易溢出。三个原配方分别是 0 / −0.3 / 0，取 −0.3 最保险。'
assert h.count(old_exp) == 1, h.count(old_exp)
h = h.replace(old_exp, '夜景里它们最容易溢出。四个原配方的作者曝光是 0 / 0 / +0.7 / 0，'
                       '取 −0.3 既保住点光源、又不至于把暗部拖死。', 1)

old_tail = ('<br><b>槽 1、槽 2 的原配方是 5300K A0 G0，不是 Auto。</b>挂在 Auto 上它们不算原味还原——'
            '想要那一口的原味，进菜单把色温拨到 <b>5300K</b>（WB 按钮 → 色温 K → 前拨盘），'
            '拍完记得拨回 Auto。<b>这就是"通用夜景"和"原配方还原"之间的那个开关。</b>')
assert h.count(old_tail) == 1, h.count(old_tail)

old_exwhy = ('<b>为什么第三个槽给 City Look：</b>它只动色彩通道，色调曲线三格全中性、没有曝光补偿，'
             '白平衡本来就是 A0 G0 无偏移，挂在 Auto 上是零代价；黄推高、青一刀砍光、红收回 −4，'
             '做出人造的、接近霓虹的都会暖黄。<br>'
             '<b>为什么第四个槽给 Q116：</b>上一版它在 C5，这一版 C5 改成胶片档，它得另找地方。'
             '它不是胶片还原，放进来纯粹是<b>影调对口</b>：Q116 暗部提 3 格、高光狠压 5 格、对比 −8，'
             '是全场压缩动态范围最狠的一格之一——夜景要的正是这个：灯泡和招牌不会爆，暗部也不会糊成死黑。'
             '它的原配方本来就是 Auto A0 G0，自然融入。')
assert h.count(old_exwhy) == 1, h.count(old_exwhy)

NEW_TAIL = ('然后按<b>白平衡签名</b>把四个槽重新挑了一遍：<b>这一档现在 4 格全部是原生 A0 G0</b>，'
            '挂在 Auto 上零位移，不需要再靠"现场拨 5300K"去凑。<br>'
            '<b>这一档已经没有固定色温的槽了。</b>原来槽 1 的 Paul Clark recipe 和槽 2 的 Portra 160 '
            '原生都是 <b>5300K A0 G0</b>（固定色温），挂在 Auto 上永远是偏的；这一版把它们挪进'
            '「这些配方得单独占一档」——想还原那一口，那一档才是它们的家。腾出来的两格按'
            '<b>"白平衡零位移 + 风格不重复"</b>选：<br>'
            '<b>槽 1 给 Cool Spring</b>：原生 A0 G0，紫／蓝／蓝紫／品红全线往上推的冷调饱和——'
            '这一档另外三格分别是暖黄（City Look）、中性压光（Q116）、青绿柔雾（PNW），'
            '缺的正是"蓝调时刻／雨后冷街"这一挂。<br>'
            '<b>槽 2 给 PNW</b>：原生 A0 G0，绿 +3／黄绿 +3／青 +2 往上推，锐度和对比都往下收、'
            '高光压 2 格、暗部提 2 格——是四格里唯一"低反差 + 青绿底子"的一格，'
            '对应雨夜湿街、雾天、混光里带一层水汽的场面。')

NEW_EXWHY = ('<b>为什么第三个槽给 City Look：</b>它只动色彩通道，色调曲线三格全中性、没有曝光补偿，'
             '白平衡本来就是 A0 G0 无偏移，挂在 Auto 上是零代价；黄推高、青一刀砍光、红收回 −4，'
             '做出人造的、接近霓虹的都会暖黄。<br>'
             '<b>为什么第四个槽给 Q116：</b>上一版它在 C5，这一版 C5 改成胶片档，它得另找地方。'
             '它不是胶片还原，放进来纯粹是影调对口：Q116 暗部提 3 格、高光狠压 5 格、对比 −8，'
             '是全场压缩动态范围最狠的一格之一——夜景要的正是这个：灯泡和招牌不会爆，暗部也不会糊成死黑。'
             '它的原配方本来就是 Auto A0 G0，自然融入。<br>'
             '<b>四格的分工：</b>混光街边有人 → 槽 4 Q116（压光最稳）；'
             '钠灯／暖灯街道要那股都会暖黄 → 槽 3 City Look；'
             '蓝调时刻、雨后湿街、冷白 LED 街 → 槽 1 Cool Spring；'
             '雨夜湿雾、想要低反差的青绿 → 槽 2 PNW。')

h = h.replace(old_tail, NEW_TAIL, 1)
h = h.replace(old_exwhy, NEW_EXWHY, 1)

# ---------- 5. 夜景人像表里的槽位引用 ----------
pairs = [
    ('<tr><td>街边混光、半身 / 全身</td><td class="og">槽 1　Paul Clark recipe</td><td>Auto</td><td>关</td></tr>',
     '<tr><td>街边混光、半身 / 全身</td><td class="og">槽 4　Q116</td><td>Auto</td><td>关</td></tr>'),
    ('<tr><td>橱窗、路灯下的柔和近景</td><td class="og">槽 2　Portra 160</td><td>Auto</td><td>关</td></tr>',
     '<tr><td>橱窗、路灯下的柔和近景</td><td class="og">槽 2　PNW</td><td>Auto</td><td>关</td></tr>'),
    ('<tr><td>想要更浓的夜市人像味、脸偏暖</td><td class="og">槽 2　Portra 160</td><td>拨 4200–4600K</td><td>可开</td></tr>',
     '<tr><td>想要更浓的夜市人像味、脸偏暖</td><td class="og">槽 3　City Look</td><td>Auto</td><td>可开</td></tr>'),
    ('结论：<b>能做，而且槽 1、槽 2 本来就是干这个的</b>——夜景人像要的就两件事：压住灯泡招牌、别让灯光的色温把脸带跑。这两格正好各自负责一件。<br>',
     '结论：<b>能做，而且槽 4（Q116）本来就是干这个的</b>——夜景人像要的就两件事：压住灯泡招牌、别让灯光的色温把脸带跑。它一格同时干这两件事。<br>'),
]
for a, b in pairs:
    assert h.count(a) == 1, a[:40]
    h = h.replace(a, b, 1)

# ---------- 6. 两卷挪进「单独占一档」 ----------
anchor = '<div class="osolo"><div class="osoloh"><b>理光风格</b>'
assert h.count(anchor) == 1
NEWSOLO = (
    '<div class="osolo"><div class="osoloh"><b>Paul Clark recipe</b>'
    '<span class="osolowb">WB 5300K A0 G0</span></div>'
    '<p>原优化版 C4 槽 1。冷暖两头同时加强的补色型配方，暗部提 3 格、高光压 3 格、对比 −2，'
    '把大光比摊得最平。问题是原生 <b>5300K</b> 固定色温：挂在 Auto 档上不是原味，'
    '而夜景用 5300K 又会满屏橙黄。想要它，得让它单独占一个 C 档（白平衡设 5300K）。</p>'
    '<div class="osline ext"><b>作者说明</b>：加强暖色和冷色、收回绿和品红，配上更柔的对比、'
    '提亮的暗部、压低的高光与降低的锐度，整体均衡自然、忠实现场。</div></div>\n'
    '<div class="osolo"><div class="osoloh"><b>Portra 160</b>'
    '<span class="osolowb">WB 5300K A0 G0</span></div>'
    '<p>原优化版 C4 槽 2。中性偏柔的负片味，混合光下人脸不崩（作者建议 −0.3 EV）。'
    '与 Paul Clark recipe 的原生签名完全相同（<b>5300K A0 G0</b>），所以这两卷可以合占同一个 C 档，'
    '白平衡一个数都不用动——前提是那一档的色温设 5300K，而不是 Auto。</p></div>\n')
h = h.replace(anchor, NEWSOLO + anchor, 1)

# ---------- 7. 场景对比页的「C4 优化版 →」按钮跟着改 ----------
i = h.find('window.SC=')
SC, end = json.JSONDecoder().raw_decode(h, i + len('window.SC='))
MOVED = {'r-paul_clark_paul_clark_recipe': None, 'r-isaac-mitropoulos_portra-160': None,
         'r-ian-will_cool-spring': 'oC4-1', 'r-ian-will_pnw': 'oC4-2'}
n = 0
for sc in SC:
    for it in sc['items']:
        if it.get('i') in MOVED:
            v = MOVED[it['i']]
            if v:
                it['os'] = v
                it['osm'] = 'C4'
            else:
                it.pop('os', None)
                it.pop('osm', None)
            n += 1
h = h[:i + len('window.SC=')] + json.dumps(SC, ensure_ascii=False, separators=(',', ':')) + h[end:]
print('对比页按钮改到新槽位：%d 条' % n)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('patch_c4 完成，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
print('  新槽 1 =', re.search(r'id="oC4-1".*?<span class="osname">(.*?)</span>', h, re.S).group(1))
print('  新槽 2 =', re.search(r'id="oC4-2".*?<span class="osname">(.*?)</span>', h, re.S).group(1))
