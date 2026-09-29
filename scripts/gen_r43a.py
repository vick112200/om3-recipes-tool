# -*- coding: utf-8 -*-
"""第 43 轮 · 步骤 A：改名 + 搜索同步 + 「配方合集」去掉档位（用户 2026-09-25）
 1. 页签名：原版方案 → **配方合集**；优化版 → **档位推荐**（底栏、顶栏代理、pane 标题、目录标题都改）
 2. 搜索同步：两个搜索框的 placeholder / 面板标题 / 结果标签（IDX 的 sl「优化版 C1 · 槽 1」→「档位推荐 · C1 槽 1」）
 3. 去档位（配方合集）：
    · 删掉 `#plan`「推荐方案总表（C1–C5 共 18 个）」（这就是"预设档位"的总表）
    · 5 个 `#mode-Cn` 分区标题从「C1 档 · 白平衡偏移 A0 G0（不偏移）」→「**不偏移 · A0 G0**」（只留白平衡签名，不再有 C 档字样）
    · 卡片右上角徽标「C4 · 槽 3」→ 换成该配方的**白平衡签名**（A+2 G+1 这种）；有作者的卡片仍显示作者
    · 「备选池：同偏移可替换的配方」→「**更多配方（可替换）**」
 注：**不删** `#mode-Cn` 的 id（目录里有 `#mode-C1` 链接），只改可见文字，避免断链。
"""
import io, json, re, sys
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()
DEC = json.JSONDecoder()
n = 0


def rep(old, new, must=True, label=''):
    global s, n
    if old not in s:
        if must:
            print('  ⚠ 没找到：%s' % (label or old[:56]))
        return
    s = s.replace(old, new, 1)
    n += 1


# ---------------- 1) 页签名 ----------------
print('=== ① 改名 ===')
rep('<button type="button" data-p="A" class="on">原版方案</button>',
    '<button type="button" data-p="A" class="on">配方合集</button>', label='底栏 原版方案')
rep('<button type="button" data-p="B">优化版</button>', '<button type="button" data-p="B">档位推荐</button>', label='底栏 优化版')
rep('data-p="A" class="on" id="tabBuiltin">内置配方<', 'data-p="A" class="on" id="tabBuiltin">配方合集<', label='顶栏 内置配方')
rep('<button type="button" data-p="B" id="tabB" style="display:none">优化版</button>',
    '<button type="button" data-p="B" id="tabB" style="display:none">档位推荐</button>', label='顶栏代理')
rep('<h1>优化版方案</h1>', '<h1>档位推荐</h1>', label='paneB 标题')
rep('<div class="t2head">搜索 / 目录</div>', '<div class="t2head">档位推荐 · 搜索 / 目录</div>', label='toc2 标题')
rep('>只在本站', '>只在本站', must=False)          # 占位（已无）

# 目录里的「原版方案」字样 → 配方合集
rep('<div class="tgh">推荐档位 C1–C5</div>', '<div class="tgh">按白平衡签名找</div>', label='toc 分组标题')
for a, b in [('在「原版方案」页签', '在「配方合集」页签'), ('「原版方案」页签里', '「配方合集」页签里'),
             ('原版方案 · 看卡片', '配方合集 · 看卡片'), ('优化版 · ', '档位推荐 · '),
             ('优化版方案', '档位推荐'), ('原版方案', '配方合集'), ('优化版', '档位推荐')]:
    if a in s:
        cnt = s.count(a)
        s = s.replace(a, b)
        n += 1
        print('    「%s」→「%s」（%d 处）' % (a, b, cnt))

# ---------------- 2) 搜索同步 ----------------
print('=== ② 搜索同步 ===')
rep('placeholder="只在原版方案里搜：配方名 / 作者 / 场景，如 人像、夜景、Portra…"',
    'placeholder="只在配方合集里搜：配方名 / 作者 / 白平衡 / 场景，如 人像、A2、夜景、Portra…"', label='搜索框 A')
rep('placeholder="只在优化版里搜：档位 / 槽位 / 配方名 / 作者，如 C1、夜景、Portra…"',
    'placeholder="只在档位推荐里搜：档位 / 槽位 / 配方名 / 作者，如 C1、夜景、Portra…"', label='搜索框 B')
