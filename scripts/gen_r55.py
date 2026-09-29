# -*- coding: utf-8 -*-
"""第 55 轮生成器：把站点现存的 19 条配方补成卡片（+ REC / IDX / SC / 计数）。幂等。

来源：站点 sitemap 有、app 没有卡片的 19 条（已排除旧版 ian-will_kinda-portra）；
     其中 18 条数据在 all_recipes.json 里，tom-jackson_porta-400-print 由 fetch_r55.py 现抓。

改 6 处：
  ① #pool「更多配方」：按白平衡签名建组/入组，19 张卡 + 重算每组的「· N 个」
  ② window.__OM3RECIPES__  +19（追加在末尾）
  ③ var IDX                +19（搜索索引；含 porta → Portra 系的搜索别名）
  ④ window.__OM3SC__       +条目（关键词匹配，保证每条至少进 1 个场景）
  ⑤ 首页计数文案           「全站 79 条配方」→「98 条」
  ⑥ 由 gen_phototags.py 重建 __OM3PHOTOS__ / __OM3PHOTOTAGS__（在最后调用）

⚠ 图片没下全也能跑（只放本地真有的图）；图片下完后再跑一次即可，md5 会变。
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from om3_profile import con_word, dir_word, gen6, profile, sat_word, wbtxt            # noqa: E402
from recipe_wheel import vals_line, wheel_svg                                          # noqa: E402
import gen_phototags                                                                     # noqa: E402

BASE = os.path.join(ROOT, 'app', 'base.html')
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
CARD_CMP = ['marathon', 'peace-memorial']       # 卡片上放的 2 张站点统一对比图（与现有 58 张一致）
CMP_LABEL = {'marathon': '人群 / 暖光石拱', 'peace-memorial': '中性白 / 蓝天绿树'}
CH = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫'
NOTE = '按色轮（12 色轴）、色调曲线、白平衡偏移**从参数直接推导**，不是作者自述'
EXIF_TXT = ('样片来源 om-recipes.com：<b>对比场景</b>为本站统一拍摄（6 个场景可在「场景对比」页签'
            '按场景横向比较），<b>作者样片</b>为作者实拍，EXIF 见图注。')
TRANS_NOTE = '<span style="opacity:.7">（中文为本手册翻译，英文原文见下）</span>'

# 站点原文的中译（本手册翻译，不是作者中文原话 → 折页里注明）
DESC_ZH = {
    'kaleigh-whitaker_bluegill-teal': '非常强调青绿和橙的搭配。拍夜晚街头会很有意思。',
    'tom-jackson_porta-400-print': '模拟柯达 Portra 400 印在 Endura 相纸上的效果；参数依据柯达数据表推导。',
    'ali_o_keefe_omtc_chrome': '感觉：反转片味道——冲击力强、边缘干净、暗部有戏。<br>适合：城市街景、黄金时刻、形状强烈的画面。'
                               '<br>避开：阴天，或者光比极大又不好好测光的场合。<br>💡 稍微欠曝一点、盯着直方图拍，这条很容易把高光冲爆。',
    'paul_clark_paul_clark_recipe': '这条配色把暖色和冷色都提上来、同时把绿和品红收下去，让互补色更跳。反差调软、暗部抬起、高光压低、锐度降低，'
                                    '整体平衡、自然，接近现场的样子。',
    'chris-brogan_a-bit-more-vivid': '我日常最常用的一条。',
    'kitty-marie_red-soda-pop': '这条配色就是我的「红汽水」。整体调暖，让红色「爆」出来，同时把黄和绿稍稍压一点；画面也变柔，多一点梦幻感。',
    'terry_mclaughlin_terry_mclaughlin_recipe': '这条是按我自己的风格做的：蓝去饱和、中间调偏暖，橙红一跳出来。整体用一条淡淡的胶片曲线压住，'
                                                '收在那个怀旧、电影感的味道上，适合黄金时刻。',
    'stella-toul_carte-postal': '颜色非常饱和：海蓝又深又亮，绿是暖的、很浓；反差明显，整体很「冲」——几乎像一张明信片。',
    'jerred_z_eternal_sunshine': '它把颜色整体挪了一挪，同时把画面变柔：高饱和 + 低反差。<br>我觉得这条在城里最出彩，在花园里也很好'
                                 '（不过值得试——不是所有颜色都吃得消）。<br>靠调色做出独特色调这件事，从彩色胶片发明那天就开始了；'
                                 '我喜欢它们那种柔、梦幻、发光的味道。',
    'luis-chavez_dirty-pop': 'Dirty Pop：名字来自 NSYNC 的一首歌。颜色自然但有劲，暗部深、高光轻轻抬起；绿和黄带一点辉光，蓝稍暗一点——'
                             '天空更厚实，肤色直出就干净。',
    'emily_m4nerds_m4nerds': '出来的画面更风格化、偏暖，户外用效果好。',
    'dave_herring_vibrant_chrome': 'Dave Herring 分享的这条参数，调出一条强调红色的鲜明 Chrome 味。基于相机 COLOR 3 默认值，'
                                   '但把绿的饱和度降下来，并用 5200K 自定义白平衡（日光下 B+1、M+1）。',
    'burak-yilmaz_portside-chrome': '我很喜欢老胶片那种味道。这条把荧光灯白平衡和一点品红偏移配在一起，曲线抬起暗部、压下中间调和高光；'
                                    '12 个颜色都只给低强度，画面更收敛、更复古。',
    'burak-yilmaz_asteroid-city': '一条电影感配色，灵感来自《小行星城》那个精心搭出来的世界——日常场景被变成安静、风格化的画面。',
}


# ================================================================ 数据
def load_by():
    snap = json.load(io.open(SNAP, encoding='utf-8'))['results']
    by = {r['slug']: r for r in snap}
    by[json.load(io.open(EXTRA, encoding='utf-8'))['slug']] = json.load(io.open(EXTRA, encoding='utf-8'))
    return by


AXES = ('yellow', 'orange', 'orangeRed', 'red', 'magenta', 'violet',
        'blue', 'blueCyan', 'cyan', 'greenCyan', 'green', 'yellowGreen')


def mkr(r):
    """站点记录 → __OM3RECIPES__ 条目（字段名与现有 79 条逐一对齐）"""
    return {
        'n': r['recipeName'], 'a': r['authorName'], 'slug': r['slug'], 't': r['type'],
        'v': [int(r.get(k) or 0) for k in AXES],
        'hi': int(r.get('highlights') or 0), 'sh': int(r.get('shadows') or 0),
        'mid': int(r.get('midtones') or 0), 'con': int(r.get('contrast') or 0),
        'shp': int(r.get('sharpness') or 0), 'eff': int(r.get('shadingEffect') or 0),
        'wb': r.get('whiteBalance2') or '', 'wbt': r.get('whiteBalanceTemperature'),
        'wba': int(r.get('whiteBalanceAmberOffset') or 0), 'wbg': int(r.get('whiteBalanceGreenOffset') or 0),
        'monoColor': r.get('monochromeColor') or '', 'monoStr': r.get('monochromeColorStrength'),
        'grain': r.get('filmGrain') or '', 'hue': r.get('filmHue') or ''}


def hero_map(by):
    """主图表（与 gen_r54 同一口径）：原站 isPrimary 的样片 → 没有就样片第一张；文件不在盘上就不算"""
    hm = {}
    for slug, r in by.items():
        ss = r.get('sampleImages') or []
        pick = ''
        for i, x in enumerate(ss):
            if x.get('isPrimary'):
                pick = '%s__s%02d.jpg' % (slug, i + 1)
                break
        if not pick and ss:
            pick = '%s__s%02d.jpg' % (slug, 1)
        if pick and pick in have:
            hm[slug] = pick
    return hm


def sig_of(rec):
    return wbtxt(rec['wba'], rec['wbg'])


def group_id(sig):
    return 'pool-' + sig.replace('+', '').replace(' ', '')


def exif_txt(s):
    try:
        if not s.get('validExif'):
            return ''
        return '%s f/%s %ss ISO %s' % (s['focalLength'], s['aperture'], s['shutterSpeed'], s['iso'])
    except Exception:
        return ''


def figures(slug, r, have):
    """作者主图 → 其余作者样片 → 2 张对比场景（只保留本地真有的）"""
    out = []
    smp = r.get('sampleImages') or []
    hero = next((i for i, s in enumerate(smp) if s.get('isPrimary')), 0 if smp else None)
    order = ([hero] if hero is not None else []) + [i for i in range(len(smp)) if i != hero]
    for i in order:
        fn = '%s__s%02d.jpg' % (slug, i + 1)
        if fn not in have:
            continue
        ex = exif_txt(smp[i])
        cap = ('作者主图 %s' % CH[i]) if i == hero else ('作者样片 %s' % CH[i])
        out.append((fn, cap + (('　·　' + ex) if ex else ''), i == hero))
    for sc in CARD_CMP:
        fn = '%s__cmp__%s.jpg' % (slug, sc)
        if fn in have:
            out.append((fn, '对比场景 · %s（%s）' % (sc, CMP_LABEL[sc]), False))
    return out


def html6(g, summary, with_source=True):
    def row(mk, mv, cls=''):
        mv = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', mv)
        return ('<div class="row"><span class="mk">%s</span><span class="mv%s">%s</span></div>'
                % (mk, (' ' + cls) if cls else '', mv))
    body = (row('画面感觉', g['feel']) + row('色彩重点', g['key']) + row('影调', g['tone'])
            + row('适合', g['good'], 'good') + row('避开', g['bad'], 'avoid') + row('提示', g['tip'], 'tip'))
    if with_source:
        body += row('来源', NOTE)
    return ('<details class="fold fgen"><summary>%s <span style="font-weight:400;opacity:.7">'
            '（展开看全 6 项）</span></summary><div class="foldbody">%s</div></details>') % (summary, body)


def card_html(r, rec, have):
    slug = rec['slug']
    sig = sig_of(rec)
    p = profile(rec)
    figs = figures(slug, r, have)
    shots = '<div class="shots">' + ''.join(
        '<figure%s><img loading="lazy" data-im="%s"><figcaption>%s</figcaption></figure>'
        % (' class="hero"' if hero else '', fn, cap)
        for fn, cap, hero in figs) + '</div>'
    summ = '参数解读 · %s / %s / %s' % (sat_word(p), dir_word(p), con_word(p))
    parts = [('<div class="card" id="r-%s"><div class="chd"><span class="cname">%s</span>'
              '<span class="slot">%s</span><span class="cauth">%s</span></div>'
              '<div class="tags"><span>%s</span><span>%s</span><span>%s</span></div>'
              '<div class="cbody"><div class="cleft">%s%s<div class="vlegend">1黄 → 12嫩黄绿 · 顺时针</div></div>'
              '<div class="cright">%s')
             % (slug, rec['n'], sig, rec['a'], sat_word(p), dir_word(p), con_word(p),
                wheel_svg(rec['v']), vals_line(rec['v']), shots),
             html6(gen6(rec), summ)]
    desc = (r.get('description') or '').strip()
    if desc:
        zh = DESC_ZH.get(slug, '')
        if zh:
            parts.append('<details class="fold fnote"><summary>原文 · 作者自述 <span style="font-weight:400;'
                         'opacity:.7">（点击展开）</span></summary><div class="foldbody">%s<br><br>%s</div></details>'
                         % (zh, TRANS_NOTE))
        parts.append('<details class="en"><summary>English original</summary><div>%s</div></details>'
                     % desc.replace('\r\n', '<br>').replace('\n', '<br>'))
    parts.append('<div class="params">色调曲线 <i>Sh %d / Mid %d / Hi %d</i>'
                 '<span class="psep">　｜　</span>阴影补偿 <i>%d</i> · 锐度 <i>%d</i> · 对比 <i>%d</i> · '
                 '曝光 <i>%s</i></div><div class="exif">%s</div></div></div></div>'
                 % (rec['sh'], rec['mid'], rec['hi'], rec['eff'], rec['shp'], rec['con'],
                    ('%g' % (int(r.get('exposureCompensation') or 0) / 10.0)), EXIF_TXT))
    return ''.join(parts)


def idx_entry(r, rec):
    g = gen6(rec)
    sl = 'A0 G0' if rec['t'] == 'MONO' else sig_of(rec)
    return {'h': 'r-' + rec['slug'], 'n': rec['n'], 'a': rec['a'], 'sl': sl,
            't': '%s · %s · %s' % (sat_word(profile(rec)), dir_word(profile(rec)), con_word(profile(rec))),
            'g': g['good'], 'v': g['bad'], 'f': g['feel']}


# ================================================================ HTML/JSON 手术
def tag_block_end(s, start, tag='details'):
    """返回从 start 处开始的 <tag> 元素结束后的下标（花括号/标签配对）"""
    pat = re.compile(r'<%s\b|</%s>' % (tag, tag))
    depth, k = 0, start
    while True:
        m = pat.search(s, k)
        if not m:
            raise ValueError('没配对：%s @ %d' % (tag, start))
        depth += 1 if m.group(0).startswith('<' + tag) else -1
        k = m.end()
        if depth <= 0:
            return k


def cut_card(s, slug):
    """从文本里删掉 r-<slug> 这张卡，返回 (新文本, 是否删了)

    ⚠ 插入时我在卡尾补了一个换行（和文件里原有分隔一致）→ 删除时必须一起吃掉，
    否则每跑一遍都会多留一个空行（幂等性就是这么破的，第一版少了这一行）。"""
    i = s.find('<div class="card" id="r-%s">' % slug)
    if i < 0:
        return s, False
    j = tag_block_end(s, i, 'div')
    if s[j:j + 1] == chr(10):
        j += 1
    return s[:i] + s[j:], True


def json_span(s, marker):
    """marker 之后那段 JSON（数组或对象）的起止下标 —— 用 raw_decode，字符串里的括号不会误判"""
    i = s.index(marker)
    j = i + len(marker)
    while j < len(s) and s[j] in ' \n':
        j += 1
    _, k = json.JSONDecoder().raw_decode(s, j)
    return j, k


def row_text(t):
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t).replace('&', '&amp;')


GARBAGE = ('把 无 推上去', '具体到画面：。')
GARBAGE_START = ('色环把 无 推上去', '12 个色轴全部为 0')


def fix_dd(dd, new_key):
    """只把 dd 里那句旧 key 换成新的 —— 前面的「图按画面自动归类…｜ feel」一个字节不碰"""
    for g in GARBAGE_START:
        i = dd.find(g)
        if i >= 0:
            return dd[:i] + new_key
    return dd


def fix_fd(fd, new_key):
    """只换 fd 里「色彩重点」那一行的内容 —— 别的行（含第 53 轮手写的「暖光现场」）保持原样"""
    return re.sub(r'(<span class="mk">色彩重点</span><span class="mv">).*?(</span></div>)',
                  lambda m: m.group(1) + row_text(new_key) + m.group(2),
                  fd, count=1, flags=re.S)


def sync_sc_blob(s, recs, have):
    """把 19 条新配方补进「场景对比 → 实拍对比」的 6 个统一场景（window.SC）。

    原来这张表是站点那批作者的手工集合（50/49/50/49/49/42 条）。新配方同样有这 6 个统一场景的
    对比图（本轮已下），不补的话会出现「按场景找配方里有它、实拍对比里没它」。
    条目字段按现有条目逐一对齐：d=一句话感觉 / dd=感觉+色彩重点 / fs / fd / ps / pb。"""
    j, k = json_span(s, 'window.SC = ')
    blob = json.loads(s[j:k])
    n = 0
    for sc in blob:
        have_slugs = {it.get('i') for it in sc['items']}
        for slug in NEW:
            if ('r-' + slug) in have_slugs or slug not in recs:
                continue
            f = '%s__cmp__%s.jpg' % (slug, sc['k'])
            if f not in have:
                continue
            r = recs[slug]
            g = gen6(r)
            p = profile(r)
            t3 = '%s · %s · %s' % (sat_word(p), dir_word(p), con_word(p))
            sc['items'].append({
                'f': f, 'n': r['n'], 'a': r['a'], 't': t3, 'd': g['feel'],
                'i': 'r-' + slug, 'sl': sig_of(r), 'dd': g['feel'] + g['key'],
                'fs': '参数解读 · %s' % t3,
                'fd': html6(g, '参数解读（按参数推导）', with_source=False),
                'ps': '调整参数：色调曲线 Sh %d / Mid %d / Hi %d ｜ 阴影补偿 %d'
                      % (r['sh'], r['mid'], r['hi'], r['eff']),
                'pb': ''})
            n += 1
    if n:
        j, k = json_span(s, 'window.SC = ')       # 写完重算下标
        s = s[:j] + dump(blob) + s[k:]
    return s, n


def sync_toc(s):
    """把侧边目录里「更多配方（按白平衡偏移）」那一段按 #pool 的真实内容重建（幂等）。

    第 55 轮往 #pool 里加了 8 个签名组 + 19 张卡，但侧边目录是**手写的** →
    不重建就会出现「页面里有、目录里点不到」。这里以 #pool 为唯一事实源。"""
    a = s.index('<details class="sec" id="pool">')
    b = s.index('id="paneB"')
    pool = s[a:b]
    pool_end = pool.rindex('</div></details>')
    heads = [(m.group(1), m.group(2).strip(), m.end())
             for m in re.finditer(r'<h3 id="(pool-[^"]+)">([^&<]*)', pool)]
    out, n_card = [], 0
    for i, (gid, lbl, hend) in enumerate(heads):
        blk_end = heads[i + 1][2] if i + 1 < len(heads) else pool_end
        blk = pool[hend:blk_end]
        cards = re.findall(r'<div class="card" id="r-([^"]+)">.*?<span class="cname">([^<]*)</span>',
                           blk, re.S)
        out.append('<a class="lv2" href="#%s">%s · %d 个</a>\n' % (gid, lbl, len(cards)))
        # 与页面原样一致：每组最多明链 8 张，其余 class="lv3 more" hidden，再挂一个展开按钮
        for slug, name in cards[:8]:
            out.append('<a class="lv3" href="#r-%s">%s</a>\n' % (slug, name))
        for slug, name in cards[8:]:
            out.append('<a class="lv3 more" href="#r-%s" hidden>%s</a>\n' % (slug, name))
        if len(cards) > 8:
            out.append('<button class="tocmore" data-n="%d">▾ 展开其余 %d 个</button>\n'
                       % (len(cards), len(cards) - 8))
        n_card += len(cards)
    # 目录里这一段：<div class="tg"><div class="tgh">更多配方（按白平衡偏移）</div> … </div>
    marker = '更多配方（按白平衡偏移）</div>'
    i = s.index(marker) + len(marker)
    j = s.index('</div>', i)
    return s[:i] + '\n' + ''.join(out) + s[j:], len(heads), n_card


