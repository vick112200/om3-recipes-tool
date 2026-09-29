# -*- coding: utf-8 -*-
"""第 39 轮（B2）：场景对比页改造 —— 用户三条要求
   ① 「把最上面的大标题小标题该省的去掉」
   ② 「场景用 select 下拉选择来选，这样就不会顶下去了，记得 select 做好看一点」
   ③ 「根据场景选择相应的图片…人像就尽量放关于人的照片」（← 用 B1 的画面自动归类标签挑图）
   同时**保留**原来的实拍对比 + 一屏一张左右滑动（第 37 轮我把它顶到了 16727px 处，等于藏了）。

做法（低风险）：
 · 删掉 paneC 顶部 `<h1>场景对比</h1>` 与 `<p class="sub">…`；删掉第 37 轮那两个 `<h2 class="sidxh">` 和 `#scidx` 索引块
 · `#scbar`（6 个按钮）**保留在 DOM 里**（原有绑定逻辑不动）但用 CSS 隐藏；前面加一个 `<select id="scsel">`
   —— 选项分两组：实拍对比 6 个（u:0…u:5）/ 按场景挑 21 个（s:<key>）
 · 场景关键词表另存 `window.__OM3SCENES__`（不依赖 scidx 那个 IIFE）
 · 在原 SC 脚本块内（`build()` 同作用域）加：按场景从 IDX 组 slides + 按标签挑图 + select 的 change 处理
"""
import io, os, re, sys
sys.path.insert(0, r'D:\workspace\om3-handbook\scripts')
import patch_scidx as PS                                  # 复用同一份 21 场景关键词表
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()
n = 0


def rep(old, new, must=True):
    global s, n
    if old not in s:
        if must:
            raise SystemExit('❌ 锚点没找到：%s' % old[:80])
        print('  ⚠ 跳过：%s' % old[:60])
        return
    s = s.replace(old, new, 1)
    n += 1


# ---------- ① 顶部大标题/小标题 + 我上轮加的两个小标题与索引块 ----------
rep('<!-- SCIDX-BEGIN -->', '<!-- SCIDX-BEGIN（第 39 轮：索引列表已被 select 取代，下面整块注释掉）-->\n<!--', must=False)
rep('<!-- SCIDX-END -->', '-->\n<!-- SCIDX-END -->', must=False)

# ---------- ② 场景关键词表（供 select 的 21 项 + 匹配用）----------
scenes = [{'k': k, 'label': lb, 'kw': kw} for (k, lb, kw) in PS.SCENES]
rep('/* ---------- 4. 场景对比 ---------- */',
    '/* ---------- 4. 场景对比（第 39 轮：select 下拉 + 按场景挑图） ---------- */\n'
    'window.__OM3SCENES__ = ' + __import__('json').dumps(scenes, ensure_ascii=False, separators=(',', ':')) + ';')

# ---------- ③ select 下拉（放在 #scbar 前；#scbar 用 CSS 隐藏）----------
u6 = [('marathon', 'marathon · 人群 / 暖光石拱'), ('peace-memorial', 'peace-memorial · 中性白 / 蓝天绿树'),
      ('redbud', 'redbud · 花卉 / 粉红与绿'), ('rosslyn-dusk', 'rosslyn-dusk · 夜景 / 混光车流'),
      ('misty-mountains', 'misty-mountains · 冷调 / 雾与远景'), ('moss', 'moss · 绿意 / 暗部细节')]
opt_u = ''.join('<option value="u:%d">%s</option>' % (i, lb) for i, (k, lb) in enumerate(u6))
opt_s = ''.join('<option value="s:%s">%s</option>' % (k, lb) for k, lb, _ in PS.SCENES)
sel = ('<div class="scselwrap">'
       '<label class="scsellab" for="scsel">看哪个场景</label>'
       '<select id="scsel" class="scsel" aria-label="选择场景">'
       '<optgroup label="实拍对比 · 同一构图、一屏一张（6 个）"><option value="u:0" selected>%s</option>%s</optgroup>'
       '<optgroup label="按场景挑 · 21 个场景，图按画面自动归类"><option value="s:portrait">人像肤色</option>%s</optgroup>'
       '</select>'
       '<span class="scselhint">按场景挑时，每条优先放**画面里对得上场景**的那张（自动归类，偶尔会看错）；'
       '左右滑动一次换一张</span></div>'
       % (u6[0][1], ''.join('<option value="u:%d">%s</option>' % (i, lb) for i, (k, lb) in enumerate(u6) if i),
          ''.join('<option value="s:%s">%s</option>' % (k, lb) for k, lb, _ in PS.SCENES if k != 'portrait')))