# 结果标签：IDX 的 sl「优化版 C1 · 槽 1」→「档位推荐 · C1 槽 1」
idx = re.search(r'var IDX=', s)
I, e = DEC.raw_decode(s, idx.start() + len('var IDX='))
k = 0
for x in I:
    sl = str(x.get('sl') or '')
    if '优化版' in sl:
        x['sl'] = sl.replace('优化版 ', '档位推荐 · ').replace('优化版', '档位推荐')
        k += 1
print('    IDX 槽位标签改 %d 条' % k)
s = s[:idx.start() + len('var IDX=')] + json.dumps(I, ensure_ascii=False, separators=(',', ':')) + s[e:]
n += 1

# ---------------- 3) 去档位 ----------------
print('=== ③ 配方合集去档位 ===')
# 删 #plan 整块（到 #mode-C1 之前）
i = s.find('<details class="sec" id="plan"')
j = s.find('<details class="sec" id="mode-C1"')
if i > 0 and j > i:
    print('    删除 #plan 推荐方案总表（%d 字符）' % (j - i))
    s = s[:i] + s[j:]
    n += 1
else:
    print('    ⚠ #plan 定位失败 i=%d j=%d' % (i, j))
# 5 个分区标题
titles = [('C1 档 &nbsp;·&nbsp; 白平衡偏移 A0 G0（不偏移）', '不偏移 · A0 G0'),
          ('C2 档 &nbsp;·&nbsp; 白平衡偏移 A2 G1（琥珀 +2、绿 +1）', 'A2 G1（琥珀 +2、绿 +1）'),
          ('C3 档 &nbsp;·&nbsp; 白平衡偏移 A1 G1（琥珀 +1、绿 +1）', 'A1 G1（琥珀 +1、绿 +1）'),
          ('C4 档 &nbsp;·&nbsp; 白平衡偏移 A4 M1（琥珀 +4、品红 +1）', 'A4 M1（琥珀 +4、品红 +1）'),
          ('C5 档 &nbsp;·&nbsp; 白平衡偏移 A3 G1（琥珀 +3、绿 +1）', 'A3 G1（琥珀 +3、绿 +1）')]
for a, b in titles:
    rep('<span class="sh">%s</span>' % a, '<span class="sh">%s</span>' % b, label='分区标题 %s' % b)
rep('<span class="sh">备选池：同偏移可替换的配方</span>', '<span class="sh">更多配方（可替换）</span>', label='备选池标题')
rep('<span class="sh">固定色温配方（21 个，需单独占档）</span>', '<span class="sh">固定色温配方（21 个）</span>', label='固定色温标题')

# 卡片徽标「C4 · 槽 3」→ 白平衡签名
m = re.search(r'window\.__OM3RECIPES__=', s)
REC, e2 = DEC.raw_decode(s, m.start() + len('window.__OM3RECIPES__='))
WBN = {}
for r in REC:
    a = r.get('wba') or 0
    g = r.get('wbg') or 0
    left = ('A+%d' % a) if a > 0 else (('B%d' % abs(a)) if a < 0 else 'A0')
    right = ('G+%d' % g) if g > 0 else (('M%d' % abs(g)) if g < 0 else 'G0')
    WBN['r-' + r['slug']] = '%s %s' % (left, right)
cards = re.findall(r'<div class="card" id="(r-[^"]+)">(.*?)<div class="cbody">', s, re.S)
k = 0
for cid, head in cards:
    mm = re.search(r'<span class="slot">(C\d+ · 槽 \d+)</span>', head)
    if mm and cid in WBN:
        old = '<div class="chd"><span class="cname">'
        # 替换这一张卡里的徽标
        i0 = s.find('id="%s"' % cid)
        seg = s[i0:i0 + 400]
        s = s[:i0] + seg.replace(mm.group(0), '<span class="slot">%s</span>' % WBN[cid], 1) + s[i0 + 400:]
        k += 1
print('    卡片徽标换成白平衡签名：%d 张' % k)
n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n✅ 步骤 A 完成（%d 处）' % n)
for kw in ('原版方案', '优化版方案', 'C1 档', 'C2 档', 'C3 档', 'C4 档', 'C5 档', '槽 1'):
    print('   %-10s 残留 %d 处' % (kw, s.count(kw)))
