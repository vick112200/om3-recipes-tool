# -*- coding: utf-8 -*-
"""第 56 轮补：给「检测认不出」的场景出**联系表**，让用户点编号 → 落成人工白名单。

每个场景：取该场景成员的**作者主图**（一人一张，最代表），编上号，拼成一张图。
用户回报编号（如「3, 9, 14」）→ 写进 `scripts/_r56_scenepick.json`：
  { "<scene key>": ["<文件名>", …] }   # 生成器优先用这些图（人工指定 > 自动挑）

用法：python scripts/mk_sheet_r56.py            # 出全部 4 张
      python scripts/mk_sheet_r56.py architectural   # 只出某几个场景
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFont      # noqa: E402

FONT = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 15)   # 默认字体没有中文，会画成方块
FONT_S = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 13)

ROOT = r'D:\workspace\om3-handbook'
IMG = os.path.join(ROOT, 'apk', 'assets', 'images')
TMP = os.environ['TEMP']
src = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()


def grab(t, m):
    i = t.rindex(m) + len(m)
    while t[i] in ' \n':
        i += 1
    return json.JSONDecoder().raw_decode(t, i)[0]


SC = grab(src, 'window.__OM3SC__ =')
PH = grab(src, 'window.__OM3PHOTOS__ =')
REC = {r['slug']: r for r in grab(src, 'window.__OM3RECIPES__=')}

# 每个场景一张表（表内按成员顺序编号）
SHEETS = {
    'arch': ('建筑几何', '看哪张是**建筑/几何线条**（屋顶、墙面、楼梯、窗、桥、塔…）；都不像就回"无"'),
    'sunset': ('日落晚霞', '看哪张是**日落/晚霞**（天上橙红紫、太阳低）'),
    'flower': ('花卉', '看哪张有**花**（一朵/一束/一片都算）'),
    'still': ('静物极简', '看哪张是**静物/极简**（桌上摆件、瓶罐、书、餐具、单色背景小景）'),
    'backlight': ('逆光大光比', '看哪张是**逆光/大光比**（背景过曝、主体偏暗、边缘发光）'),
    'mist': ('雾 / 阴天 / 雨天', '看哪张是**雾天/阴天平光**（发灰、低反差、远景发白）'),
    'wedding': ('婚礼聚会', '看哪张有**婚礼/聚会**（仪式、礼服、宴席、举杯、一群人庆祝）'),
    'kids': ('儿童亲子', '看哪张有**小孩**（0-12 岁，玩耍、被抱着、和大人互动）'),
    'food': ('食物咖啡', '看哪张是**食物/餐具/咖啡**（菜、甜点、杯盘、桌面餐食）'),
}
COLS, TW, TH = 5, 300, 240


def sheet(key):
    sc = next((x for x in SC if x['k'] == key), None)
    if not sc:
        print('   ⚠ 没有场景', key)
        return None
    rows = []
    seen = set()
    for it in sc['items']:
        slug = re.sub(r'^[rk]-', '', it.get('i') or '')
        if slug in seen:
            continue
        seen.add(slug)
        fs = PH.get(slug) or []
        hero = next((f for f in fs if '__cmp__' not in f), '')
        if hero:
            rows.append((slug, hero))
    n = len(rows)
    nr = (n + COLS - 1) // COLS
    im = Image.new('RGB', (COLS * TW, nr * TH + 34), '#101a16')
    d = ImageDraw.Draw(im)
    title = SHEETS[key][0] + '  ——  ' + SHEETS[key][1]
    d.text((8, 8), title, fill='#8fd8c2', font=FONT)
    for k, (slug, f) in enumerate(rows):
        x, y = (k % COLS) * TW + 5, (k // COLS) * TH + 38
        try:
            ph = Image.open(os.path.join(IMG, f))
            ph.thumbnail((TW - 12, TH - 46))
            im.paste(ph, (x, y))
        except Exception as e:                                    # noqa: BLE001
            d.text((x + 4, y + 40), '读取失败', fill='#ff8080', font=FONT_S)
        d.text((x, y + TH - 50), '#%-3d %s' % (k + 1, (REC.get(slug, {}).get('n') or slug)[:24]), fill='#ffffff', font=FONT_S)
        d.text((x, y + TH - 33), (REC.get(slug, {}).get('a') or '')[:22], fill='#ffd479', font=FONT_S)
        d.text((x + 150, y + TH - 33), f.split('__')[-1][:16], fill='#8fd8c2', font=FONT_S)
    out = os.path.join(TMP, 'sheet_%s.png' % key)
    im.save(out)
    print('   %-14s %2d 个候选 → %s' % (key, n, out))
    return out


keys = [a for a in sys.argv[1:] if a in SHEETS] or ['arch']
for k in keys:
    sheet(k)

# 同时写一份空白的白名单模板（用户回报后我填）
tpl = os.path.join(ROOT, 'scripts', '_r56_scenepick.json')
if not os.path.exists(tpl):
    io.open(tpl, 'w', encoding='utf-8', newline='').write('{}')
    print('已建空白白名单：scripts/_r56_scenepick.json')