def refresh_sc_blob(s):
    """`window.SC`（实拍对比 6 个统一场景）里存着一份**预渲染好的** fold HTML，
    gen6 那两句退化文案在这里也有 50 条（×2 句 = 100 处）。同一批机器句子，一起修。"""
    j, k = json_span(s, 'window.SC = ')
    blob = json.loads(s[j:k])
    jj, kk = json_span(s, 'window.__OM3RECIPES__=')
    RECb = {r['slug']: r for r in json.loads(s[jj:kk])}
    n = 0
    for sc in blob:
        for it in sc['items']:
            r = RECb.get((it.get('i') or '')[2:])
            if not r:
                continue
            if not any(x in (it.get('dd') or '') + (it.get('fd') or '') for x in GARBAGE):
                continue
            g = gen6(r)
            it['dd'] = fix_dd(it.get('dd') or '', g['key'])
            it['fd'] = fix_fd(it.get('fd') or '', g['key'])
            n += 1
    if n:
        j, k = json_span(s, 'window.SC = ')          # 重算下标再写
        s = s[:j] + dump(blob) + s[k:]
    return s, n


def refresh_stale_key(s, REC, SC):
    """顺带修：gen6 原来在两条退化情况下（12 轴全 0 / 只有往下的轴）会生成
    「色环把 无 推上去……具体到画面：。」这种机器句子，早年已写进 17 张卡和若干场景条目。
    本函数把这些**已经坏掉的句子**按新 gen6 逐条重写（只动含垃圾片段的行，别的字一个不碰）。"""
    by = {r['slug']: r for r in REC}
    n_card = 0
    for m in list(re.finditer(r'<div class="card" id="r-([^"]+)">', s))[::-1]:
        r = by.get(m.group(1))
        if not r:
            continue
        end = tag_block_end(s, m.start(), 'div')
        blk = s[m.start():end]
        row = re.search(r'(<div class="row"><span class="mk">色彩重点</span><span class="mv">)(.*?)'
                        r'(</span></div>)', blk, re.S)
        if not row or not any(x in row.group(2) for x in GARBAGE):
            continue
        s = s[:m.start()] + blk[:row.start(2)] + row_text(gen6(r)['key']) + blk[row.end(2):] + s[end:]
        n_card += 1
    n_sc = 0
    for sc in SC:
        for it in sc['items']:
            r = by.get((it.get('i') or '')[2:])
            if not r:
                continue
            g = gen6(r)
            if any(x in (it.get('dd') or '') for x in GARBAGE):
                it['dd'] = fix_dd(it['dd'], g['key'])
                n_sc += 1
            if any(x in (it.get('fd') or '') for x in GARBAGE):
                it['fd'] = fix_fd(it['fd'], g['key'])
    return s, n_card, n_sc


