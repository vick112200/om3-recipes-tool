# -*- coding: utf-8 -*-
"""档位推荐「槽位」渲染器（第 44 轮抽出，和 recipe_wheel.py 配套）。

一个 .oslot 的全部内容都能从已有数据重建：
  · 色轮 SVG      ← __OM3RECIPES__[].v            （recipe_wheel.wheel_svg）
  · osvals 12 格  ← 同上
  · 样片 figure   ← 配方卡片里已有的 <figure>（对比场景优先，作者样片最多 3 张）
  · 原文 / English / 补充6项 ← 配方卡片里的 <details> 整块**原样搬过来**
  · 一句话风格    ← IDX[].f
  · 参数行        ← 卡片 .params（色调曲线 / 锐度 / 对比 / 阴影补偿 / 曝光）
  · 白平衡行      ← 配方签名 vs 档位签名（算位移）
"""
import re

import recipe_wheel as W

CHCOLOR = W.CHCOLOR
CHNAME = W.CHNAME


def sgn0(v):
    """槽位里的数值写法：0 写作 0，正数带 +。"""
    return ('+%d' % v) if v > 0 else str(v)


def wheel_block(v):
    return '<div class="oswheel">%s</div>' % W.wheel_svg(v)


def vals_block(v):
    h = ['<div class="osvals">']
    for i in range(12):
        h.append('<span class="ovc" style="border-left-color:%s">%s<b>%s</b></span>'
                 % (CHCOLOR[i], CHNAME[i], sgn0(v[i])))
    h.append('</div>')
    return ''.join(h)


def shots_block(card_seg, max_samples=3):
    """从配方卡片里搬样片：对比场景全要 + 作者样片最多 max_samples 张。"""
    figs = re.findall(r'<figure>.*?</figure>', card_seg, re.S)
    cmp_figs = [f for f in figs if '__cmp__' in f]
    smp_figs = [f for f in figs if '__cmp__' not in f]
    picked = cmp_figs + smp_figs[:max_samples]
    if not picked:
        return ''
    return '<div class="osshots">%s</div>' % ''.join(picked)


def det_block(card_seg, cls):
    """把卡片里的某个 <details class="…"> 整块原样取出来（内容不重写）。"""
    m = re.search(r'<details class="%s"[^>]*>.*?</details>' % re.escape(cls), card_seg, re.S)
    return m.group(0) if m else ''


def params_block(card_seg):
    """参数行：槽位里是行内格式（和卡片 .params 不同），从卡片取数重排。"""
    m = re.search(r'<div class="params">(.*?)</div>', card_seg, re.S)
    if not m:
        return ''
    t = m.group(1)
    tc = re.search(r'色调曲线 <i>([^<]*)</i>', t)
    sh = re.search(r'阴影补偿 <i>([^<]*)</i>', t)
    sp = re.search(r'锐度 <i>([^<]*)</i>', t)
    cn = re.search(r'对比 <i>([^<]*)</i>', t)
    ex = re.search(r'曝光 <i>([^<]*)</i>', t)
    parts = []
    if tc:
        parts.append('色调曲线 %s' % tc.group(1).replace(' / ', ' / '))
    if sh:
        parts.append('阴影补偿 <b>%s</b>' % sh.group(1))
    if cn:
        parts.append('对比 %s' % cn.group(1))
    if sp:
        parts.append('锐度 %s' % sp.group(1))
    if ex:
        parts.append('作者曝光 %s' % ex.group(1))
    return '<div class="osline prm">%s</div>' % '　｜　'.join(parts)


def wb_line(a, g, tier_a, tier_g):
    """白平衡行：算位移格数（A-B 轴 + G-M 轴，曼哈顿距离）。"""
    if (a, g) == (tier_a, tier_g):
        return '<div class="osline wbok">白平衡：原配方即本档签名，与档位一致，<b>未改动</b></div>'
    d = abs(a - tier_a) + abs(g - tier_g)
    return ('<div class="osline wbno">白平衡：原配方是 %s，本档是 %s，'
            '<b>挪了 %s 格</b>（能接受再录；想 100%% 原味就换一格）</div>'
            % (W.__dict__ and sig(a, g), sig(tier_a, tier_g), ('%g' % d)))


def sig(a, g):
    left = ('A+%d' % a) if a > 0 else (('B%d' % abs(a)) if a < 0 else 'A0')
    right = ('G+%d' % g) if g > 0 else (('M%d' % abs(g)) if g < 0 else 'G0')
    return '%s %s' % (left, right)


def slot_html(slot_id, n, rec, card_seg, idx_f, tier_a, tier_g, tag=None):
    name = tag or rec['n']
    return (
        '<div class="oslot" id="%s">'
        '<div class="osh"><span class="osnum">槽 %d</span>'
        '<span class="osname">%s</span><span class="osauth">%s</span></div>'
        '<div class="osbody">%s<div class="osinfo">'
        '%s'
        '<div class="osline exif">样片来源 om-recipes.com：<b>对比场景</b>为本站统一拍摄'
        '（6 个场景可在「场景对比」页签按场景横向比较），<b>作者样片</b>为作者实拍，EXIF 见图注。</div>'
        '%s'
        '<div class="osline style">%s</div>'
        '%s%s%s'
        '%s%s'
        '</div></div></div>'
    ) % (slot_id, n, name, rec['a'], wheel_block(rec['v']), shots_block(card_seg),
         vals_block(rec['v']), idx_f,
         det_block(card_seg, 'fold fnote'), det_block(card_seg, 'en'),
         det_block(card_seg, 'fold fmine'),
         params_block(card_seg), wb_line(rec['wba'] or 0, rec['wbg'] or 0, tier_a, tier_g))


# ---------------------------------------------------------------- 自检
if __name__ == '__main__':
    import io
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    S = io.open(r'D:\workspace\om3-handbook\app\base.html', encoding='utf-8').read()
    ok = bad = 0
    nowheel = []
    for m in re.finditer(r'<div class="oslot" id="(oC[^"]+)">', S):
        sid = m.group(1)
        j = S.find('<div class="oslot" id="oC', m.start() + 10)
        seg = S[m.start():(j if j > 0 else len(S))]
        w = re.search(r'<div class="oswheel">.*?</div>', seg, re.S)
        v = re.search(r'<div class="osvals">.*?</div>', seg, re.S)
        # 从 osvals 反推 v，再看 wheel 是不是同一套
        has_svg = bool(w and '<svg' in w.group(0))
        if not has_svg and not v:
            nowheel.append(sid)          # 黑白槽（挂 MONO 档，oswheel 里放的是 .osmono 占位）
            continue
        if not w or not v:
            bad += 1
            print('  ✗ %s 只有 wheel/vals 其中一个' % sid)
            continue
        nums = [int(x) for x in re.findall(r'<b>([-+]?\d+)</b>', v.group(0))]
        if len(nums) != 12:
            bad += 1
            print('  ✗ %s osvals 不是 12 格（%d）' % (sid, len(nums)))
            continue
        if w.group(0) != '<div class="oswheel">%s</div>' % W.wheel_svg(nums):
            bad += 1
            print('  ✗ %s 色轮与 osvals 不一致' % sid)
        else:
            ok += 1
        if v.group(0) != vals_block(nums):
            bad += 1
            print('  ✗ %s osvals 排版与生成器不同' % sid)
    print('槽位自检：%d 个「色轮 ↔ osvals」逐字节一致，%d 个不一致；无色轮槽 %d 个（%s）'
          % (ok, bad, len(nowheel), ','.join(nowheel)))
    assert bad == 0, '有 %d 个槽位对不上' % bad
