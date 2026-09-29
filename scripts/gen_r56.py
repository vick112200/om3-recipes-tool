# -*- coding: utf-8 -*-
"""第 56 轮生成器（幂等）：场景挑图「人像可信化」+ 重名配方区分。

起因（用户两句话）：
  ① 「场景对比是怎么算出来的？说『图按画面自动归类』，但人像场景基本上没有人像的照片」
  ② 「很多名字一样的配方，比如 Portra 400，这种也改个名做个区分」
用户给的口子：「场景对比实在不行就不用作者原图，用网站的对比图像也行」

根因（已拼图钉死）：
  · 「人像」标签只是**色彩统计**（暖棕像素 > 5%）→ 木头/吉他/泳池/暖石墙全中；
  · 页面里那套按场景挑图的 JS 与 SEL_TAGS（第 39 轮）**早就是死代码**（当前 base.html 里已无那套函数），
    真正显示的是数据侧 `__OM3SC__[].items[].f`。

本脚本做 5 件事（全部按结构定位，重跑 md5 不变）：
  A. 跑 `gen_phototags`：标签改口径（人像→暖肤调）+ 用 YuNet 人脸检测给 人像特写/人脸/人群
  B. 页面 `SEL_TAGS` 表同步成新口径（并注明它已是死代码，只作说明用）
  C. `__OM3SC__` 逐条重挑 `f`：命中的作者图 → 命中的对比图 → **没命中就用站点统一对比图**（用户同意）→ 作者第一张；
     说明文字改成三态说真话；每个场景里"命中"的条目排前面
  D. 重名配方加作者区分（只改归一化后同名的；"冲印版/早期版"这类已有区分词的保持不动）
  E. 侧边目录按 #pool 重建（复用 r55 的 sync_toc）

用法：
  python scripts/gen_r56.py            # 正式改 app/base.html
  python scripts/gen_r56.py --check    # 只看报告，不写盘
"""
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
BASE = os.path.join(ROOT, 'app', 'base.html')

import gen_r55 as G55          # noqa: E402  复用 json_span / dump / sync_toc / hero_map / tag_block_end
import gen_phototags           # noqa: E402  标签的唯一写者

# 场景 → 期望的画面标签（与页面 SEL_TAGS 同口径；空 = 不谈题材，用作者第一张）
WANT = {
    'portrait': ['人像特写'], 'wedding': ['人像特写'], 'kids': ['人像特写'], 'mono': [],
    'flower': ['花卉'], 'sunset': ['花卉'], 'forest': ['绿意'], 'autumn': ['绿意'],
    'night': ['夜景'], 'skywater': ['天空水面'], 'snow': ['高调'], 'mist': ['雾'],
    'arch': ['中性白'], 'still': ['中性白'], 'street': ['人群'], 'travel': ['人群'],
    'backlight': ['人群'], 'rain': ['日常'], 'food': ['日常'], 'indoor': ['夜景'], 'film': ['日常'],
}
HIT_PREFIX = '图按画面自动归类：%s（自动判断，偶尔会看错）'
MISS_CMP = '本条没有对「%s」的实拍 · 显示站点统一对比图'
MISS_AUTH = '本条没有对「%s」的实拍 · 显示作者样片（题材未标注）'
OLD_PREFIX = ('图按画面自动归类：', '本条没有对「')


def blob(s, marker):
    j, k = G55.json_span(s, marker)
    return json.loads(s[j:k])


def set_blob(s, marker, obj):
    j, k = G55.json_span(s, marker)
    return s[:j] + G55.dump(obj) + s[k:]


PRE_RE = re.compile(
    r'^(图按画面自动归类：[^｜|]*?（自动判断，偶尔会看错）'
    r'|本条没有对「[^」]*」的实拍 · (?:显示站点统一对比图|显示作者样片（题材未标注）))\s*(?:｜\s*)?')


def strip_prefix(txt):
    """剥掉旧前缀。⚠ 有两种形态：`前缀｜正文` 和 `整串就只有前缀`（第 55 轮有几个条目就是这样，
    第一版按 ｜ 切分 → 那几条剥不掉，新前缀被叠在旧前缀前面）。"""
    return PRE_RE.sub('', txt)


