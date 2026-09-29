# -*- coding: utf-8 -*-
"""第 45 轮 · 加「怎么挑这 5 个」一览表（幂等）

要点（这是本轮真正要传达的事）：
  · 相机只有 **5 个 C 档**；C1..C10 是 **10 个候选档**，从里面挑 5 个。
  · **原方案的 5 档其实只用了 4 种白平衡**：C1（人像）和 C3（风光）都是 **A+1 G+1**
    ⇒ 有一个 C 档是"重"的，相当于白空出一档。去掉重复后是 **9 个彩色签名**，挑 5 个。
  · 同一个签名的档**只需要占一个 C 档**（多选就是浪费）。
  · 表里列出了 10 个候选档 + 4 组"照着挑"的组合。

做法：插一节 `<details class="sec" id="opick">`（在 #ointro 之后、#oskin 之前），
并把 `#omodes` 的标题「5 个档位」改成「10 个候选档」。
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
D = json.JSONDecoder()
LOG = []

s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r45.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r45.html')

# ---------------------------------------------------------------- 从 HTML 里读 10 个候选档
tiers = []
for m in re.finditer(r'<div class="omode" id="(oC\d+)">', s):
    tid = m.group(1)
    j = s.find('<div class="omode" id="', m.start() + 10)
    if j < 0:                      # 最后一个候选档：截到容器结尾（#opink 之前）
        j = s.find('<details class="sec" id="opink"', m.start())
    seg = s[m.start():(j if j > 0 else len(s))]
    title = re.search(r'<span class="omtitle">([^<]*)</span>', seg).group(1)
    wb = re.search(r'<span class="omchip wb">白平衡 <b>([^<]*)</b>', seg).group(1)
    wb = wb.replace('Auto ', '')      # 表里统一只留签名（C4 的 chip 写的是 'Auto A0 G0'）
    n = len(re.findall(r'<div class="oslot" id="oC\d+-[1-4]"', seg))
    nmono = len(re.findall(r'<div class="oslot" id="oC\d+-m1"', seg))
    tiers.append(dict(id=tid, n=tid[1:], title=title, wb=wb, slots=n, mono=nmono))
print('读到 %d 个候选档：%s' % (len(tiers), ', '.join('%s/%s/%d格' % (t['n'], t['wb'], t['slots']) for t in tiers)))

ONELINE = {
    'C1': '把脸拍白拍透（人像档）',
    'C2': '富士负片味的纪实暖（街拍档）',
    'C3': '反转片浓艳 · 老柯达（风光档）',
    'C4': '不偏暖的夜色与混光（夜景档）',
    'C5': '柯达暖纪实 · 日落（胶片档）',
    'C6': '暖里带玫瑰：人像的暖粉调',
    'C7': '浓而平 · 现代胶片',
    'C8': '青蓝都市 · 偏冷纪实',
    'C9': '青调柔雾 · 清透风光',
    'C10': 'Kodachrome 的两个版本',
}

rows = []
for t in tiers:
    rows.append('<tr><td class="og"><a href="#%s">%s</a></td><td class="mono"><b>%s</b></td>'
                '<td class="mono">%d 格%s</td><td>%s</td></tr>'
                % (t['id'], t['title'], t['wb'], t['slots'],
                   ' ＋1 黑白' if t['mono'] else '', ONELINE.get(t['n'], '')))

COMBOS = [
    ('通用 / 什么都拍', ['C1', 'C2', 'C4', 'C5', 'C7'],
     '四个原主题档各留一格，再补一个"浓而平"的现代胶片；<b>白平衡一格都没动</b>。'),
    ('多拍人', ['C1', 'C6', 'C2', 'C4', 'C5'],
     '人像占两格：C1 把脸拍白拍透，C6 给暖粉调；再加纪实、夜景、胶片各一格。'),
    ('多拍风光', ['C3', 'C9', 'C2', 'C4', 'C5'],
     '风光占两格：C3 反转片浓艳，C9 青调柔雾；<b>C1 与 C3 同签名，所以这里只留 C3</b>。'),
    ('胶片味重', ['C5', 'C10', 'C7', 'C2', 'C4'],
     '柯达暖、Kodachrome 怀旧、现代浓郁三种胶片味各占一格。'),
]

SEC = (
    '<details class="sec" open id="opick"><summary>'
    '<span class="sh">怎么挑这 5 个（10 个候选档一览）</span><span class="si"></span></summary>'
    '<div class="sb">'
    '<p class="onote"><b>相机只有 5 个 C 档，下面有 10 个候选档。</b>'
    '每一个候选档就是一整套「一份白平衡 + 最多 4 个 Color Profile 槽」，'
    '你从里面挑 5 个写进相机就行——挑哪 5 个完全取决于你拍什么，没有标准答案。</p>'

    '<div class="warnbox"><b>先说一件容易吃亏的事：原来的 5 档其实只用了 4 种白平衡。</b>'
    'C1（人像）和 C3（风光）在站上的白平衡签名<b>都是 A+1 G+1</b>，'
    '也就是说那 5 个 C 档里有两个在往相机里写同一个白平衡设置——<b>相当于白空出一个 C 档</b>。'
    '去掉这个重复之后，一共是 <b>9 个彩色签名 + 1 个黑白</b>；'
    '相机只有 5 个 C 档 ⇒ <b>从这 9 个彩色签名里挑 5 个</b>。'
    '同一个签名的档<b>只需要占一个 C 档</b>，两个都选是浪费。</div>'

    '<div class="tw"><table class="otbl"><thead><tr><th>候选档</th><th>白平衡签名</th>'
    '<th>格数</th><th>干什么用</th></tr></thead><tbody>%s</tbody></table></div>'
    '<p class="onote">C6–C10 是<b>按白平衡签名补的候选档</b>：这 5 个签名在库里各只有 2 卷，'
    '所以每档只填得满 2 格，剩下 2 格留空——想用可以把「我的配方」里自配的方案录进去。'
    '<b>它们一律用原生签名，一格白平衡都没动。</b></p>'
    '<h3 class="pkh">照着挑：4 组 5 档组合</h3>'
    '<p class="onote">下面每组都是 <b>5 个互不重复的白平衡签名</b>，直接照抄进相机就行。'
    '点档名可以跳到那一档看具体四个槽位。</p>%s'
    '<p class="onote">另外那一档黑白（Creative Mono / Basic Color）<b>挂在拨盘的 MONO 档上，不占 C 档槽位</b>，'
    '所以它不参与这 5 个的挑选——它在 C1 档位卡里，跟着 C1 的白平衡走。</p>'
    '</div></details>'
) % (''.join(rows),
     ''.join('<div class="omwhy"><b>%s：</b>%s<br>%s</div>'
             % (name,
                ' ＋ '.join('<a href="#o%s">%s</a>' % (c, c) for c in combo),
                why)
             for name, combo, why in COMBOS))

if 'id="opick"' in s:
    LOG.append('  · #opick 已存在，跳过')
else:
    k = s.find('<details class="sec" id="oskin"')
    assert k > 0, '找不到 #oskin'
    s = s[:k] + SEC + s[k:]
    LOG.append('  ✅ 已插入 #opick（在 #ointro 之后、#oskin 之前，%d 字符）' % len(SEC))

# 目录（toc2）里那条
if '<a class="lv2" href="#omodes">5 个档位</a>' in s:
    s = s.replace('<a class="lv2" href="#omodes">5 个档位</a>',
                  '<a class="lv2" href="#omodes">10 个候选档（挑 5 个）</a>', 1)
    LOG.append('  ✅ 目录 #omodes 条目：5 个档位 → 10 个候选档（挑 5 个）')

# 「保持暖色调」那段里的「5 个 C 档」
_old_wb = '档位推荐 5 个 C 档全部建立在 <b>Auto 白平衡</b>上（C1–C3、C5 是 Auto ＋ 琥珀／绿偏移，C4 是 Auto 不偏移）'
_new_wb = '档位推荐这 10 个候选档全部建立在 <b>Auto 白平衡</b>上（C1–C3、C5、C6–C10 都是 Auto ＋ 琥珀／绿／品红偏移，C4 是 Auto 不偏移）'
if _old_wb in s:
    s = s.replace(_old_wb, _new_wb, 1)
    LOG.append('  ✅ 保持暖色调那段：5 个 C 档 → 10 个候选档')

# #omodes 标题
if '<span class="sh">5 个档位</span>' in s:
    s = s.replace('<span class="sh">5 个档位</span>',
                  '<span class="sh">10 个候选档（挑 5 个写进相机）</span>', 1)
    LOG.append('  ✅ #omodes 标题：5 个档位 → 10 个候选档')

# 跳转条：加一条「挑档指南」，放在「说明」后面
if 'data-goto="opick"' not in s:
    m = re.search(r'(<a href="#ointro" data-goto="ointro">[^<]*</a>)', s)
    assert m, '跳转条里找不到 ointro'
    s = s[:m.end(1)] + '<a href="#opick" data-goto="opick">怎么挑 5 个</a>' + s[m.end(1):]
    LOG.append('  ✅ 跳转条 +「怎么挑 5 个」')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n'.join(LOG))
print('写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))

# ---------------------------------------------------------------- 自检
print('\n=== 自检 ===')
S = io.open(P, encoding='utf-8').read()
print('候选项表行数：', len(re.findall(r'<tr><td class="og"><a href="#oC\d+"', S)))
print('#opick 存在：', 'id="opick"' in S)
print('跳转条有 opick：', 'data-goto="opick"' in S)
ids = set(re.findall(r'\bid="([^"]+)"', S))
dead = sorted(l for l in set(re.findall(r'href="#([^"]+)"', S)) if l not in ids and "'" not in l)
print('死链：', dead or '无')
print('五档/10 档标题：', re.findall(r'<span class="sh">10 个候选档[^<]*</span>', S))
