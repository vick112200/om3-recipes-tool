# -*- coding: utf-8 -*-
"""第 42 轮 · 步骤 2：清掉步骤 1 的残留
 ① 重建 `window.__OM3PHOTOTAGS__ / __OM3PHOTOS__`（删掉的 12 张模拟图不该再出现）
 ② 重建 `window.__OM3SC__`（场景 slides 里引用了 r-om3lab_* / oLAB-N，要重新生成）
 ③ 清掉只在"本站设计"里用过的 CSS 与文案（#toc3 规则、LAB 档说明、"全站 91 条"计数等）
"""
import io, json, os, re, sys
sys.path.insert(0, r'D:\workspace\om3-handbook\scripts')
import patch_scidx as PS
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
IMG = r'D:\workspace\om3-handbook\apk\assets\images'
DEC = json.JSONDecoder()
SEL_TAGS = {
 'portrait': ['人像'], 'wedding': ['人像'], 'kids': ['人像'], 'mono': ['人像'],
 'flower': ['花卉'], 'sunset': ['花卉'], 'forest': ['绿意'], 'autumn': ['绿意'],
 'night': ['夜景'], 'skywater': ['天空水面'], 'snow': ['高调'], 'mist': ['雾'],
 'arch': ['中性白'], 'still': ['中性白'], 'street': ['人群'], 'travel': ['人群'], 'backlight': ['人群'],
 'rain': ['日常'], 'food': ['日常'], 'indoor': ['日常'], 'film': ['日常'],
}
s = io.open(P, encoding='utf-8').read()
n = 0

# ---------- ① 照片标签/清单：只保留实际存在的图 ----------
files = set(os.listdir(IMG))
m3 = re.search(r'window\.__OM3PHOTOTAGS__\s*=\s*', s)
PT, e3 = DEC.raw_decode(s, m3.end())
m4 = re.search(r'window\.__OM3PHOTOS__\s*=\s*', s)
PH, e4 = DEC.raw_decode(s, m4.end())
PT2 = {k: v for k, v in PT.items() if k in files}
PH2 = {k: [f for f in v if f in files] for k, v in PH.items()}
PH2 = {k: v for k, v in PH2.items() if v}
print('  照片标签 %d → %d ｜ 配方图清单 %d → %d' % (len(PT), len(PT2), len(PH), len(PH2)))
s = s[:m3.end()] + json.dumps(PT2, ensure_ascii=False, separators=(',', ':')) + ';\n' + s[e3:]
m4 = re.search(r'window\.__OM3PHOTOS__\s*=\s*', s)
PH, e4 = DEC.raw_decode(s, m4.end())
s = s[:m4.end()] + json.dumps(PH2, ensure_ascii=False, separators=(',', ':')) + ';\n' + s[e4:]
n += 2

# ---------- ② 重建 __OM3SC__ ----------
m2 = re.search(r'var IDX=', s)
IDX, _ = DEC.raw_decode(s, m2.start() + len('var IDX='))
OSLOT = {}
for e in IDX:
    if str(e.get('h', '')).startswith('o') and e.get('n'):
        OSLOT.setdefault(e['n'], e)


def pick(anchor, key):
    want = SEL_TAGS.get(key, [])
    slug = re.sub(r'^[rk]-', '', str(anchor or ''))
    cand = PH2.get(slug) or []
    best, bs, btg = '', -1, []
    for f in cand:
        tg = PT2.get(f, [])
        sc = 3 * sum(1 for w in want if w in tg) + (1 if '__cmp__' in f else 0)
        if sc > bs:
            bs, best, btg = sc, f, tg
    return best, (btg if bs > 0 else [])


SCENES = []
for k, label, kw in PS.SCENES:
    items = []
    for it in IDX:
        g = str(it.get('g') or '')
        if not g:
            continue
        hay = g + ' ' + str(it.get('t') or '')
        if not any(w in hay for w in kw):
            continue
        f, tg = pick(it['h'], k)
        if not f:
            continue
        os_ = OSLOT.get(it['n'])
        items.append({'i': it['h'], 'n': it['n'], 'a': it.get('a', ''), 'sl': it.get('sl', ''),
                      't': it.get('t', ''), 'f': f,
                      'd': (('图按画面自动归类：%s（自动判断，偶尔会看错）｜ ' % ' / '.join(tg)) if tg else '') +
                           str(it.get('f') or '')[:150],
                      'os': os_['h'] if os_ else '', 'osl': (os_.get('sl') or '') if os_ else ''})
    SCENES.append({'k': k, 'label': label, 'items': items})
    print('    %-14s %3d 条' % (label, len(items)))
js = 'window.__OM3SC__ = ' + json.dumps(SCENES, ensure_ascii=False, separators=(',', ':')) + ';\n'
s = re.sub(r'window\.__OM3SC__\s*=\s*\[.*?\];\n', js.replace('\\', '\\\\'), s, count=1, flags=re.S)
if 'window.__OM3SC__ = ' not in s:
    print('  ⚠ __OM3SC__ 替换失败，改用标记块替换')
    s = re.sub(r'<!-- OM3SC-BEGIN -->.*?<!-- OM3SC-END -->\n?', '<!-- OM3SC-BEGIN -->\n' + js + '<!-- OM3SC-END -->\n', s, flags=re.S)
n += 1

# ---------- ③ 清 CSS 与文案 ----------
# 把 #toc3 从合并过的选择器里摘掉（现在没有这个元素了）
s2 = re.sub(r',#toc3(?=[,{.])', '', s)
s2 = re.sub(r'#toc3(?=,|\.|\{|\s)', '', s2) if '#toc3' in s2 else s2
if s2 != s:
    print('  ✅ 摘掉 #toc3 的 CSS 选择器（%d 处）' % (s.count('#toc3') - s2.count('#toc3')))
    s = s2
    n += 1
rep = [
 ('<span class="sh">6 个档位（5 个 C 档 + 本站设计档）</span>', '<span class="sh">5 个档位</span>'),
 ('；<b>另有第 6 档「LAB 本站设计」</b>——12 条本站自己设计的配方（Auto 不偏移，没有实拍样片，格子里是模拟预览）。相机上只有 C1–C5，所以写入 LAB 的配方时，在弹窗里选你要写进哪个 C 档', ''),
 ('<br><b>第 6 档「LAB 本站设计」那 12 格全部没有实拍样片</b>——格子里那张标注了 <b>「模拟预览 · 不是相机实拍」</b>：拿「Default - 1」（数值全 0）在同一场景的实拍当底，按该条的色轴/影调数值做近似映射，<b>只反映色轮 / 影调 / 对比 / 锐度的方向，不含白平衡与曝光</b>；在「原版方案」页签那条「本站设计」分区里，还放了一组「原站真实实拍 vs 我的模拟」自检对照，可信到什么程度你可以自己判断。', ''),
 ('按白平衡偏移分档 · 全站 91 条配方（原站 79 + 本站设计 12）', '按白平衡偏移分档 · 全站 79 条配方'),
]
for a, b in rep:
    if a in s:
        s = s.replace(a, b, 1); n += 1
    else:
        print('  ⚠ 文案没找到：%s' % a[:44])

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('✅ 步骤 2 完成（%d 处）。残留：' % n)
for kw in ('om3lab', 'oLAB', 'toc3', 'LIDX', '本站设计'):
    print('   %-8s %d 处' % (kw, s.count(kw)))