def dump(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


def main():
    global have
    s = io.open(BASE, encoding='utf-8').read()
    have = set(os.listdir(IMG))
    by = load_by()

    # 原 REC（要在动 s 之前先存一份：其中 18 条新配方本来就已经在 REC 里了，
    # 必须**原样保留它们的记录**，只补 porta 那一条 → 否则旧条目会被重建得不一样）
    j0, k0 = json_span(s, 'window.__OM3RECIPES__=')
    REC0 = {x['slug']: x for x in json.loads(s[j0:k0])}

    # ---------- 0) 幂等：先删掉本轮的卡与索引条目 ----------
    removed = 0
    for slug in NEW:
        s, ok = cut_card(s, slug)
        removed += 1 if ok else 0
    # 清理空掉的 pool 组（上次跑留下的）+ 重算计数之前先把没有卡片的 <h3> 删掉
    for m in list(re.finditer(r'<h3 id="pool-[^"]+">.*?</h3>',
                              s[s.index('<details class="sec" id="pool">'):s.index('id="paneB"')], re.S))[::-1]:
        a = s.index('<details class="sec" id="pool">')
        b = s.index('id="paneB"')
        h3_start, h3_end = a + m.start(), a + m.end()
        nxt = re.compile(r'<h3 id="pool-').search(s, h3_end)
        blk_end = nxt.start() if (nxt and nxt.start() < b) else s.rindex('</div></details>', h3_end, b)
        if '<div class="card"' not in s[h3_end:blk_end]:
            s = s[:h3_start] + s[blk_end:]

    # ---------- 1) REC / IDX 里也先删掉旧条目 ----------
    for marker, keyname in (('window.__OM3RECIPES__=', 'slug'), ('var IDX=', 'h')):
        j, k = json_span(s, marker)
        arr = json.loads(s[j:k])
        if keyname == 'slug':
            arr = [x for x in arr if x.get('slug') not in NEW]
        else:
            arr = [x for x in arr if x.get('h') not in ('r-' + x2 for x2 in NEW)]
        s = s[:j] + dump(arr) + s[k:]
    # SC 里也删掉旧条目
    j, k = json_span(s, 'window.__OM3SC__ =')
    SC = json.loads(s[j:k])
    for sc in SC:
        sc['items'] = [it for it in sc['items'] if it.get('i') not in ('r-' + x for x in NEW)]

    # ---------- 2) 生成 19 张卡 ----------
    recs, cards = {}, {}
    for slug in NEW:
        r = by.get(slug)
        if not r:
            print('   ⚠ 没有数据：%s' % slug)
            continue
        rec = REC0.get(slug) or mkr(r)          # 已有的原样沿用，只有 porta 是新造的
        recs[slug] = rec
        cards[slug] = card_html(r, rec, have)

    # 按签名分组，组内按名字排序
    groups = {}
    for slug in NEW:
        if slug in recs:
            groups.setdefault(sig_of(recs[slug]), []).append(slug)
    for sig in groups:
        groups[sig].sort(key=lambda x: recs[x]['n'].lower())

    new_groups = []
    for sig in sorted(groups):
        gid = group_id(sig)
        head = '<h3 id="%s">偏移 %s &nbsp;<span style="color:#7ed3bd;font-size:12px"> · %d 个</span></h3>\n' % (
            gid, sig.replace('+', ''), len(groups[sig]))
        body = ''.join(cards[x] for x in groups[sig])
        # ⚠ 每轮都要重新定位：上一轮插入已经改了长度，a/b/ins_default 全会过期
        a = s.index('<details class="sec" id="pool">')
        b = s.index('id="paneB"')
        ins_default = s.rindex('</div></details>', a, b)      # pool 段自己的收尾
        m = re.search(r'<h3 id="%s">.*?</h3>' % re.escape(gid), s[a:b], re.S)
        if m:
            # 已有该组 → 追加到组尾
            h3_end = a + m.end()
            nxt = re.compile(r'<h3 id="pool-').search(s, h3_end)
            pos = nxt.start() if (nxt and nxt.start() < b) else ins_default
            s = s[:pos] + body + '\n' + s[pos:]
        else:
            new_groups.append(head + body + '\n')
    if new_groups:
        a = s.index('<details class="sec" id="pool">')
        b = s.index('id="paneB"')
        ins_default = s.rindex('</div></details>', a, b)
        s = s[:ins_default] + ''.join(new_groups) + s[ins_default:]

    # 重算 #pool 每组的「· N 个」
    fixed = 0
    for m in list(re.finditer(r'(<h3 id="pool-[^"]+">)(.*?)(</h3>)',
                              s[s.index('<details class="sec" id="pool">'):s.index('id="paneB"')], re.S))[::-1]:
        a = s.index('<details class="sec" id="pool">')
        b = s.index('id="paneB"')
        h3_start, h3_end = a + m.start(), a + m.end()
        nxt = re.compile(r'<h3 id="pool-').search(s, h3_end)
        blk_end = nxt.start() if (nxt and nxt.start() < b) else s.rindex('</div></details>', h3_end, b)
        n = s[h3_end:blk_end].count('<div class="card"')
        old = m.group(0)
        new = re.sub(r'· \d+ 个', '· %d 个' % n, old, count=1)
        if new != old:
            s = s[:h3_start] + new + s[h3_end:]
            fixed += 1

    # ---------- 3) REC 追加 ----------
    j, k = json_span(s, 'window.__OM3RECIPES__=')
    REC = json.loads(s[j:k])
    REC += [recs[x] for x in NEW if x in recs]
    s = s[:j] + dump(REC) + s[k:]

    # ---------- 4) IDX 追加（别名：porta 也能搜到 Portra 系） ----------
    j, k = json_span(s, 'var IDX=')
    IDX = json.loads(s[j:k])
    for slug in NEW:
        if slug in by:
            IDX.append(idx_entry(by[slug], recs[slug]))
    # 搜索别名：站点自己把那条拼成 Porta —— 给 Portra 系加个别名标签
    for _it in IDX:
        pass          # 别名改走页面现成的 SYN 词表（见下面的 4b），不再往标签文案里塞词
    s = s[:j] + dump(IDX) + s[k:]

    # ---------- 4b) 搜索别名：站点把招牌那条拼成「Porta 400 Print」，按站点拼法搜 "porta" 会一无所获 ----------
    if "'porta':" not in s:
        anchor = 'var SYN={\n'
        assert anchor in s, 'SYN 表没找到'
        s = s.replace(anchor, anchor + "  'porta':['portra'],        // 站点自己把 Portra 拼成了 Porta（Porta 400 Print）\n", 1)

    # ---------- 5) SC 用第 0 步里**已经剪掉本轮旧条目**的那份（⚠ 别在这儿重读，会把剪掉的又读回来 → 重复条目）
    j, k = json_span(s, 'window.__OM3SC__ =')
    s = s[:j] + dump(SC) + s[k:]
    s, n_fixsc2 = refresh_sc_blob(s)              # ← 实拍对比那份预渲染副本，同一批句子
    s = s.replace('全站 79 条配方', '全站 %d 条配方' % len(REC))      # 计数文案
    io.open(BASE, 'w', encoding='utf-8', newline='').write(s)
    gen_phototags.HERO = hero_map(by)              # ← 关键：不带这张表，第 54 轮的主图顺序会被打回字典序
    gen_phototags.main()
    s = io.open(BASE, encoding='utf-8').read()
    j, k = json_span(s, 'window.__OM3SCENES__ =')
    SCENES = json.loads(s[j:k])
    j, k = json_span(s, 'window.__OM3SC__ =')
    SC = json.loads(s[j:k])
    jj, kk = json_span(s, 'window.__OM3PHOTOS__ = ')
    PH = json.loads(s[jj:kk])
    jj2, kk2 = json_span(s, 'window.__OM3PHOTOTAGS__ = ')
    PT = json.loads(s[jj2:kk2])
    print('F. __OM3PHOTOS__ = %d 条配方；本轮 19 条里盘上已有图 %d 张'
          % (len(PH), sum(len(PH.get(x) or []) for x in NEW)))
    used = {}
    for sc in SC:
        for it in sc['items']:
            used.setdefault(sc['k'], set()).add(it.get('f'))
    # 这 7 个场景是第 51~53 轮人工重建/按打法挑的（还带手写提示行）→ 新配方**不进去**：
    # 机器匹配会稀释它们，也会撞坏 dv_r51/52/53 的既有断言（这条边界是故意写死的）
    CURATED = {'雾 / 阴天 / 雨天', '雪景', '森林绿意', '夜景霓虹', '暖光 / 灯光下',
               '日落晚霞', '逆光大光比'}
    # 条件类场景的参数判定（与第 50/51 轮同一口径，dv_r51 会盯着这条）
    COND = {'雾 / 阴天 / 雨天': lambda p, d: sat_word(p) in ('清淡', '寡淡'),
            '暖光 / 灯光下': lambda p, d: d >= 8,
            '雪景': lambda p, d: d > 4,
            '日落晚霞': lambda p, d: d < -4}
    scene_of, kwcnt = {}, {}
    for sc in SC:
        if sc['label'] in CURATED:
            continue
        kw = next((x.get('kw') or [] for x in SCENES if x['k'] == sc['k']), [])
        for slug in NEW:
            if slug not in recs:
                continue
            g = gen6(recs[slug])
            p = profile(recs[slug])
            hit_kw = [x for x in kw if x and x in g['good']]
            if not hit_kw:
                continue
            kwcnt[slug] = max(kwcnt.get(slug, 0), len(hit_kw))
            cond = COND.get(sc['label'])
            if cond and cond(p, p['eff_w'] - p['eff_c']):
                continue                       # 参数不合适 → 不放这个场景（第 51 轮口径）
            scene_of.setdefault(slug, []).append(sc)
    # 兜底：一条都没落进去的，退回"匹配词最多"的那个场景（但避开条件类场景）
    fallback = []
    for slug in NEW:
        if slug in scene_of or slug not in recs:
            continue
        g = gen6(recs[slug])
        p = profile(recs[slug])
        cand = []
        for sc in SC:
            if sc['label'] in COND or sc['label'] in CURATED:
                continue
            kw = next((x.get('kw') or [] for x in SCENES if x['k'] == sc['k']), [])
            cand.append((len([x for x in kw if x and x in g['good']]), sc))
        cand.sort(key=lambda t: -t[0])
        if cand:
            scene_of[slug] = [cand[0][1]]
            fallback.append((slug, cand[0][1]['label'], cand[0][0]))
    for sc in SC:
        first = sc['items'][0] if sc['items'] else None
        for slug in NEW:
            if slug not in scene_of or sc not in scene_of[slug]:
                continue
            ph = list(PH.get(slug) or [])
            want = PT.get(ph[0]) if ph else []
            f = ''
            for cand in ph:                        # 对题优先 + 作者优先（第 54 轮口径）
                if cand in used.get(sc['k'], set()):
                    continue
                tg = PT.get(cand) or []
                if any(t in tg for t in (want or [])):
                    f = cand
                    break
            if not f:
                f = next((c for c in ph if c not in used.get(sc['k'], set())), ph[0] if ph else '')
            if not f:
                continue
            used.setdefault(sc['k'], set()).add(f)
            g = gen6(recs[slug])
            tags = ' / '.join(PT.get(f) or [])
            pre = '图按画面自动归类：%s（自动判断，偶尔会看错）' % tags
            t3 = '%s · %s · %s' % (sat_word(profile(recs[slug])), dir_word(profile(recs[slug])),
                                   con_word(profile(recs[slug])))
            it = {'i': 'r-' + slug, 'n': recs[slug]['n'], 'a': recs[slug]['a'], 'sl': sig_of(recs[slug]),
                  't': t3, 'f': f, 'd': pre, 'dd': pre + '｜ ' + g['feel'] + g['key'],
                  'fs': '参数解读 · %s' % t3, 'fd': html6(g, '参数解读（按参数推导）', with_source=False),
                  'ps': '调整参数：色调曲线 Sh %d / Mid %d / Hi %d ｜ 阴影补偿 %d'
                        % (recs[slug]['sh'], recs[slug]['mid'], recs[slug]['hi'], recs[slug]['eff']),
                  'os': '', 'osl': ''}
            sc['items'].append(it)
    s, n_fixcard, n_fixsc = refresh_stale_key(s, REC, SC)
    j, k = json_span(s, 'window.__OM3SC__ =')     # ⚠ 上面改过卡片文字，SC 的下标必须重算
    s = s[:j] + dump(SC) + s[k:]
    no_scene = [x for x in NEW if x not in scene_of]
    print('G. 顺带修掉 gen6 的两处退化文案：「把 无 推上去」「具体到画面：。」'
          '→ 卡片 %d 张、按场景挑 %d 处、实拍对比（window.SC）%d 条'
          % (n_fixcard, n_fixsc, n_fixsc2))

    s, n_toc_grp, n_toc_card = sync_toc(s)         # 侧边目录跟着 #pool 重建（手写的会过期）
    s, n_sc2 = sync_sc_blob(s, recs, have)         # 实拍对比 6 个统一场景也把这 19 条补进去
    n_open, n_close = len(re.findall(r'<div\b', s)), s.count('</div>')
    assert n_open == n_close, '结构坏了：<div %d 个、</div> %d 个（多半是插入/删除下标漂了）' % (n_open, n_close)
    io.open(BASE, 'w', encoding='utf-8', newline='').write(s)
    print('H. 侧边目录已重建：%d 个签名组 / %d 张卡的 lv2+lv3 链接' % (n_toc_grp, n_toc_card))
    print('I. 实拍对比（window.SC）补进 %d 条（6 个统一场景 × 有图的新配方）' % n_sc2)
    print('A. #pool 插入 %d 张卡（新建 %d 个签名组，重算计数 %d 组；幂等删掉旧卡 %d 张）'
          % (sum(len(v) for v in groups.values()), len(new_groups), fixed, removed))
    print('B. __OM3RECIPES__ = %d 条（+%d）' % (len(REC), len(recs)))
    print('C. IDX = %d 条（+%d）；SYN 里已加 porta→portra 别名' % (len(IDX), len(recs)))
    got = {}
    for sc in SC:
        for it in sc['items']:
            got.setdefault((it.get('i') or '')[2:], 0)
            got[(it.get('i') or '')[2:]] += 1
    miss = [x for x in NEW if not got.get(x)]
    print('D. 场景：19 条里 %d 条已真的进了场景（共 %d 个条目）；还没进的 %d 条（图没到齐）%s'
          % (19 - len(miss), sum(got.get(x, 0) for x in NEW), len(miss), miss or ''))
    if fallback:
        print('   兜底放进题材类场景的：%s' % '；'.join('%s→%s(词%d)' % x for x in fallback))
    print('E. 计数文案：全站 %d 条配方' % len(REC))
    return 0


if __name__ == '__main__':
    sys.exit(main())
