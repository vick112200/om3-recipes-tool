# -*- coding: utf-8 -*-
"""配方/档位/场景 数据体检（只读）——
   A. 配方合集卡片上的「白平衡偏移」标签 vs 数据里的 wba/wbg（缺标 / 标错）
   B. 档位推荐槽位（.oslot）上的白平衡标签 vs 数据（缺标 / 标错）
   C. 场景（__OM3SC__ / __OM3SCENES__）：哪些条目缺详细描述；哪些条目的「避开」与所在场景自相矛盾
   D. 场景里推荐的配方，其「避开」原文里提到该场景天气/题材的
   E. 卡片标签（明显偏暖/偏冷…）与色轮数据的方向是否一致（机械核对）
用法：python om3_audit_data.py
"""
import io
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()


def grab(var):
    """从 window.<var> = <json>; 里把 JSON 抠出来（括号配对）。"""
    i = s.index('window.%s' % var)
    j = s.index('=', i) + 1
    while s[j] in ' \n':
        j += 1
    open_ch = s[j]
    close_ch = {'[': ']', '{': '}'}[open_ch]
    depth = 0
    k = j
    while k < len(s):
        c = s[k]
        if c == '"':                     # 跳过字符串
            k += 1
            while k < len(s):
                if s[k] == '\\':
                    k += 2
                    continue
                if s[k] == '"':
                    break
                k += 1
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return json.loads(s[j:k + 1])
        k += 1
    raise SystemExit('抠不出来：' + var)


REC = grab('__OM3RECIPES__')
OPT = grab('__OM3OPT__')
SC = grab('__OM3SC__')
try:
    SCN = grab('__OM3SCENES__')
except Exception as e:
    SCN = None
    print('（__OM3SCENES__ 读不到：%s）' % e)

byslug = {r['slug']: r for r in REC}
byname = {}
for r in REC:
    byname.setdefault(r['n'], []).append(r)
print('配方 %d 条 ｜ 优化清单 %d 条 ｜ 场景（SC）%d 个 ｜ 场景页（SCENES）%s' %
      (len(REC), len(OPT), len(SC), (len(SCN) if isinstance(SCN, list) else type(SCN).__name__)))


def wbtxt(r):
    """数据里的白平衡偏移文本：A{+n} G{+n}"""
    if r is None:
        return '?'
    a, g = r.get('wba'), r.get('wbg')
    if a is None or g is None:
        return '?'
    return 'A%s G%s' % (('+%d' % a) if a > 0 else a, ('+%d' % g) if g > 0 else g)


def norm(t):
    return re.sub(r'\s+', '', str(t or '')).upper().replace('＋', '+')


# ---------------- A. 配方合集卡片 ----------------
print('\n=== A. 配方合集卡片上的白平衡标签 vs 数据 ===')
cards = {}
for m in re.finditer(r'<div class="card" id="r-([^"]+)">(.*?)(?=<div class="card" id="r-|</details>)', s, re.S):
    cards[m.group(1)] = m.group(2)
print('页面上卡片 %d 张 ｜ 数据 %d 条' % (len(cards), len(REC)))
miss, bad, extra = [], [], []
for slug, html in cards.items():
    r = byslug.get(slug)
    m = re.search(r'<div class="chd">.*?<span class="slot">([^<]*)</span>', html, re.S)
    shown = m.group(1).strip() if m else ''
    if not r:
        extra.append((slug, shown))
        continue
    want = wbtxt(r)
    if not shown:
        miss.append((slug, r['n'], want))
    elif norm(shown) != norm(want):
        bad.append((slug, r['n'], shown, want))
print('  缺标签 %d 张：%s' % (len(miss), '、'.join('%s[应 %s]' % (x[1], x[2]) for x in miss[:12])))
print('  标签与数据不符 %d 张：%s' % (len(bad), '、'.join('%s(页面 %s / 数据 %s)' % (x[1], x[2], x[3]) for x in bad[:12])))
print('  页面有卡、数据里没有 %d 张：%s' % (len(extra), extra[:8]))

