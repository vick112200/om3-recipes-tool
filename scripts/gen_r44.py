# -*- coding: utf-8 -*-
"""第 44 轮 · 档位推荐扩成「10 个候选档」（幂等）

做法（增量、可验证）：
  · C1–C5 是原来的主题档（人像 / 街拍 / 风光 / 夜景 / 胶片），**整块保留不动**（手写正文质量高）
  · 按「白平衡签名」补 5 个新候选档 C6–C10，把原方案没覆盖到的签名补进来
  · 新档的槽位**全部由 `recipe_slot.py` 从数据生成**（色轮 / osvals / 样片 / 原文 / 补充 / 参数 / 白平衡行）
  · 新档**一律用原生签名**，0 位移（守住「只有 1 格动过白平衡」的诚实底线）
  · 页首 / 顶栏跳转条 / modetabs 同步说明「相机只有 C1–C5，从这 10 个里挑 5 个」

真源：`__OM3RECIPES__` + 配方卡片 + `IDX` + `__OM3PHOTOS__`，所以改配方内容后重跑本脚本即可。
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recipe_slot as SL          # noqa: E402
import recipe_wheel as W          # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
D = json.JSONDecoder()
LOG = []

# ------------------------------------------------------------------ 5 个新候选档
# 每档：签名必须是所有槽位的原生签名（0 位移）；label 用于 modetabs；title 用于档位卡
TIERS = [
    dict(tag='C6', label='C6 暖调玫瑰', title='暖调玫瑰（人像）', key='A+4 M1', a=4, g=-1,
         theme='暖调 · 玫瑰肤色 · 人像　·　Auto · 琥珀 +4 / 品红 +1',
         md='A 档', md_why='光圈优先',
         why='<b>为什么用 A 档：</b>这一档两卷都是拍人的。A 档把光圈定在 f/1.8–f/2.8，让背景化开；ISO 设自动上限 '
             '3200，快门交给机器，人脸不容易拍虚。要更浅的景深就手动再开一档。',
         note='两卷的原始曝光补偿都是 0，取 0 最稳；肤色本就偏暖，别再往上推曝光。',
         slots=['andrew-gow_rose-gold', 'ali_o_keefe_omtc_warm']),
    dict(tag='C7', label='C7 浓郁冷暖', title='浓郁冷暖（现代胶片）', key='A+4 G+3', a=4, g=3,
         theme='浓郁 · 冷暖互补 · 现代胶片　·　Auto · 琥珀 +4 / 绿 +3',
         md='S 档', md_why='快门优先',
         why='<b>为什么用 S 档：</b>这一档两卷都靠"浓"和"平"取胜，适合会动的东西（街上的车、走动的路人）。'
             'S 档钉快门、ISO 自动，构图时不用管曝光。',
         note='两卷的原始曝光补偿都是 −0.7，说明作者觉得它们亮部容易顶；先按 0 拍，容易糊再往下压。',
         slots=['basi-torre_cinematic-tundra', 'ibd-fuji-classic-neg']),
    dict(tag='C8', label='C8 偏冷都市', title='偏冷都市（青蓝）', key='A+2 M1', a=2, g=-1,
         theme='偏冷 · 都市 · 青蓝　·　Auto · 琥珀 +2 / 品红 +1',
         md='S 档', md_why='快门优先',
         why='<b>为什么用 S 档：</b>这一档是给街上的抓拍用的（市集、人文、走动的人）。'
             'S 档把快门钉在 1/250，ISO 自动上限 6400，抬手就能按。',
         note='两卷的原始曝光补偿都是 0，取 0。',
         slots=['ali-o-keefe_omtc-cool', 'james_bloomer_kodachrome_slim_aarons']),
    dict(tag='C9', label='C9 青调柔雾', title='青调柔雾（清透风光）', key='A+2 G0', a=2, g=0,
         theme='清透 · 青调 · 柔雾　·　Auto · 琥珀 +2 / 绿 0',
         md='A 档', md_why='光圈优先',
         why='<b>为什么用 A 档：</b>这一档两卷都是风光/旅拍取向——青调、柔雾、干净。'
             'A 档收光圈要景深和画质，上三脚架时切 M 档、关防抖。',
         note='两卷的原始曝光补偿都是 0，取 0；青调配方容易显得欠曝，逆光时手动 +1/3 试试。',
         slots=['james-bloomer_om-3-tokyo-wetzlar', 'ali_o_keefe_omtc_soft']),
    dict(tag='C10', label='C10 Kodachrome', title='Kodachrome 怀旧（两版）', key='A+3 M1', a=3, g=-1,
         theme='怀旧 · 老柯达 · 两版对照　·　Auto · 琥珀 +3 / 品红 +1',
         md='A 档', md_why='光圈优先',
         why='<b>为什么用 A 档：</b>这一档是"慢慢拍"的题材（老街、旧物、有年代感的场景）。'
             'A 档控制景深，构图为主。',
         note='两卷的原始曝光补偿都是 0，取 0。',
         slots=['tom-jackson_kodachrome-64-print', 'james-bloomer_kodachrome-64-v0']),
]

s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r44.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r44.html')


def blk(key):
    i = s.find(key)
    p = s.index('=', i) + 1
    while s[p].isspace():
        p += 1
    return D.raw_decode(s, p)[0]


REC = blk('window.__OM3RECIPES__')
IDX = blk('var IDX')
by = dict((r['slug'], r) for r in REC)
f_of = dict((x['h'], x.get('f') or '') for x in IDX)


def card_seg(slug):
    i = s.find('<div class="card" id="r-%s">' % slug)
    assert i > 0, '找不到卡片：' + slug
    j = s.find('<div class="card" id="r-', i + 10)
    if j < 0:
        j = s.find('</details>', i)
    return s[i:j]


# ------------------------------------------------------------------ 生成新档的槽位
print('=== 生成 C6–C10 的槽位 ===')
NEW_BLOCKS = []
SLOT_IDS = []
for t in TIERS:
    body = []
    for n, slug in enumerate(t['slots'], 1):
        r = by[slug]
        assert (r['wba'] or 0) == t['a'] and (r['wbg'] or 0) == t['g'], \
            '%s 的签名 %d/%d 与本档 %d/%d 不符' % (slug, r['wba'] or 0, r['wbg'] or 0, t['a'], t['g'])
        sid = 'o%s-%d' % (t['tag'], n)
        body.append(SL.slot_html(sid, n, r, card_seg(slug), f_of.get('r-' + slug, ''), t['a'], t['g']))
        SLOT_IDS.append(sid)
    sigtxt = SL.sig(t['a'], t['g'])
    names = '、'.join(by[x]['n'] for x in t['slots'])
    omwb = (
        '<details class="fold fomwb"><summary>为什么白平衡是 %s：</summary><div class="foldbody">'
        '<b>为什么白平衡是 %s：</b><b>这一档一格没动。</b>%s 在站上登记的白平衡都是 <b>%s</b>，'
        '直接落位。<br>这一档是按<b>白平衡签名</b>挑出来的候选：原方案的 C1–C5 只覆盖了四个签名，'
        '库里还有一批「签名一致、但题材和色轮完全不同」的配方，它们没法塞进现有那五档（硬塞就要动白平衡），'
        '所以单独给它们一个档位。这一档<b>%d 格</b>（原生签名只有 %d 卷，填不满 4 格——剩下 %d 格留空，'
        '想用可以把「我的配方」里的自配方案填进去）。</div></details>'
    ) % (sigtxt, sigtxt, names, sigtxt, len(t['slots']), len(t['slots']), 4 - len(t['slots']))
    block = (
        '<div class="omode" id="o%s"><div class="omh omtog"><span class="omtag">%s</span>'
        '<span class="omtitle">%s</span><span class="omi"></span></div>'
        '<div class="ombody" style="display:none"><div class="ombar">'
        '<span class="omchip wb">白平衡 <b>%s</b></span>'
        '<span class="omchip md">曝光 <b>%s</b> %s</span>'
        '<span class="omchip ex">曝光补偿 <b>0 EV</b></span>'
        '<span class="omchip warm">保持暖色调 <b>关</b></span></div>'
        '<p class="omtheme">%s</p>%s<div class="omwhy">%s</div>'
        '<div class="omexp">%s</div>%s</div></div>'
    ) % (t['tag'], t['tag'], t['title'], sigtxt, t['md'], t['md_why'],
         t['theme'], omwb, t['why'], t['note'], ''.join(body))
    NEW_BLOCKS.append(block)
    LOG.append('  ✅ %s %s（%s，%d 格：%s）' % (t['tag'], t['title'], sigtxt, len(t['slots']), names))

# ------------------------------------------------------------------ 插到 #oC5 之后
print('\n=== 插进 paneB ===')
i = s.find('<div class="omode" id="oC5"')
assert i > 0, '找不到 #oC5'
j = s.find('<div class="omode" id="oC6"', i)
if j < 0:
    # 第一次跑：#oC1..oC5 是兄弟节点，整体包在一个 div 里，
    # 那个 div 的收尾就是 #opink 之前最近的一次 '</div></details>'。
    k = s.find('<details class="sec" id="opink"')
    assert k > i, '找不到 #opink（用来定位候选档容器结尾）'
    j = s.rfind('</div></details>', i, k)
assert j > i, '定位 #oC5 结尾失败'
if '<div class="omode" id="oC6"' in s:
    LOG.append('  · C6–C10 已存在，跳过插入')
else:
    s = s[:j] + ''.join(NEW_BLOCKS) + s[j:]
    LOG.append('  ✅ 5 个新候选档已插到 #oC5 之后（容器内、#opink 之前）')

# ------------------------------------------------------------------ modetabs
print('\n=== 同步 modetabs / 跳转条 / 页首说明 ===')
mt_old = re.search(r'(<div class="modetabs" id="modetabs">)(.*?)(</div>)', s, re.S)
assert mt_old, '找不到 modetabs'
add = ''.join('<button type="button" data-m="o%s">%s</button>' % (t['tag'], t['label'])
              for t in TIERS)
if 'data-m="oC6"' not in s:
    s = s[:mt_old.end(2)] + add + s[mt_old.end(2):]
    LOG.append('  ✅ modetabs +5 个按钮')

# 顶栏跳转条
if 'data-goto="oC6"' not in s:
    m = re.search(r'(<a href="#oC5" data-goto="oC5">[^<]*</a>)', s)
    assert m, '跳转条里找不到 C5'
    add2 = ''.join('<a href="#%s" data-goto="%s">%s</a>'
                   % ('o' + t['tag'], 'o' + t['tag'], t['label'].split(' ', 1)[1])
                   for t in TIERS)
    s = s[:m.end(1)] + add2 + s[m.end(1):]
    LOG.append('  ✅ 顶栏跳转条 +5 条')

# ------------------------------------------------------------------ 页首说明
old_sub = ('<p class="sub">5 个 C 档：4 档按肤色重排 ＋ 1 档胶片直出 · 18 个原站配方 ＋ 2 个自配'
           '（20/20 个 Color Profile 槽位，全满）· 外加 1 个挂在 MONO 档的黑白 · '
           '<b>20 个彩色槽位里只有 1 格动了白平衡</b></p>')
new_sub = ('<p class="sub"><b>相机只有 C1–C5 五个 C 档；下面有 10 个候选档，从里面挑 5 个写进去。</b>'
           'C1–C5 是原来的主题档（人像 / 街拍 / 风光 / 夜景 / 胶片）；'
           'C6–C10 是<b>按白平衡签名</b>补的候选档——同一个 C 档里 4 个 Color Profile 槽共享一组白平衡，'
           '所以同档配方的白平衡签名必须一致。<b>C6–C10 用的全是原生签名，一格没动。</b>'
           '另外 1 个黑白挂在 MONO 档上，不占 C 档槽位。</p>')
if old_sub in s:
    s = s.replace(old_sub, new_sub, 1)
    LOG.append('  ✅ 页首说明已改写成「10 个候选档，挑 5 个」')
else:
    LOG.append('  ⚠ 页首说明没匹配到（可能已改过）')

# ------------------------------------------------------------------ OPT / IDX / SC
print('\n=== 同步 __OM3OPT__ / IDX / 场景对比 ===')
OPT = blk('window.__OM3OPT__')
used = [x for t in TIERS for x in t['slots']]
for u in used:
    if u not in OPT:
        OPT.append(u)
LOG.append('  ✅ __OM3OPT__ %d → %d 条' % (len(OPT) - len(used), len(OPT)))

n_idx = 0
for t in TIERS:
    for n, slug in enumerate(t['slots'], 1):
        r = by[slug]
        h = 'o%s-%d' % (t['tag'], n)
        e = dict(h=h, n=r['n'], a=r['a'], sl='候选 %s · 槽 %d' % (t['tag'][1:], n),
                 t=None, g=None, v=None, f=None)
        # 借 IDX 里该配方已有条目的标签/适合/避开/一句话
        src = [x for x in IDX if x['h'] == 'r-' + slug]
        if src:
            for k in ('t', 'g', 'v', 'f'):
                e[k] = src[0].get(k)
        IDX = [x for x in IDX if x['h'] != h] + [e]
        n_idx += 1
LOG.append('  ✅ IDX 写入 %d 条 oC6–oC10 条目（现 %d 条）' % (n_idx, len(IDX)))

# 场景对比：把槽位映射重算（i → os）
slotmap = {}
for t in TIERS:
    for n, slug in enumerate(t['slots'], 1):
        slotmap[slug] = ('o%s-%d' % (t['tag'], n), '候选 %s · 槽 %d' % (t['tag'][1:], n))
SC = blk('window.__OM3SC__')
n_sc = 0
for sc in SC:
    for it in sc['items']:
        h = it.get('i') or ''
        if h.startswith('r-') and h[2:] in slotmap:
            sid, sl = slotmap[h[2:]]
            if it.get('os') != sid:
                it['os'] = sid
                it['osl'] = sl
                n_sc += 1
        elif it.get('os') and it['os'] not in []:
            pass
LOG.append('  ✅ 场景对比 %d 条的 os/osl 指向新候选档' % n_sc)
# 新配方「日常挂机」现在也该指向它所在的槽位
for sc in SC:
    for it in sc['items']:
        if it.get('i') == 'r-momo_everyday' and not it.get('os'):
            it['os'] = 'oC1-1'
            it['osl'] = 'C1 · 槽 1'
            LOG.append('  ✅ 「日常挂机」的场景对比按钮指向 C1 槽 1')

# ------------------------------------------------------------------ 写回
for key, obj in (('window.__OM3RECIPES__', REC), ('var IDX', IDX), ('window.__OM3OPT__', OPT),
                 ('window.__OM3SC__', SC)):
    i2 = s.find(key)
    p2 = s.index('=', i2) + 1
    while s[p2].isspace():
        p2 += 1
    _, e2 = D.raw_decode(s, p2)
    s = s[:p2] + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + s[e2:]

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n'.join(LOG))
print('\n写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))

# ------------------------------------------------------------------ 自检
print('\n=== 自检 ===')
S = io.open(P, encoding='utf-8').read()
tiers = re.findall(r'<div class="omode" id="(oC\d+)"', S)
slots = re.findall(r'<div class="oslot" id="(oC[^"]+)"', S)
print('候选档 %d 个：%s' % (len(tiers), tiers))
print('槽位 %d 个：%s' % (len(slots), slots))
print('modetabs 按钮', len(re.findall(r'<button type="button" data-m="oC\d+">', S)))
ids = set(re.findall(r'\bid="([^"]+)"', S))
print('死锚点：', sorted(l for l in set(re.findall(r'href="#([^"]+)"', S)) if l not in ids and "'" not in l) or '无')
print('IDX oC 条目：', len([x for x in blk('var IDX') if x['h'].startswith('oC')]))
