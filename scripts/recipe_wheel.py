# -*- coding: utf-8 -*-
"""色轮 SVG 渲染器（第 43 轮抽出，供「图片 → 配方」录入复用）。

几何（从库里 57 张卡的既有 SVG 反推）：
  · viewBox 0 0 270 270，圆心 (130,130)
  · 12 根辐条：第 i 根跨 -90°+30(i-1) → -90°+30i，半径固定 84，stroke-width 8，色 CHCOLOR[i-1]
  · 12 个数字标号：半径 104.94，角度 -75°+30(i-1)
  · 数据多边形：顶点 = 第 i 根辐条起点角度、半径 r(v)=49.23*(1+v/8)
  · 圆心参考圆 r=49.23（= v0 的半径）
"""
import math

CHNAME = ['黄', '橙', '红', '品红', '紫', '蓝紫', '蓝', '浅蓝', '青', '绿', '黄绿', '嫩黄绿']
CHCOLOR = ['#FCF750', '#DBA12A', '#CC1210', '#CD076B', '#970AA0', '#7710E8',
           '#3054E0', '#5392EB', '#83E7EB', '#87EE77', '#9DEE3A', '#CBEE3A']
CX = CY = 130.0
R0 = 49.23          # v=0 的半径 = 参考圆
RSPOKE = 84.0       # 辐条半径
RLABEL = 104.94     # 数字标号半径
STEP = 30.0
A0 = -90.0          # 第 1 根辐条的起始角


def _pt(ang, r):
    a = math.radians(ang)
    return (CX + r * math.cos(a), CY + r * math.sin(a))


def sgn(v):
    return '%+d' % v if v else '0'


def r_of(v):
    return R0 * (1.0 + v / 8.0)


def wheel_svg(v, cls='wheel'):
    """v: 12 个整数（黄→嫩黄绿）。返回与库里逐字节一致的 <svg> 串。"""
    assert len(v) == 12
    p = ['<svg viewBox="0 0 270 270" class="%s">' % cls]
    p.append('<circle cx="130" cy="130" r="49.23" fill="none" stroke="#fff" '
             'stroke-width="1.5" opacity="0.6"/>')
    for i in range(12):
        x1, y1 = _pt(A0 + STEP * i, RSPOKE)
        x2, y2 = _pt(A0 + STEP * (i + 1), RSPOKE)
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="8" stroke-linecap="round"/>' % (x1, y1, x2, y2, CHCOLOR[i]))
        lx, ly = _pt(A0 + STEP * i + STEP / 2.0, RLABEL)
        p.append('<text x="%.1f" y="%.1f" fill="#fff" font-size="13" font-weight="700" '
                 'text-anchor="middle" dominant-baseline="middle">%d</text>' % (lx, ly, i + 1))
    pts = []
    for i in range(12):
        x, y = _pt(A0 + STEP * i, r_of(v[i]))
        pts.append('%.1f,%.1f' % (x, y))
    p.append('<polygon points="%s" fill="rgba(255,255,255,0.30)" stroke="#fff" '
             'stroke-width="2.2"/>' % ' '.join(pts))
    p.append('</svg>')
    return ''.join(p)


def vals_line(v):
    return '<div class="vals">%s</div>' % ' '.join('%+d' % x for x in v)


# ---------------------------------------------------------------- 自检
if __name__ == '__main__':
    import io
    import re
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    S = io.open(r'D:\workspace\om3-handbook\app\base.html', encoding='utf-8').read()
    D = __import__('json').JSONDecoder()
    i = S.find('window.__OM3RECIPES__')
    j = S.index('=', i) + 1
    while S[j].isspace():
        j += 1
    REC = D.raw_decode(S, j)[0]
    byslug = dict((r['slug'], r) for r in REC)
    cards = re.findall(r'<div class="card" id="r-([^"]+)">', S)
    ok = fail = 0
    nowheel = []
    seen = set()
    for slug in cards:
        if slug in seen:
            continue
        seen.add(slug)
        r = byslug.get(slug)
        if not r:
            print('  跳过（数据里没有）：', slug)
            continue
        i0 = S.find('id="r-%s"' % slug)
        i1 = S.find('<div class="card" id="r-', i0 + 10)
        if i1 < 0:
            i1 = S.find('</details>', i0)
        seg = S[i0:i1]
        # ⚠ 必须只在**这张卡的范围**里找 SVG。以前写成 S[i0:] → 没轮子的卡会抓到下一张卡的 SVG，
        #    于是"没轮子"被误判成"轮子和数据不一致"（2026-09-25 踩过，别再犯）。
        m = re.search(r'<svg viewBox="0 0 270 270" class="wheel">.*?</svg>', seg, re.S)
        want = wheel_svg(r['v'])
        if m is None:
            nowheel.append((slug, r['t'], 'nomon' in seg))
            continue
        if m.group(0) == want:
            ok += 1
        else:
            fail += 1
            if fail <= 3:
                got = m.group(0) if m else '(没找到 svg)'
                print('  ✗ %s 不一致' % slug)
                for k, (a, b) in enumerate(zip(got, want)):
                    if a != b:
                        print('     首处差异 @%d' % k)
                        print('      库里:', got[max(0, k - 60):k + 60])
                        print('      生成:', want[max(0, k - 60):k + 60])
                        break
                else:
                    print('      长度不同', len(got), len(want))
    print('色轮自检：%d 张逐字节一致，%d 张不一致' % (ok, fail))
    print('没有色轮的卡（走 .nomon 占位，共 %d 张）：%s'
          % (len(nowheel), ', '.join('%s[%s]' % (a, b) for a, b, c in nowheel)))
    assert fail == 0, '有 %d 张卡的色轮和数据对不上' % fail
    assert all(c for a, b, c in nowheel), '无轮卡必须带 .nomon 占位：%s' % [a for a, b, c in nowheel if not c]
    # 顺便核对 vals 行（无轮卡不该有 vals）
    bad = 0
    for slug in seen:
        r = byslug.get(slug)
        if not r:
            continue
        i0 = S.find('id="r-%s"' % slug)
        i1 = S.find('<div class="card" id="r-', i0 + 10)
        seg = S[i0:(i1 if i1 > 0 else S.find('</details>', i0))]
        m = re.search(r'<div class="vals">([^<]*)</div>', seg)
        want = vals_line(r['v'])[len('<div class="vals">'):-len('</div>')]
        if not m:
            if not any(x[0] == slug for x in nowheel):
                bad += 1
                print('  ✗ 有轮卡却没 vals：%s' % slug)
            continue
        if m.group(1) != want:
            bad += 1
            if bad <= 3:
                print('  ✗ vals 不一致 %s: 库里=%r 生成=%r' % (slug, m.group(1), want))
    print('vals 行自检：不一致 %d 张' % bad)
    assert bad == 0, 'vals 行有 %d 张对不上' % bad
    print('✅ 全部对账通过：%d 张带轮 + %d 张无轮，与数据完全一致' % (ok, len(nowheel)))
