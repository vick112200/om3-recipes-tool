# -*- coding: utf-8 -*-
"""第 57 轮生成器（幂等）：按用户两条决定收尾场景对比。

用户原话：
  ①「建筑几何_我的建议：建议18是一个卧室，其他没问题。」
     → 实测：表上 **#13** 才是卧室（室内黑白），#18 是红顶房子 → 去掉室内那张，保留另外 8 张
  ②「婚礼和儿童这种，没有图就不要按照图片了，可以不出现在场景对比中。
     按照婚礼和儿童适合哪些风格，比如胶片风格、比如温馨的风格，按照风格，
     在配方合集中能够在搜索中点相应场景搜索出来推荐的就行了。」
     → 把「婚礼聚会 / 儿童亲子」从场景对比里**删掉**（20 → 18 个场景），
        改成**搜索能搜到**（补同义词：儿童/小孩/温馨/聚会/结婚…）

顺带修（第 56 轮我自己认下的错）：**"日常"凑命中** ——
  食物咖啡 29 条里 25 条的"命中"其实是兜底标签「日常」凑的，等于没挑。
  本轮把期望表收紧成"只有真检测/真统计支持的口径"，没有口径的场景改成
  **显示作者样片 + 明说"本场景不挑题材"**（不再假装命中）。

四态说明（每条场景条目的 `d`/`dd` 前缀）：
  人工挑选：这张是「建筑几何」的实拍（我逐张看过）
  图按画面自动归类：<该图全部标签>（自动判断，偶尔会看错）
  本条没有对「<场景>」的实拍 · 显示站点统一对比图
  本条没有对「<场景>」的实拍 · 显示作者样片（题材未标注）
  本场景不挑题材 · 显示作者样片（这类画面没做检测）

用法：python scripts/gen_r57.py [--check]
"""
import io
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
BASE = os.path.join(ROOT, 'app', 'base.html')
PICK_JSON = os.path.join(HERE, '_r56_scenepick.json')

import gen_r55 as G55          # noqa: E402  复用 json_span / dump

# 只有"真检测（人脸）/真统计（色彩）"支持的期望才留；空 = 本场景不挑题材
WANT = {
    'portrait': ['人像特写'],
    'street': ['人群'], 'travel': ['人群'],
    'night': ['夜景'], 'indoor': ['夜景'],
    'forest': ['绿意'], 'autumn': ['绿意'],
    'flower': ['花卉'],
    'snow': ['高调'], 'skywater': ['天空水面'],
    # 建筑几何：没有"建筑"这种画面标签 → 用一个永远不会被命中的哨兵，
    #   效果 = 只有人工白名单那几张"命中"，其余明说"没有对题实拍"
    'arch': ['建筑几何'],
    # 这些场景**没有任何检测依据** → 不挑题材，显示作者样片并说明
    'still': [], 'sunset': [], 'backlight': [], 'mist': [], 'food': [], 'film': [], 'mono': [],
}
DROP = ['wedding', 'kids']          # 没图就不放在场景对比里（用户决定）
SYN_ADD = {
    '儿童': ['亲子', '小孩', '孩子'],
    '小孩': ['儿童', '亲子', '孩子'],
    '亲子': ['儿童', '小孩', '孩子'],
    '温馨': ['家居', '日常', '柔和', '暖调'],
    '聚会': ['婚礼', '宴会', '举杯', '人群'],
    '结婚': ['婚礼', '宴会'],
    '婚礼': ['婚礼', '聚会', '宴会'],          # 原来就能搜到（适合文本里有"婚礼"），补上别名更稳
    '胶片': ['复古胶片味', '胶片', '怀旧'],
}
P_人工 = '人工挑选：这张是「%s」的实拍（我逐张看过）'
P_命中 = '图按画面自动归类：%s（自动判断，偶尔会看错）'
P_兜底图 = '本条没有对「%s」的实拍 · 显示站点统一对比图'
P_兜底人 = '本条没有对「%s」的实拍 · 显示作者样片（题材未标注）'
P_不挑人 = '本场景不挑题材 · 显示作者样片（这类画面没做检测）'
P_不挑图 = '本场景不挑题材 · 显示站点统一对比图'


