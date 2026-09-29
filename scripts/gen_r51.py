# -*- coding: utf-8 -*-
"""第 51 轮生成器（幂等）· v3.5 —— 文案补写 + 按参数重新规划场景

用户 2026-09-25 追加：
  ①「补写，并且你根据摄影调色知识、奥巴的色轮原理，把说明写了，写专业一点」
  ②「你看看有没有必要过滤，因为可能你之前写的避开xxx是错的，你要重新审视之前的所有文案，然后再重新规划」
  ③「室内暖光这个我不太懂」
  ④「白平衡自己进相机改，因为现在是支持一个档位几个槽位不同的白平衡的，需要用户自己用的时候改」

先查（`scripts/om3_profile.py` 的 profile()/对账）：
  · ⚠ **纠正第 50 轮的一个测量错误**：我当时切卡片用的正则以 `</details>` 结尾 → 每张卡都被截断在
    第一个折页处，"卡片里有没有「补充」折页"永远查不到。按"到下一张卡开头"重切后实测：
    **58 张卡全都有「补充」折页（fold fmine）**，50 张另有「原文」（fnote）。
    ⇒ 第 50 轮那句"51 张卡没有补充折页"**是错的**；本轮的「参数解读」是**另写一折**（不覆盖、不冒充），
      并统一用作场景里 289 张照片那份说明的来源（那份早年按关键词拼的 6 行口径不一致）。
  · 场景推荐原来是**按文字关键词**过滤的（我上一轮的做法）：文字一错，过滤就错。
    ⇒ 本轮改成**按参数**判断场景适配（色环方向 / 饱和总量 / 反差 / 白平衡），文字只是解释。

本脚本 3 件事（幂等，标记 `r51gen`）：
  A. 58 张卡：每张追加一折 `参数解读`（按 om3_profile.gen6 从参数生成，标明"非作者自述"）；
     原有「原文 / 补充」折页**一概不动**
  B. `window.SC`（289 张照片那份）的 6 行 → 统一换成生成的参数解读（dd/fd/fs/pb 同步）
  C. `__OM3SC__`：每条都带生成的 6 行；**场景适配改成按参数判定**（见 SCENE_RULE），
     只对 7 个天气/光线条件类场景生效（题材类不动，别把好推荐删了）
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
from om3_profile import gen6, profile, wbtxt, sat_word, dir_word, con_word   # noqa: E402

ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r51.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r51.html（= v3.4 源码）')


def grab(var, start=0):
    i = s.index('window.%s' % var, start)
    j = s.index('=', i) + 1
    while s[j] in ' \n':
        j += 1
    oc = s[j]
    cc = {'[': ']', '{': '}'}[oc]
    d = 0
    k = j
    while k < len(s):
        if s[k] == '"':
            k += 1
            while k < len(s):
                if s[k] == chr(92):
                    k += 2
                    continue
                if s[k] == '"':
                    break
                k += 1
        elif s[k] == oc:
            d += 1
        elif s[k] == cc:
            d -= 1
            if d == 0:
                return json.loads(s[j:k + 1]), i, k + 1
        k += 1
    raise SystemExit('抠不出来：' + var)


REC, _, _ = grab('__OM3RECIPES__')
byslug = dict((r['slug'], r) for r in REC)
byname = {}
for r in REC:
    byname.setdefault(r['n'], r)


def ddtxt(it, g):
    """详细描述 = 短描述里那句「图按画面自动归类：…（偶尔会看错）」+ 参数解读（留住分类提示）"""
    pre = (it.get('d') or '').split('｜')[0].strip()
    body = g['feel'] + g['key']
    return (pre + '｜ ' + body) if ('自动归类' in pre and pre not in body) else body


def html6(g, summary, note=''):
    """把 6 行做成卡片里那种折页（结构跟已有 .fold fmine 一致，另外加一句来源说明）"""
    def row(mk, mv, cls=''):
        mv = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', mv)      # **加粗** → <b>
        return ('<div class="row"><span class="mk">%s</span><span class="mv%s">%s</span></div>'
                % (mk, (' ' + cls) if cls else '', mv))
    body = (row('画面感觉', g['feel']) + row('色彩重点', g['key']) + row('影调', g['tone'])
            + row('适合', g['good'], 'good') + row('避开', g['bad'], 'avoid') + row('提示', g['tip'], 'tip'))
    if note:
        body += ('<div class="row"><span class="mk">来源</span><span class="mv">%s</span></div>' % note)
    return ('<details class="fold fgen"><summary>%s <span style="font-weight:400;opacity:.7">（展开看全 6 项）</span>'
            '</summary><div class="foldbody">%s</div></details>') % (summary, body)


# ================================================================ A. 卡片补「参数解读」折页
nA = nA2 = 0
cards = list(re.finditer(r'<div class="card" id="r-([^"]+)">(.*?)(?=<div class="card" id="r-|</details>)', s, re.S))
for m in sorted(cards, key=lambda x: -x.start()):        # 从后往前改，偏移不失效
    slug, html = m.group(1), m.group(2)
    if 'fold fgen' in html:
        continue
    r = byslug.get(slug)
    if not r:
        continue
    g = gen6(r)
    p = profile(r)
    summ = ('参数解读 · %s / %s / %s' % (sat_word(p), dir_word(p), con_word(p)))
    blk = html6(g, summ, note='按色轮（12 色轴）、色调曲线、白平衡偏移**从参数直接推导**，不是作者自述')
    at = m.end(2)
    # 插在「原文 · 作者自述」折页之前（贴着色轮/数值）
    anchor = html.find('<details class="fold')
    if anchor >= 0:
        at = m.start(2) + anchor
        s = s[:at] + blk + s[at:]
    else:
        s = s[:at] + blk + s[at:]
    if 'fold fmine' in html:
        nA2 += 1
    else:
        nA += 1
print('  ✓ A：%d 张卡各加了一折「参数解读」（原有原文/补充折页都没动）' % (nA + nA2))

# ================================================================ B. window.SC（289 张照片那份）6 行统一换新
SCL, lj1, lj2 = grab('SC')
nB = 0
for sc in SCL:
    for it in sc.get('items') or []:
        slug = re.sub(r'^[rk]-', '', it.get('i') or '')
        r = byslug.get(slug)
        if not r:
            continue
        g = gen6(r)
        it['dd'] = ddtxt(it, g)
        it['fs'] = '参数解读 · %s' % (it.get('t') or '')
        it['fd'] = html6(g, '参数解读（按参数推导）')
        it['pb'] = ''
        nB += 1
newlb = 'window.SC = ' + json.dumps(SCL, ensure_ascii=False, separators=(',', ':'))
s = s[:s.index('window.SC')] + newlb + s[lj2:]
print('  ✓ B：window.SC 的 %d 条照片说明统一换成参数解读' % nB)

# ================================================================ C. __OM3SC__：按参数判定场景适配
SC, scj1, scj2 = grab('__OM3SC__')


def scene_ok(label, r):
    """场景适配：**只看参数**（天气/光线条件类才判；题材类返回 True = 不动）"""
    p = profile(r)
    sw, d = sat_word(p), (p['eff_w'] - p['eff_c'])
    if label == '雾与阴天':
        # 灰平光：低饱和会"更没劲"；要中性以上的饱和 + 不硬压
        return not (sw in ('清淡', '寡淡')) and con_word(p) != '硬朗'
    if label == '雨天':
        return sw not in ('清淡', '寡淡') and d <= 8
    if label == '雪景':
        # 雪本身冷：别再往上加暖；反差别太硬（雪容易爆）
        return d <= 4 and con_word(p) != '硬朗'
    if label == '日落晚霞':
        # 要暖 / 要品红，别把暖意抵消
        return d >= -4 and (p['v'][3] >= 0 or d >= 4)
    if label == '夜景霓虹':
        return sw not in ('清淡', '寡淡') or con_word(p) == '硬朗'
    if label == '室内暖光':
        # 钨丝灯：暖上加暖会黄脸 —— 但**只排除明显偏暖**（d>=8），
        # 温和偏暖/中性的仍然留（它们靠色环和曲线在暖光里也能站住），不然这个场景会被抽空
        return d < 8
    if label == '逆光大光比':
        # 大光比：要高光压得住（平顺/高光负）
        return p['hi'] <= -1 or p['sh'] >= 1 or con_word(p) == '平顺'   # 高光压得住 / 暗部提得起
    return True


ndd = nrm = 0
for sc in SC:
    lab = sc.get('label')
    keep = []
    for it in sc.get('items') or []:
        slug = re.sub(r'^[rk]-', '', it.get('i') or '')
        r = byslug.get(slug)
        if not r:
            keep.append(it)
            continue
        g = gen6(r)
        it['dd'] = ddtxt(it, g)
        it['fd'] = html6(g, '参数解读（按参数推导）')
        it['fs'] = '参数解读 · %s' % (it.get('t') or '')
        it['pb'] = ''
        ndd += 1
        if not scene_ok(lab, r):
            nrm += 1
            continue
        keep.append(it)
    sc['items'] = keep
newsc = 'window.__OM3SC__ = ' + json.dumps(SC, ensure_ascii=False, separators=(',', ':'))
s = s[:s.index('window.__OM3SC__')] + newsc + s[scj2:]
print('  ✓ C：场景条目 %d 条补/换参数解读；按参数判定移除 %d 条（剩 %d 条）'
      % (ndd, nrm, sum(len(x['items']) for x in SC)))

# CSS：参数解读折页的标题色（跟作者补充区分开）
if '.fold.fgen' not in s:
    s = s.replace('/* r50：白平衡偏移小标签',
                  '/* r51：参数解读折页（按参数推导，跟作者自述区分） */\n'
                  '.fold.fgen>summary{color:#8fd8c2}\n'
                  '.fold.fgen{border-left:2px solid #2b6b7a;padding-left:8px}\n'
                  '/* r50：白平衡偏移小标签', 1)
    print('  ✓ CSS：参数解读折页样式')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))
