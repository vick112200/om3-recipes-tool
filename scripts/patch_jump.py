# -*- coding: utf-8 -*-
"""场景对比：跳转按钮改成「原版方案 / 优化版」两个明确选项（没有的会说明）。
- 对比卡：两个按钮并列；不在优化版里的显示灰色提示
- 全屏看图：同样两个按钮
- 数据：每个条目补上优化版槽位标签 osl
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
P = BASE + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(BASE + r'\app\base.before_jump.html', 'w', encoding='utf-8', newline='').write(h)

# ---------- 1. 数据：osl 槽位标签 ----------
osl = {}
for m in re.finditer(r'<div class="oslot" id="(oC\d)-([a-z0-9]+)">(.*?)(?=<div class="oslot"|\Z)', h, re.S):
    sid, blk = m.group(1) + '-' + m.group(2), m.group(3)
    numlab = re.search(r'<span class="osnum">(.*?)</span>', blk)
    numlab = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', numlab.group(1))).strip() if numlab else ''
    osl[sid] = '%s · %s' % (m.group(1)[1:], numlab)      # 例：C4 · 槽 1

i = h.find('window.SC=')
SC, end = json.JSONDecoder().raw_decode(h, i + len('window.SC='))
n = 0
for sc in SC:
    for it in sc['items']:
        if it.get('os'):
            it['osl'] = osl.get(it['os'], '')
            n += 1
h = h[:i + len('window.SC=')] + json.dumps(SC, ensure_ascii=False, separators=(',', ':')) + h[end:]
print('SC 条目补上优化版槽位标签：%d 条' % n)

# ---------- 2. 对比卡的按钮 ----------
OLD_ACTS = """        var acts = '';
        if (it.i) {
          acts = '<div class="scacts"><button type="button" class="scjump" data-jump="' + esc(it.i) + '">看参数详情 →</button>' +
            (it.os ? '<button type="button" class="scjump2" data-jump="' + esc(it.os) + '">' + esc(it.osm || '') + ' 优化版 →</button>' : '') +
            '</div>';
        }"""
NEW_ACTS = """        var acts = '<div class="scacts">';
        if (it.i) acts += '<button type="button" class="scjump" data-jump="' + esc(it.i) + '">原版方案 · 看卡片 →</button>';
        if (it.os) acts += '<button type="button" class="scjump2" data-jump="' + esc(it.os) + '">优化版 · ' + esc(it.osl || '') + ' →</button>';
        else if (it.i) acts += '<span class="scnoplan">优化版 21 个槽位里没有这一卷</span>';
        acts += '</div>';"""
assert h.count(OLD_ACTS) == 1
h = h.replace(OLD_ACTS, NEW_ACTS, 1)

OLD_SLIDE = """        return '<div class="scslide" data-cid="' + esc(it.i || '') + '" data-lt="' +
          esc(it.n + ' · ' + it.a + (it.sl ? '（' + it.sl + '）' : '')) + '">' +"""
NEW_SLIDE = """        return '<div class="scslide" data-cid="' + esc(it.i || '') + '" data-lt="' +
          esc(it.n + ' · ' + it.a + (it.sl ? '（' + it.sl + '）' : '')) + '"' +
          ' data-os="' + esc(it.os || '') + '" data-osl="' + esc(it.osl || '') + '">' +"""
assert h.count(OLD_SLIDE) == 1
h = h.replace(OLD_SLIDE, NEW_SLIDE, 1)

# ---------- 3. 全屏看图的按钮 ----------
OLD_LB = """    lbbot.innerHTML = (it.cap || '') +
      (it.cid ? '<button class="lbdetail" type="button" data-jump="' + it.cid + '">看参数详情 →</button>' : '') +
      '<div class="lbhint">双指缩放 / 双击放大 · 左右滑动切换 · Esc 关闭（共 ' + group.length + ' 张）</div>';"""
NEW_LB = """    var acts = '';
    if (it.cid) acts += '<button class="lbdetail" type="button" data-jump="' + it.cid + '">原版方案 · 看卡片 →</button>';
    if (it.os) acts += '<button class="lbdetail lb2" type="button" data-jump="' + it.os + '">优化版 · ' + (it.osl || '') + ' →</button>';
    else if (it.cid) acts += '<div class="lbnoplan">这一卷没进优化版（优化版只有 21 个槽位）</div>';
    lbbot.innerHTML = (it.cap || '') + acts +
      '<div class="lbhint">双指缩放 / 双击放大 · 左右滑动切换 · Esc 关闭（共 ' + group.length + ' 张）</div>';"""
assert h.count(OLD_LB) == 1
h = h.replace(OLD_LB, NEW_LB, 1)

OLD_ITEM = """      items.push({ src: t.getAttribute('src'), title: title, cap: cap, el: t,
                   cid: (slide && slide.getAttribute('data-cid')) || '' });"""
NEW_ITEM = """      items.push({ src: t.getAttribute('src'), title: title, cap: cap, el: t,
                   cid: (slide && slide.getAttribute('data-cid')) || '',
                   os: (slide && slide.getAttribute('data-os')) || '',
                   osl: (slide && slide.getAttribute('data-osl')) || '' });"""
assert h.count(OLD_ITEM) == 1
h = h.replace(OLD_ITEM, NEW_ITEM, 1)

# ---------- 4. CSS ----------
ANCHOR = '.scjump2{background:#242424;color:#8fd8c2;border:1px solid #3a4a52}'
assert h.count(ANCHOR) == 1
NEW_CSS = (ANCHOR + '\n'
           '.scnoplan{align-self:center;font-size:11.5px;color:#8a8a8a;line-height:1.5;padding:6px 4px}\n'
           '.lbnoplan{font-size:11.5px;color:#8a8a8a;margin:8px 0 2px}\n'
           '#lb .lbbot .lbdetail.lb2{margin-top:6px;background:#242424;color:#8fd8c2;border:1px solid #3a4a52}')
h = h.replace(ANCHOR, NEW_CSS, 1)

# ---------- 5. 对比页脚说明 ----------
OLD_NOTE = '要看完整说明点「看参数详情」，会跳到那个配方的原始卡片并高亮。'
assert h.count(OLD_NOTE) == 1
h = h.replace(OLD_NOTE, '看完整说明有两个去处：点「原版方案 · 看卡片」跳到那个配方的原始卡片，点「优化版 · C? · 槽 ?」跳到优化版里对应的槽位（那一卷没进优化版时会写出来）。两处都会滚过去并高亮一下。', 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('对比页跳转按钮改成双选项，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