def blob(s, marker):
    j, k = G55.json_span(s, marker)
    return json.loads(s[j:k])


def set_blob(s, marker, obj):
    j, k = G55.json_span(s, marker)
    return s[:j] + G55.dump(obj) + s[k:]


PRE_RE = re.compile(
    r'^(图按画面自动归类：[^｜|]*?（自动判断，偶尔会看错）'
    r'|本条没有对「[^」]*」的实拍 · (?:显示站点统一对比图|显示作者样片（题材未标注）)'
    r'|本场景不挑题材 · (?:显示作者样片（这类画面没做检测）|显示站点统一对比图)'
    r'|人工挑选：这张是「[^」]*」的实拍（我逐张看过）)\s*(?:｜\s*)?')


def strip_prefix(txt):
    return PRE_RE.sub('', txt)


def join(pre, rest):
    rest = strip_prefix(rest).strip()
    return pre + ('｜ ' + rest if rest else '')


def pick(slug, want, PH, PT):
    files = PH.get(slug) or []
    if not files:
        return None, ''
    if not want:
        return files[0], 'plain'
    hit = lambda f: any(t in want for t in (PT.get(f) or []))       # noqa: E731
    for is_author in (True, False):
        for f in files:
            if ('__cmp__' not in f) == is_author and hit(f):
                return f, 'hit'
    for is_cmp in (True, False):
        for f in files:
            if ('__cmp__' in f) == is_cmp:
                return f, ('cmp' if is_cmp else 'author')
    return None, ''


