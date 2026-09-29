# -*- coding: utf-8 -*-
"""第 39 轮（B3）：把「按场景挑」的 21 个场景**在 Python 里算好**，嵌成 `window.__OM3SC__`。

为什么不在运行时算：实测 `window.IDX` / `window.LIDX` 都是 undefined（那些 `var` 不是全局），
运行时拿不到索引 —— 所以照「6 个统一场景」的既有做法，数据在构建期生成，运行时只查表。

每个场景：{ k, label, items:[ {i 锚点, n 名, a 作者, sl 槽位, t 标签, f 图, d 描述, os 优化版锚点, osl} ] }
选图规则（和 B1 的标签对应）：该配方所有图里，标签命中场景期望的优先；同分时优先「统一构图图」
（同场景里更好比），最后才轮到作者样片；一张都没命中就用统一场景图兜底。
"""
import io, json, os, re, sys
sys.path.insert(0, r'D:\workspace\om3-handbook\scripts')
import patch_scidx as PS
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\workspace\om3-handbook'
P = BASE + r'\app\base.html'
IMG = BASE + r'\apk\assets\images'
B, E = '<!-- OM3SC-BEGIN -->', '<!-- OM3SC-END -->'
DEC = json.JSONDecoder()
SEL_TAGS = {
 'portrait': ['人像'], 'wedding': ['人像'], 'kids': ['人像'], 'mono': ['人像'],
 'flower': ['花卉'], 'sunset': ['花卉'], 'forest': ['绿意'], 'autumn': ['绿意'],
 'night': ['夜景'], 'skywater': ['天空水面'], 'snow': ['高调'], 'mist': ['雾'],
 'arch': ['中性白'], 'still': ['中性白'], 'street': ['人群'], 'travel': ['人群'], 'backlight': ['人群'],
 'rain': ['日常'], 'food': ['日常'], 'indoor': ['日常'], 'film': ['日常'],
}

s = io.open(P, encoding='utf-8').read()
m = re.search(r'window\.__OM3RECIPES__=', s)
REC, _ = DEC.raw_decode(s, m.start() + len('window.__OM3RECIPES__='))
m2 = re.search(r'var IDX=', s)
IDX, _ = DEC.raw_decode(s, m2.start() + len('var IDX='))
m3 = re.search(r'window\.__OM3PHOTOTAGS__\s*=\s*', s)
PT, _ = DEC.raw_decode(s, m3.end())
m4 = re.search(r'window\.__OM3PHOTOS__\s*=\s*', s)
PH, _ = DEC.raw_decode(s, m4.end())
print('  配方 %d 条 / 索引 %d 条 / 图标签 %d 张 / 图清单 %d 个配方' % (len(REC), len(IDX), len(PT), len(PH)))

# 名字 → 优化版槽位（给跳转按钮）
OSLOT = {}
for e in IDX:
    if str(e.get('h', '')).startswith('o') and e.get('n'):
        OSLOT.setdefault(e['n'], e)


def pick(anchor, key):
    want = SEL_TAGS.get(key, [])
    slug = re.sub(r'^[rk]-', '', str(anchor or ''))
    slug2 = slug.replace('om3lab_', 'om3lab_')          # 本站设计的 slug 就是这样
    cand = PH.get(slug) or PH.get(slug2) or []
    best, bs, btg = '', -1, []
    for f in cand:
        tg = PT.get(f, [])
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
        os = OSLOT.get(it['n'])
        items.append({'i': it['h'], 'n': it['n'], 'a': it.get('a', ''), 'sl': it.get('sl', ''),
                      't': it.get('t', ''), 'f': f,
                      'd': (('图按画面自动归类：%s（自动判断，偶尔会看错）｜ ' % ' / '.join(tg)) if tg else '') +
                           str(it.get('f') or '')[:150],
                      'os': os['h'] if os else '', 'osl': (os.get('sl') or '') if os else ''})
    SCENES.append({'k': k, 'label': label, 'items': items})
    print('    %-14s %3d 条（有图）' % (label, len(items)))

js = ('window.__OM3SC__ = ' + json.dumps(SCENES, ensure_ascii=False, separators=(',', ':')) + ';\n')
s = re.sub(re.escape(B) + r'.*?' + re.escape(E) + r'\n?', '', s, flags=re.S)
k = s.find('/* ---------- 4. 场景对比')
assert k > 0
s = s[:k] + B + '\n' + js + E + '\n' + s[k:]

# 运行时改成查表（替换 B2 里那段自己算的逻辑）
old_start = s.find('    var SCR = {}, SCRL = [];')
old_end = s.find('    window.__om3scSel = scsel;', old_start)
assert old_start > 0 and old_end > old_start, '运行时段落定位失败'
new_run = r"""    var SCTAB = window.__OM3SC__ || [], SCR = {};
    for (var ti = 0; ti < SCTAB.length; ti++) SCR[SCTAB[ti].k] = SCTAB[ti];
    window.__scShowScene = function (key) {
      var sc = SCR[key];
      if (!sc || !sc.items || !sc.items.length) return false;
      if (SC.indexOf(sc) < 0) SC.push(sc);
      build(SC.indexOf(sc));
      return true;
    };
    window.__scBuild = build;
    window.__scSceneInfo = function () {
      var o = {};
      for (var i = 0; i < SCTAB.length; i++) o[SCTAB[i].k] = SCTAB[i].items.length;
      return o;
    };
    var scsel = document.getElementById('scsel');
    if (scsel) {
      scsel.addEventListener('change', function () {
        var v = String(this.value || '');
        if (v.indexOf('u:') === 0) { build(Number(v.slice(2))); }
        else if (v.indexOf('s:') === 0) {
          if (!window.__scShowScene(v.slice(2))) { scpos.textContent = '这个场景暂时没有配得上的图'; }
        }
      });
    }
"""
s = s[:old_start] + new_run + s[old_end + len('    window.__om3scSel = scsel;'):]
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('  ✅ 已嵌入 window.__OM3SC__（21 个场景，约 %.0f KB）+ 运行时改为查表' % (len(js) / 1024.0))
