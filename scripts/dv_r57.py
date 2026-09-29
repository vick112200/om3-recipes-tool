# -*- coding: utf-8 -*-
"""第 57 轮验收：婚礼/儿童退出场景对比 + 建筑几何人工白名单 + 收紧期望表 + 风格搜索。

对应关系（用户两句）：
  ① 建筑几何去掉"卧室"那张（实测是表上 #13）→ 8 张人工白名单，图上写明"人工挑选"
  ② 婚礼/儿童没有实拍 → 不出现在场景对比；改成**搜索能搜到**（儿童/小孩/温馨/聚会/结婚…）
跑法：python scripts/dv_r57.py
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


src = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()
OLD = io.open(os.path.join(ROOT, 'app', 'base.before_r57.html'), encoding='utf-8').read()


def grab(t, m):
    i = t.rindex(m) + len(m)
    while t[i] in ' \n':
        i += 1
    return json.JSONDecoder().raw_decode(t, i)[0]


SC = grab(src, 'window.__OM3SC__ =')
SCN = grab(src, 'window.__OM3SCENES__ =')
PH = grab(src, 'window.__OM3PHOTOS__ =')
PT = grab(src, 'window.__OM3PHOTOTAGS__ =')
IDX = grab(src, 'var IDX=')
OLD_SC = grab(OLD, 'window.__OM3SC__ =')
WL = json.load(io.open(os.path.join(ROOT, 'scripts', '_r56_scenepick.json'), encoding='utf-8'))

print('=== ① 婚礼 / 儿童 退出场景对比 ===')
A(len(SC) == 18 and len(SCN) == 18, '__OM3SC__ / __OM3SCENES__ 都是 18 个场景（实得 %d / %d）' % (len(SC), len(SCN)))
A(all(x['k'] not in ('wedding', 'kids') for x in SC), 'SC 里没有 wedding / kids')
A(all(x['k'] not in ('wedding', 'kids') for x in SCN), 'SCENES 里没有 wedding / kids')
A('s:wedding' not in src and 's:kids' not in src, '下拉里没有 s:wedding / s:kids')
A('按场景挑 · 18 个场景' in src, '下拉分组文案已改成 18 个场景')
# 第 57 轮踩过：改文案的正则把 optgroup 收尾的 `">` 吃了 → 浏览器把第一个选项（s:portrait）吞掉、
# 场景切换整个失效（dv_scene39 的运行时断言抓到的）。这里把结构钉死。
A(src.count('<optgroup') == src.count('</optgroup>'), 'optgroup 开闭配对（%d / %d）'
  % (src.count('<optgroup'), src.count('</optgroup>')))
A(re.search(r'<optgroup label="按场景挑 · 18 个场景（图按画面归类）">', src) is not None,
  '「按场景挑」的 optgroup 标签结构完好（收尾引号没被吃掉）')
A('<option value="s:portrait">' in src and '<option value="s:mono">' in src,
  '首尾两个场景选项都在（s:portrait / s:mono）')
A(all(x['k'] in [y['k'] for y in SC] for x in SCN), 'SCENES 与 SC 的场景集合完全一致')
A(len(SC) == len(OLD_SC) - 2, '只是少了 2 个场景（%d → %d，没有误删别的）' % (len(OLD_SC), len(SC)))

print('\n=== ② 建筑几何：人工白名单 8 张 + 写明"人工挑选" ===')
arch = next(x for x in SC if x['k'] == 'arch')
wla = set(WL.get('arch', []))
man = [it for it in arch['items'] if (it.get('d') or '').startswith('人工挑选')]
A(len(wla) == 8 and len(man) == 8, '白名单 8 张、生效 8 条（实得 %d / %d）' % (len(wla), len(man)))
A({it['f'] for it in man} == wla, '这 8 条用的正是白名单里的图')
A(all(('「建筑几何」' in it['d']) and ('我逐张看过' in it['d']) for it in man),
  '说明里写明了「人工挑选 · 建筑几何 · 我逐张看过」（人工挑的就说人工挑的）')
A('peter-turner_sydney-grain__s03.jpg' in wla and 'james-bloomer_kodachrome-64-v0__s01.jpg' in wla,
  '白名单里含"黑白木纹台阶"和"住宅+泳池"两张')
_nb = [f for f in wla if 'om-3-x-monochrome' in f or 'fuji-eterna' in f]
A(not _nb, '用户点名去掉的"室内/卧室"那张（#13 = X-Monochrome 室内）不在白名单里')
A(all((it.get('d') or '').startswith('人工挑选') for it in arch['items'][:8]), '人工挑选的排在场景最前面')
rest = arch['items'][8:]
A(all((it.get('d') or '').startswith('本条没有对「建筑几何」的实拍') and '__cmp__' in it['f'] for it in rest),
  '其余 %d 条明说"没有对题实拍"并退到站点统一对比图（不拿泳池/吉他冒充建筑）' % len(rest))

print('\n=== ③ 收紧期望表：不再有"日常"凑命中 ===')
WANT = {'portrait': ['人像特写'], 'street': ['人群'], 'travel': ['人群'], 'night': ['夜景'], 'indoor': ['夜景'],
        'forest': ['绿意'], 'autumn': ['绿意'], 'flower': ['花卉'], 'snow': ['高调'], 'skywater': ['天空水面'],
        'arch': ['建筑几何'], 'still': [], 'sunset': [], 'backlight': [], 'mist': [], 'food': [], 'film': [], 'mono': []}
_bad = []
for sc in SC:
    w = WANT.get(sc['k'])
    for it in sc['items']:
        if not w:
            if not (it.get('d') or '').startswith('本场景不挑题材'):
                _bad.append((sc['k'], it['n'], (it.get('d') or '')[:18]))
A(not _bad, '没有检测依据的场景（食物/静物/日落/逆光/雾/胶片/黑白）一律说"本场景不挑题材"（异常 %s）' % (_bad[:3] or 0))
_nopick = [sc['k'] for sc in SC if not WANT.get(sc['k'])
           and not all((it.get('d') or '').startswith('本场景不挑题材') for it in sc['items'])]
A(not _nopick, '这些场景里**每一条**都不再声称归类（%s）' % (_nopick or 0))
A(sum(1 for sc in SC for it in sc['items'] if (it.get('d') or '').startswith('本场景不挑题材')) >= 60,
  '不挑题材的条目有 %d 条（原来这些是拿"日常"凑命中）'
  % sum(1 for sc in SC for it in sc['items'] if (it.get('d') or '').startswith('本场景不挑题材')))
_pc = [(sc['k'], it['n']) for sc in SC for it in sc['items']
       if (it.get('d') or '').startswith('本场景不挑题材 · 显示作者样片') and '__cmp__' in it['f']]
A(not _pc, '说"作者样片"的确实给的是作者样片（不符 %s）' % (_pc[:3] or 0))

print('\n=== ④ 四态说明自洽 ===')
_bad = []
for sc in SC:
    w = WANT.get(sc['k'], [])
    for it in sc['items']:
        f, d = it['f'], it.get('d') or ''
        tags = PT.get(f) or []
        if d.startswith('人工挑选：'):
            if f not in set(WL.get(sc['k'], [])):
                _bad.append((sc['k'], it['n'], '人工态但不在白名单'))
        elif d.startswith('图按画面自动归类：'):
            got = d.split('（自动判断', 1)[0][len('图按画面自动归类：'):]
            if sorted(got.split(' / ')) != sorted(tags) or not (w and any(t in w for t in tags)):
                _bad.append((sc['k'], it['n'], '声称归类但对不上'))
        elif d.startswith('本条没有对「%s」的实拍' % sc['label']):
            if w and any(t in w for t in tags):
                _bad.append((sc['k'], it['n'], '命中了却写兜底'))
        elif d.startswith('本场景不挑题材'):
            if w:
                _bad.append((sc['k'], it['n'], '有期望却说"不挑题材"'))
        else:
            _bad.append((sc['k'], it['n'], '没有已知前缀'))
A(not _bad, '每条说明与图、与场景口径三方自洽（问题 %d：%s）' % (len(_bad), _bad[:2] or 0))

print('\n=== ⑤ 风格 / 题材搜索（婚礼、儿童不靠图，靠搜索） ===')
syn = re.search(r'var SYN=\{(.*?)\n \};', src, re.S)
tbl = {}
for m in re.finditer(r"'([^']+)':\[(.*?)\]", syn.group(1)):
    tbl[m.group(1)] = [x.strip().strip("'") for x in m.group(2).split(',') if x.strip()]


def sim(q):
    qs = [q] + tbl.get(q, [])
    return [it['n'] for it in IDX
            if any(x.lower() in ' '.join(str(it.get(f) or '') for f in ('n', 'a', 't', 'g', 'f')).lower()
                   for x in qs)]


for q, least in (('儿童', 10), ('小孩', 10), ('亲子', 10), ('婚礼', 10), ('聚会', 10),
                 ('结婚', 10), ('温馨', 20), ('胶片', 20), ('复古', 20), ('夜景', 5)):
    r = sim(q)
    A(len(r) >= least, '搜「%s」→ %d 条（≥%d）' % (q, len(r), least))
for k in ('儿童', '小孩', '温馨', '聚会', '结婚'):
    A(k in tbl, 'SYN 里补了「%s」这组别名' % k)

print('\n=== ⑥ 只动该动的 ===')
print('\\n=== ⑤b 搜索面板的「常用词」chip ===')
_chip = re.findall(r'id="toc2chips"[\s\S]*?</div>', src)[0]
for q in ('婚礼', '儿童', '温馨', '胶片'):
    A('data-q="%s"' % q in _chip, '搜索面板有「%s」chip（一键点）' % q)
A('人像、婚礼、儿童、温馨、Portra' in src, '搜索框提示词里也带上了风格词')
A(chr(1) not in src and chr(2) not in src, '页面里没混进控制字符（踩过：替换串的 反斜杠1 被当成 0x01）')

A(len(re.findall(r'<div class="card" id="r-', src)) == 77, '卡片仍是 77 张（本轮不碰卡片）')
A(src.count('<option value="s:') == 18, '按场景挑的 option 是 18 个（实得 %d）' % src.count('<option value="s:'))
A(grab(src, 'window.__OM3RECIPES__=') == grab(OLD, 'window.__OM3RECIPES__='), '配方数据一个字没动')
A(grab(src, 'window.__OM3PHOTOTAGS__ =') == grab(OLD, 'window.__OM3PHOTOTAGS__ ='), '图片标签一个字没动')

print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