def main():
    check = '--check' in sys.argv
    s = io.open(BASE, encoding='utf-8').read()
    SC = blob(s, 'window.__OM3SC__ =')
    SCN = blob(s, 'window.__OM3SCENES__ =')
    PH = blob(s, 'window.__OM3PHOTOS__ =')
    PT = blob(s, 'window.__OM3PHOTOTAGS__ =')
    WL = json.load(io.open(PICK_JSON, encoding='utf-8')) if os.path.exists(PICK_JSON) else {}

    # ---------- 1) 删掉"没图"的两个场景 ----------
    n_before = len(SC)
    SC = [x for x in SC if x['k'] not in DROP]
    SCN = [x for x in SCN if x['k'] not in DROP]
    print('1. 场景 %d → %d（删掉 %s）' % (n_before, len(SC), '、'.join(DROP)))

    # ---------- 2) 重挑 + 四态说明 ----------
    rep = Counter()
    for sc in SC:
        want = WANT.get(sc['k'], [])
        wl = set(WL.get(sc['k'], []))
        rows = []
        for it in sc['items']:
            slug = re.sub(r'^[rk]-', '', it['i'])
            files = PH.get(slug) or []
            man = next((f for f in files if f in wl), '')
            if man:
                f, state = man, '人工'
            else:
                f, state = pick(slug, want, PH, PT)
            if not f:
                rows.append((it, False))
                continue
            it['f'] = f
            pre = (P_人工 % sc['label'] if state == '人工'
                   else P_命中 % ' / '.join(PT.get(f) or []) if state == 'hit'
                   else P_兜底图 % sc['label'] if state == 'cmp'
                   else P_兜底人 % sc['label'] if state == 'author'
                   else (P_不挑图 if '__cmp__' in f else P_不挑人))
            it['d'] = join(pre, it.get('d') or '')
            it['dd'] = join(pre, it.get('dd') or '')
            rep[state] += 1
            rows.append((it, state in ('人工', 'hit')))
        sc['items'] = [r[0] for r in rows if r[1]] + [r[0] for r in rows if not r[1]]
    s = set_blob(s, 'window.__OM3SC__ =', SC)
    s = set_blob(s, 'window.__OM3SCENES__ =', SCN)
    print('2. 重挑：人工 %d 条 / 命中 %d 条 / 兜底对比图 %d 条 / 兜底作者样片 %d 条 / 不挑题材 %d 条'
          % (rep['人工'], rep['hit'], rep['cmp'], rep['author'], rep['plain']))

    # ---------- 3) 下拉里删掉那两项 + 改场景数文案 ----------
    for k in DROP:
        s, n = re.subn(r'<option value="s:%s">[^<]*</option>' % k, '', s)
        assert n <= 1, '下拉里 s:%s 出现 %d 次（异常）' % (k, n)      # 重跑时已经是 0 次
    # ⚠ [^<]* 会把 optgroup 收尾的 `">` 一起吃掉（第一版就这么写的 → 标签属性把后面的 option 全吞了，
    #   第一个场景选项"s:portrait"在浏览器里直接消失、整个场景切换失效）。用前瞻钉住收尾引号。
    s, n = re.subn(r'按场景挑 · \d+ 个场景[（，]图按画面(?:自动)?归类）?(?=">)',
                   '按场景挑 · %d 个场景（图按画面归类）' % len(SC), s)
    assert n >= 1, '没找到"按场景挑 · N 个场景"文案'
    # 结构自查：optgroup 必须配对、场景选项必须齐全（上面那个坑就是这条抓的）
    assert s.count('<optgroup') == s.count('</optgroup>'), 'optgroup 没配对'
    assert len(re.findall(r'<option value="s:[^"]+">', s)) == len(SC), '场景选项数不对'
    for _k in ('portrait', 'arch', 'food'):
        assert '<option value="s:%s">' % _k in s, '缺少场景选项 s:%s' % _k
    print('3. 下拉已删婚礼/儿童；文案改为「按场景挑 · %d 个场景（图按画面归类）」' % len(SC))

    # ---------- 4) 搜索同义词（风格/人物题材照样能搜到） ----------
    i = s.index('var SYN={')
    add = ''.join("   '%s':[%s],\n" % (k, ','.join("'%s'" % x for x in v))
                  for k, v in SYN_ADD.items() if ("'%s':" % k) not in s[i:i + 4000])
    if add:
        s = s[:i + len('var SYN={')] + '\n' + add + s[i + len('var SYN={'):]
    print('4. 同义词补了 %d 组（儿童/小孩/亲子/温馨/聚会/结婚/胶片）' % len(SYN_ADD))

    # ---------- 4b) 搜索面板加"常用词"：婚礼 / 儿童 / 温馨 / 胶片 一键点 ----------
    # 用户要求：婚礼、儿童这种"没有实拍"的场景，直接在搜索里按风格找
    i = s.index('id="toc2chips"')
    j = s.index('</div>', i)
    seg = s[i:j]
    add_chips = ''.join('<button type="button" data-q="%s">%s</button>' % (q, q)
                        for q in ('婚礼', '儿童', '温馨', '胶片') if ('data-q="%s"' % q) not in seg)
    if add_chips:
        s = s[:j] + add_chips + s[j:]
    # 占位符提示顺带补上风格词（幂等：只在还没补过时替换）
    if '人像、婚礼、儿童、温馨、Portra' not in s:
        s = s.replace('人像、夜景、Portra', '人像、婚礼、儿童、温馨、Portra')
    n_chip = sum(1 for q in ('婚礼', '儿童', '温馨', '胶片') if ('data-q="%s"' % q) in s)
    print('4b. 搜索常用词：4 个风格 chip 就位（实测 %d 个）' % n_chip)
    for q in ('婚礼', '儿童', '温馨', '胶片'):
        assert ('data-q="%s"' % q) in s, 'chip 没进去：%s' % q

    # ---------- 5) 收尾自查 ----------
    SC2 = blob(s, 'window.__OM3SC__ =')
    bad = []
    for sc in SC2:
        for it in sc['items']:
            d = it.get('d') or ''
            if not d.startswith(('人工挑选：', '图按画面自动归类：', '本条没有对「', '本场景不挑题材')):
                bad.append((sc['k'], it['n'], d[:20]))
    assert not bad, '有条目说明没有前缀：%s' % bad[:3]
    ks = [x['k'] for x in SC2]
    assert 'wedding' not in ks and 'kids' not in ks, '婚礼/儿童还在 SC 里'
    assert len(SC2) == 18, '场景数应为 18，实得 %d' % len(SC2)
    print('5. 自查：18 个场景、无婚礼/儿童、每条说明都有前缀 ✅')
    if check:
        print('（--check：不写盘）')
        return 0
    io.open(BASE, 'w', encoding='utf-8', newline='').write(s)
    print('已写入 app/base.html')
    return 0


if __name__ == '__main__':
    sys.exit(main())