# 把两个 optgroup 里的重复项去掉（上面第一组已含 u:0，第二组已含 portrait）
sel = sel.replace('<option value="u:0" selected>%s</option><option value="u:0">%s</option>' % (u6[0][1], u6[0][1]),
                  '<option value="u:0" selected>%s</option>' % u6[0][1])
rep('<div class="scbar" id="scbar">', sel + '\n<div class="scbar" id="scbar">', must=False)

# ---------- ④ CSS：隐藏旧按钮条 + 让 select 好看 ----------
rep('#toc3.open', '#toc3.open', must=False)     # 占位（不做事）
css = ('\n/* 第 39 轮：场景对比页 —— 旧按钮条隐藏，改用好看的 select */\n'
       '#scbar{display:none !important}\n'
       '.scselwrap{position:sticky;top:56px;z-index:20;background:#161616;padding:8px 0 10px;margin:0 0 10px;'
       'border-bottom:1px solid #262626}\n'
       '.scsellab{display:block;font-size:12px;color:#8fa;opacity:.75;margin:0 0 5px 2px;letter-spacing:.4px}\n'
       '.scsel{width:100%;appearance:none;-webkit-appearance:none;background:#20262b;color:#eaf6f1;'
       'border:1px solid #2f8f74;border-radius:11px;padding:12px 40px 12px 14px;font-size:15px;font-weight:600;'
       'line-height1.2;box-shadow:0 2px 10px rgba(0,0,0,.35)}\n'
       '.scsel:focus{outline:none;border-color:#7ed3bd;box-shadow:0 0 0 3px rgba(47,143,116,.28)}\n'
       '.scselwrap{position:relative}\n'
       '.scselwrap::after{content:"▾";position:absolute;right:15px;top:39px;font-size:15px;color:#7ed3bd;pointer-events:none}\n'
       '.scsel optgroup{color:#8fa;background:#1b1f22;font-size:13px}\n'
       '.scsel option{color:#e9e9e9;background:#1b1f22;font-size:14px;padding:6px}\n'
       '.scselhint{display:block;font-size:11.5px;color:#7d7d7d;margin-top:6px;line-height:1.5}\n'
       '.scptag{display:inline-block;font-size:10.5px;color:#8fd8c2;border:1px solid #2f5b4e;border-radius:6px;'
       'padding:1px 5px;margin-right:6px;vertical-align:1px}\n')
rep('</style>', css + '</style>')

# ---------- ⑤ 原 SC 脚本块内：按场景组 slides + 挑图 + select 联动 ----------
anchor = ("    var btns = scbar.querySelectorAll('button');\n"
          "    for (var bi = 0; bi < btns.length; bi++) {\n"
          "      btns[bi].addEventListener('click', function () { build(+this.getAttribute('data-i')); });\n"
          "    }")