# ---------------- B. 档位推荐槽位 ----------------
print('\n=== B. 档位推荐槽位（.oslot）与数据 ===')
slots = re.findall(r'<div class="oslot" id="(oC\d+-(?:m?\d+))">(.*?)(?=<div class="oslot" id="|</div></div></div>)', s, re.S)
print('  槽位卡 %d 个' % len(slots))
slotmiss, slotbad, nolib = [], [], []
for sid, html in slots:
    nm = re.search(r'<span class="osname">([^<]*)</span>', html)
    name = (nm.group(1).strip() if nm else '')
    lab = re.search(r'<span class="oswb">([^<]*)</span>', html) or re.search(r'<span class="oslotwb">([^<]*)</span>', html)
    shown = lab.group(1).strip() if lab else ''
    cands = byname.get(name) or []
    if not cands:
        nolib.append((sid, name))
        continue
    want = wbtxt(cands[0])
    if not shown:
        slotmiss.append((sid, name, want))
    elif norm(shown) != norm(want):
        slotbad.append((sid, name, shown, want))
print('  槽位没有白平衡标签：%d 个' % len(slotmiss))
print('  槽位标签与数据不符：%d 个 %s' % (len(slotbad), slotbad[:8]))
print('  名字在库里对不上：%d 个 %s' % (len(nolib), nolib[:8]))

# ---------------- C/D. 场景 ----------------
print('\n=== C. 场景（__OM3SC__）：缺详细描述 / 避开自相矛盾 ===')
WEATHER = ['阴天', '雨天', '雪', '雾', '夜景', '日光', '晴天', '多云', '清晨', '黄昏', '室内', '棚拍', '灯光']
nodetail, contra, mention = [], [], []
for sc in SC:
    k, lab, items = sc.get('k'), sc.get('label'), sc.get('items') or []
    for it in items:
        nm = it.get('n', '')
        dd = (it.get('dd') or '').strip()
        fd = (it.get('fd') or '').strip()
        d = (it.get('d') or '').strip()
        if not dd and not fd:
            nodetail.append((lab, nm, it.get('i')))
        avoid = (it.get('v') or '')          # 场景索引里的「避开」原文
        if avoid:
            for w in WEATHER:
                if w in lab and (w in avoid or ('避免' in avoid and w in avoid)):
                    contra.append((lab, nm, avoid[:40]))
                    break
            if lab and lab[:2] in avoid:
                mention.append((lab, nm, avoid[:40]))
print('  缺详细描述（dd/fd 都空）的条目：%d 条' % len(nodetail))
for x in nodetail[:25]:
    print('     · %s → %s (%s)' % x)
print('  所在场景与「避开」矛盾（场景名里的天气出现在避开里）：%d 条' % len(contra))
for x in contra[:20]:
    print('     · 场景「%s」里有 %s，而它的避开写着：%s…' % x)

# ---------------- E. 标签方向 vs 色轮 ----------------
print('\n=== E. 卡片标签方向 vs 色轮数据（机械核对）===')
WARM = [0, 1, 2, 3]          # 黄 / 橙 / 红 / 品红（暖侧）
COOL = [6, 7, 8, 9, 10, 11]  # 蓝 / 浅蓝 / 青 / 蓝紫 / 紫 / 黄绿（冷侧）
tagbad = []
for slug, html in cards.items():
    r = byslug.get(slug)
    if not r:
        continue
    tg = re.findall(r'<div class="tags">(.*?)</div>', html, re.S)
    tags = re.sub(r'<[^>]+>', ' ', tg[0]).split() if tg else []
    v = r.get('v') or []
    if len(v) < 12:
        continue
    warm = sum(v[i] for i in WARM)
    cool = sum(v[i] for i in COOL)
    t = ' '.join(tags)
    if '明显偏暖' in t and warm < cool:
        tagbad.append((r['n'], tags, warm, cool))
    if '明显偏冷' in t and cool < warm:
        tagbad.append((r['n'], tags, warm, cool))
print('  标签方向与色轮相反的：%d 条' % len(tagbad))
for x in tagbad[:15]:
    print('     · %s %s（暖侧合计 %d / 冷侧合计 %d）' % x)