# ---------------------------------------------------------------- C：重挑
def pick(slug, want, PH, PT):
    """返回 (图, 状态)。状态：hit 命中 / cmp 没命中但用统一对比图 / author 没命中且只能给作者样片。"""
    files = PH.get(slug) or []
    if not files:
        return None, ''
    if not want:
        return files[0], 'plain'
    hit = lambda f: any(t in want for t in (PT.get(f) or []))       # noqa: E731
    for is_author in (True, False):          # ① 命中的作者图 ② 命中的对比图
        for f in files:
            if ('__cmp__' not in f) == is_author and hit(f):
                return f, 'hit'
    for is_cmp in (True, False):             # ③ 没命中 → 优先用站点统一对比图（用户同意）
        for f in files:
            if ('__cmp__' in f) == is_cmp:
                return f, ('cmp' if is_cmp else 'author')
    return None, ''


def main():
    check = '--check' in sys.argv
    s = io.open(BASE, encoding='utf-8').read()
    REC = blob(s, 'window.__OM3RECIPES__=')
    by = {r['slug']: r for r in REC}

    # ---------- A：标签重构（人脸检测） ----------
    # ⚠ HERO 必须用**源数据**算：base.html 里的 REC 没有 sampleImages 字段，
    #   用它会得到空表 → gen_phototags 退回"按文件名排序"，把第 54 轮的"主图优先"打回原形
    #   （dv_r54 的第 129 条断言当场抓出来：andrew-gow 的主图从 s02 掉回 s01）。
    G55.have = set(os.listdir(os.path.join(ROOT, 'apk', 'assets', 'images')))   # hero_map 要用它
    gen_phototags.HERO = G55.hero_map(G55.load_by())
    print('A. 跑 gen_phototags（人像→暖肤调；人脸检测给 人像特写/人脸/人群）')
    gen_phototags.main()
    s = io.open(BASE, encoding='utf-8').read()
    PT = blob(s, 'window.__OM3PHOTOTAGS__ =')
    PH = blob(s, 'window.__OM3PHOTOS__ =')
    n_big = sum(1 for v in PT.values() if '人像特写' in v)
    n_face = sum(1 for v in PT.values() if '人脸' in v)
    n_crowd = sum(1 for v in PT.values() if '人群' in v)
    n_warm = sum(1 for v in PT.values() if '暖肤调' in v)
    print('   图库 %d 张：人像特写 %d / 有脸 %d / 人群 %d / 暖肤调 %d'
          % (len(PT), n_big, n_face, n_crowd, n_warm))

    # ---------- B：页面 SEL_TAGS 表（死代码，但别让它说谎） ----------
    CMT = '/* 第 56 轮：这张表是第 39 轮'          # ⚠ 重跑时要把上一版注释一起圈进来，否则会叠注释
    i = s.index(CMT) if CMT in s else s.index('var SEL_TAGS = {')
    j = s.index('};', s.index('var SEL_TAGS = {', i)) + 2
    new_tab = ('/* 第 56 轮：这张表是第 39 轮「按场景挑图」留下的**说明表**——那套按场景挑图的 JS\n'
               '   早已被后来的重写取代（那套函数早已被删），真正生效的是数据侧\n'
               '   `__OM3SC__[].items[].f`（由 gen_r56.py 按这张表的口径预先挑好）。\n'
               '   口径：portrait/wedding/kids 只认人脸检测出来的「人像特写」；\n'
               '   原来写的「人像」是色彩统计（暖棕像素>5%），木头吉他都会中，第 56 轮已改名「暖肤调」。 */\n'
               '    var SEL_TAGS = {\n'
               "      portrait: ['人像特写'], wedding: ['人像特写'], kids: ['人像特写'], mono: [],\n"
               "      flower: ['花卉'], sunset: ['花卉'], forest: ['绿意'], autumn: ['绿意'],\n"
               "      night: ['夜景'], skywater: ['天空水面'], snow: ['高调'], mist: ['雾'],\n"
               "      arch: ['中性白'], still: ['中性白'], street: ['人群'], travel: ['人群'], backlight: ['人群'],\n"
               "      rain: ['日常'], food: ['日常'], indoor: ['夜景'], film: ['日常']\n"
               '    };')
    s = s[:i] + new_tab + s[j:]

    # ---------- C：__OM3SC__ 重挑 + 说真话 + 命中优先 ----------
    SC = blob(s, 'window.__OM3SC__ =')
    rep = Counter()
    for sc in SC:
        key, label, want = sc['k'], sc['label'], WANT.get(sc['k'], [])
        rows = []
        for it in sc['items']:
            slug = re.sub(r'^[rk]-', '', it['i'])
            f, state = pick(slug, want, PH, PT)
            if not f:
                rows.append((it, False))
                continue
            it['f'] = f
            pre = (HIT_PREFIX % ' / '.join(PT.get(f) or []) if state == 'hit'
                   else MISS_CMP % (label,) if state == 'cmp'
                   else MISS_AUTH % (label,))
            def _join(pre, rest):
                rest = strip_prefix(rest).strip()
                return pre + ('｜ ' + rest if rest else '')   # ★ 剥完是空就别留悬空的「｜」
            it['d'] = _join(pre, it.get('d') or '')
            it['dd'] = _join(pre, it.get('dd') or '')
            rep[state if state != 'plain' else 'hit' if state == 'plain' and want == [] else state] += 1
            rows.append((it, state == 'hit'))
        hit_rows = [r for r in rows if r[1]]
        miss_rows = [r for r in rows if not r[1]]
        sc['items'] = [r[0] for r in hit_rows + miss_rows]      # 命中的排前面
    s = set_blob(s, 'window.__OM3SC__ =', SC)
    print('C. __OM3SC__ 重挑：命中 %d 条 / 兜底用统一对比图 %d 条 / 兜底作者样片 %d 条'
          % (rep.get('hit', 0), rep.get('cmp', 0), rep.get('author', 0)))
    for sc in SC:
        bad = [it['n'] for it in sc['items']
               if WANT.get(sc['k']) and any(t in WANT[sc['k']] for t in (PT.get(it['f']) or []))]
        if sc['k'] in ('portrait', 'wedding', 'kids'):
            print('   %-12s %2d 条，其中真·对题 %d 条' % (sc['label'], len(sc['items']), len(bad)))

    # ---------- D：重名配方加作者 ----------
    def norm(n):
        return re.sub(r'[\s·\-—]', '', re.sub(r'[（(].*?[)）]', '', n)).lower()

    g = defaultdict(list)
    for r in REC:
        g[norm(r['n'])].append(r)
    rename = {}
    for k, v in g.items():
        if len(v) < 2:
            continue
        cnt = Counter(r['n'] for r in v)
        for r in v:
            if cnt[r['n']] > 1:                     # 只改"一模一样"的；"（冲印版）"这类已有区分词的不动
                rename[r['slug']] = '%s（%s）' % (r['n'], (r['a'] or '').strip())
    print('D. 重名配方 %d 条要加作者区分' % len(rename))
    for k, v in sorted(rename.items()):
        print('   %-46s → %s' % (k, v))
    if rename:
        for r in REC:
            if r['slug'] in rename:
                r['n'] = rename[r['slug']]
        s = set_blob(s, 'window.__OM3RECIPES__=', REC)
        IDX = blob(s, 'var IDX=')
        SC = blob(s, 'window.__OM3SC__ =')
        SCB = blob(s, 'window.SC = ')
        # 槽位 → slug：以**旧文件**为准（读旧 .osname → 旧 REC 名字 → slug）。
        # ⚠ 别只用 __OM3SC__ 的 os 字段：不在任何场景里的槽位会漏（'Portra 400' 那两个就漏过）
        OLD56 = io.open(os.path.join(ROOT, 'app', 'base.before_r56.html'), encoding='utf-8').read()
        _oldrecs = blob(OLD56, 'window.__OM3RECIPES__=')
        # ⚠ 必须 (名字, 作者) 双键：Portra 400 有三条，只按名字会张冠李戴
        #   （第一版就错了：oC2-3/oC5-4 被写成 Isaac 的，而槽位里的参数是 Peter 的 → dv_r50 当场抓出来）
        _old_nm = defaultdict(list)
        for r in _oldrecs:
            _old_nm[r['n']].append(r)

        def _wb(r):
            return '%s%d %s%d' % ('A' if r['wba'] >= 0 else 'B', abs(r['wba']),
                                  'G' if r['wbg'] >= 0 else 'M', abs(r['wbg']))

        slot_slug = {}
        for _m in re.finditer(r'<div class="oslot" id="([^"]+)">(.*?)(?=<div class="oslot" id=|</div></details>)',
                              OLD56, re.S):
            _sid, _seg = _m.group(1), _m.group(2)
            _mn = re.search(r'<span class="osname">([^<]*)</span>', _seg)
            _ma = re.search(r'<span class="osauth">([^<]*)</span>', _seg)
            _mw = re.search(r'<span class="oswb">([^<]*)</span>', _seg)
            if not _mn:
                continue
            _nm, _wbv = _mn.group(1), (_mw.group(1) if _mw else '')
            _c = _old_nm.get(_nm.strip(), [])
            _sl = ''
            if len(_c) == 1:
                _sl = _c[0]['slug']
            elif _c:
                # 重名 → 用**色轮 12 值**认人（最可靠的指纹；白平衡可能撞车，名字/作者标签本身可能就是错的）
                #   实测：oC2-3 标签写 James 却是 Peter 的、oC3-3 写 Angelo 却是别人的 —— 只有色轮值说了算
                _vals = [int(x) for x in re.findall(r'<b>(-?\d+)</b>', _seg)]
                _w = re.sub(r'[+ ]', '', _wbv)
                for _r in _c:
                    if len(_vals) == 12 and list(_r['v']) == _vals:
                        _sl = _r['slug']
                        break
                if not _sl:                       # 色轮对不上（黑白槽不走色轮）→ 退到白平衡
                    for _r in _c:
                        if re.sub(r'[+ ]', '', _wb(_r)) == _w:
                            _sl = _r['slug']
                            break
                if not _sl:
                    _sl = _c[0]['slug']
            if _sl:
                slot_slug[_sid] = _sl
        for sc in list(SC) + list(SCB):                 # 场景里的 os 字段作为补充
            for it in sc.get('items', []):
                if it.get('os') and str(it.get('i', '')).startswith('r-'):
                    slot_slug.setdefault(it['os'], it['i'][2:])
        for it in IDX:
            h = str(it.get('h') or '')
            slug = h[2:] if h[:2] in ('r-', 'k-') else slot_slug.get(h)
            if slug in rename:
                it['n'] = rename[slug]
        for sc in SC:
            for it in sc['items']:
                if str(it.get('i', '')).startswith('r-') and it['i'][2:] in rename:
                    it['n'] = rename[it['i'][2:]]
        for sc in SCB:
            for it in sc.get('items', []):
                if str(it.get('i', '')).startswith('r-') and it['i'][2:] in rename:
                    it['n'] = rename[it['i'][2:]]
        s = set_blob(s, 'var IDX=', IDX)
        s = set_blob(s, 'window.__OM3SC__ =', SC)
        s = set_blob(s, 'window.SC = ', SCB)
        # 卡片标题 / 固定色温表 / 槽位名
        for slug, new in rename.items():
            old = by[slug]['n']
            s, n1 = re.subn(r'(<div class="card" id="r-%s">.*?<span class="cname">)[^<]*(</span>)'
                            % re.escape(slug), lambda m: m.group(1) + new + m.group(2), s, count=1, flags=re.S)
            s, n2 = re.subn(r'(<tr id="k-%s">\s*<td>)[^<]*(</td>)' % re.escape(slug),
                            lambda m: m.group(1) + new + m.group(2), s, count=1, flags=re.S)
            n3 = 0                      # ⚠ 别写 s, n3 = (0, 0)（那会把 s 变成 int）
            for sid, sl in slot_slug.items():
                if sl == slug:
                    s, nn = re.subn(r'(<div class="oslot" id="%s">.*?<span class="osname">)[^<]*(</span>)'
                                    % re.escape(sid), lambda m: m.group(1) + new + m.group(2), s,
                                    count=1, flags=re.S)
                    n3 += nn
            assert n1 <= 1 and n2 <= 1, '改名定位异常（卡 %d / 色温表 %d）' % (n1, n2)
            print('   %-44s 卡 %d 处 / 色温表 %d 处 / 槽位 %d 处' % (old, n1, n2, n3))

    # ---------- D2：槽位归属纠正（按色轮 12 值认人） ----------
    # 起因：oC5-3 实际是 James 的 Kodachrome 64，槽位上的白平衡却写着别人的 A+1 G0
    # （第 50 轮给槽位补 .oswb 时是"按名字找配方"，重名就张冠李戴了）。
    # 色轮 12 值是唯一指纹 → 用它对上配方，再把 名字/作者/白平衡 三处一起纠。
    import om3_profile as _OP
    _segs = dict((m.group(1), m.group(2)) for m in re.finditer(
        r'<div class="oslot" id="([^"]+)">(.*?)(?=<div class="oslot" id=|</div></details>)', s, re.S))
    _fix = []
    for sid, seg in _segs.items():
        vals = [int(x) for x in re.findall(r'<b>([-+]?\d+)</b>', seg)]
        if len(vals) != 12:
            continue
        hit = [r for r in REC if list(r['v']) == vals]
        if len(hit) != 1:                       # 认不出来/多义 → 不猜
            continue
        r = hit[0]
        want_nm, want_au = r['n'], (r['a'] or '').strip()
        # ⚠ 用 is not None：wba=wbg=0 是合法的「A0 G0」；写成 or 会被判成没有白平衡 → 报告里一堆假纠正
        want_wb = (_OP.wbtxt(r.get('wba'), r.get('wbg'))
                   if (r.get('wba') is not None and r.get('wbg') is not None) else '')
        cur = dict((k, (re.search(r'<span class="%s">([^<]*)</span>' % k, seg) or [None, ''])[1])
                   for k in ('osname', 'osauth', 'oswb'))
        if cur.get('osname') == want_nm and cur.get('osauth') == want_au and cur.get('oswb') == want_wb:
            continue
        for k, v in (('osname', want_nm), ('osauth', want_au), ('oswb', want_wb)):
            if not v:
                continue
            s, n = re.subn(r'(<div class="oslot" id="%s">.*?<span class="%s">)[^<]*(</span>)'
                           % (re.escape(sid), k), lambda m: m.group(1) + v + m.group(2), s,
                           count=1, flags=re.S)
            assert n == 1, '槽位 %s 的 %s 改不动' % (sid, k)
        _fix.append((sid, cur.get('osname'), want_nm, cur.get('oswb'), want_wb))
    print('D2. 槽位归属：按色轮 12 值对上 %d 个；纠正 %d 个' % (len(_segs), len(_fix)))
    for sid, o, nw, owb, nwb in _fix:
        print('   %-8s %-30s → %-30s ｜ 白平衡 %-8s → %s' % (sid, (o or '')[:28], nw[:28], owb, nwb))
    if _fix:
        IDX2 = blob(s, 'var IDX=')
        _slot_owner = {}
        for sid, seg in _segs.items():
            vals = [int(x) for x in re.findall(r'<b>([-+]?\d+)</b>', seg)]
            h = [r for r in REC if len(vals) == 12 and list(r['v']) == vals]
            if len(h) == 1:
                _slot_owner[sid] = h[0]
        for it in IDX2:
            r = _slot_owner.get(str(it.get('h') or ''))
            if r:
                it['n'], it['a'] = r['n'], (r['a'] or '').strip()
        s = set_blob(s, 'var IDX=', IDX2)

    # ---------- E：目录重建 + 结构配平 ----------
    s, n_toc_grp, n_toc_card = G55.sync_toc(s)
    n_open, n_close = len(re.findall(r'<div\b', s)), s.count('</div>')
    assert n_open == n_close, '结构坏了：<div %d / </div> %d' % (n_open, n_close)

    # ---------- 收尾自查 ----------
    REC2 = blob(s, 'window.__OM3RECIPES__=')
    names = [r['n'] for r in REC2]
    dup = [k for k, v in Counter(names).items() if v > 1]
    cards = re.findall(r'<div class="card" id="r-[^"]+">.*?<span class="cname">([^<]*)</span>', s, re.S)
    dupc = [k for k, v in Counter(cards).items() if v > 1]
    assert not dup, 'REC 里还有重名：%s' % dup[:5]
    assert not dupc, '卡片里还有重名：%s' % dupc[:5]
    print('E. 目录重建 %d 组 / %d 卡；REC %d 条名唯一；卡片 %d 张名唯一'
          % (n_toc_grp, n_toc_card, len(names), len(cards)))
    if check:
        print('（--check：不写盘）')
        return 0
    io.open(BASE, 'w', encoding='utf-8', newline='').write(s)
    print('已写入 app/base.html')
    return 0


if __name__ == '__main__':
    sys.exit(main())