assert anchor in s, '找不到 #scbar 绑定处'
extra = anchor + r"""

    /* ================= 第 39 轮：select 下拉 + 「按场景挑」+ 按画面归类挑图 ================= */
    /* 场景 → 期望的画面标签（B1 自动归类得到；没有对得上的就退回统一场景图） */
    var SEL_TAGS = {
      portrait: ['人像'], wedding: ['人像'], kids: ['人像'], mono: ['人像'],
      flower: ['花卉'], sunset: ['花卉'], forest: ['绿意'], autumn: ['绿意'],
      night: ['夜景'], skywater: ['天空水面'], snow: ['高调'], mist: ['雾'],
      arch: ['中性白'], still: ['中性白'], street: ['人群'], travel: ['人群'], backlight: ['人群'],
      rain: ['日常'], food: ['日常'], indoor: ['日常'], film: ['日常']
    };
    var PTAGS = window.__OM3PHOTOTAGS__ || {}, PHOTOS = window.__OM3PHOTOS__ || {};
    var ALLIDX = window.__om3idx || [];
    try { if (!ALLIDX.length && window.IDX) ALLIDX = window.IDX; } catch (e6) {}
    /* 名字 → 优化版槽位锚点（给「优化版 · 看槽位 →」按钮用） */
    var OSLOT = {};
    for (var oi = 0; oi < ALLIDX.length; oi++) {
      var e1 = ALLIDX[oi];
      if (String(e1.h || '').charAt(0) === 'o' && e1.n) OSLOT[e1.n] = e1;
    }
    function pickPhoto(anchorId, key) {
      var want = SEL_TAGS[key] || [];
      var slug = String(anchorId || '').replace(/^r-/, '');
      var list = PHOTOS[slug] || [];
      var best = '', bs = -1;
      for (var i = 0; i < list.length; i++) {
        var f = list[i], tg = PTAGS[f] || [], sc = 0;
        for (var j = 0; j < want.length; j++) if (tg.indexOf(want[j]) >= 0) sc += 3;
        if (f.indexOf('__cmp__') >= 0) sc += 1;        /* 统一构图图：同一场景里更好比 */
        if (sc > bs) { bs = sc; best = f; }
      }
      return { f: best, tg: bs > 0 ? (PTAGS[best] || []) : [] };
    }
    var SCR = {}, SCRL = [];
    function sceneOf(key) {
      if (SCR[key]) return SCR[key];
      var def = null, all = window.__OM3SCENES__ || [];
      for (var i = 0; i < all.length; i++) if (all[i].k === key) def = all[i];
      if (!def) return null;
      var kw = def.kw || [], items = [];
      for (var j = 0; j < ALLIDX.length; j++) {
        var it = ALLIDX[j], g = String(it.g || ''), t = String(it.t || '');
        if (!g) continue;
        var hit = false;
        for (var w = 0; w < kw.length; w++) if ((g + ' ' + t).indexOf(kw[w]) >= 0) { hit = true; break; }
        if (!hit) continue;
        var ph = pickPhoto(it.h, key);
        if (!ph.f) continue;                            /* 这张配方在这个场景没有图 → 不占位 */
        var os = OSLOT[it.n] || null;
        items.push({ i: it.h, n: it.n, a: it.a || '', sl: it.sl || '', t: it.t || '',
                     f: ph.f, d: (ph.tg.length ? ('图按画面自动归类：' + ph.tg.join(' / ') + '（可能看错）｜ ') : '') + String(it.f || ''),
                     os: os ? os.h : '', osl: os ? os.sl : '' });
      }
      var sc = { key: def.k, label: def.label, items: items, pick: true };
      SCR[key] = sc; SCRL.push(sc);
      return sc;
    }
    window.__scShowScene = function (key) {
      var sc = sceneOf(key);
      if (!sc || !sc.items.length) return false;
      if (SC.indexOf(sc) < 0) SC.push(sc);
      build(SC.indexOf(sc));
      return true;
    };
    window.__scBuild = build;
    window.__scSceneInfo = function () {
      var o = {};
      for (var i = 0; i < (window.__OM3SCENES__ || []).length; i++) {
        var k = window.__OM3SCENES__[i].k, sc = sceneOf(k);
        o[k] = sc ? sc.items.length : 0;
      }
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
      /* 默认停在第一个「按场景挑」的场景上？不 —— 默认保持原来的实拍对比首页（u:0），
         用户想挑场景时再下拉。 */
    }
    window.__om3scSel = scsel;"""
rep(anchor, extra)

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('✅ B2 完成，共改 %d 处（隐藏旧按钮条 + select 下拉 + 按场景挑图 + 保留左右滑动）' % n)
