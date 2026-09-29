# -*- coding: utf-8 -*-
"""第 47 轮生成器（幂等）· v3.1

用户 2026-09-25 提的四件事：
  ① 「现在目录点击了不会自动关。」
  ② 「档位推荐的目录页面有同步新增的档位。」（＝ 目录还停在第 43 轮的手写状态，没跟上 C6–C10 / #opick）
  ③ 「切换底部的配方合集到档位推荐等功能，会保持之前的滚动位置，所以可能切换了成空页面。」
  ④ 「我需要能够在档位推荐中，整个档位存入我的配方中的新建档位中，名称也继承过去。」
     用户答复：④-a 先弹确认框；④-b 名字格式「C1 人像档」。

本脚本改 6 处（全部幂等；跑第二遍一条都不会重复改）：
  A. CSS：`.omstore` / `.omtierbtn`（新按钮的排布）
  B. 块02：`close()` 走唯一主控；`nav2` 那条死监听 → document 级委托（解析顺序问题根治）
  C. 块07：暴露 `window.__om3tocClose` + document 级「点目录项 → 关面板」
  D. 块03：槽位数改成运行时数（写死的"21 个槽位"早过期了）
  E. 块08：`switchPane()` 切页签时滚动归零；`#toc2` 的"候选档"那一组改成**按 DOM 生成**（目录与页面永不失同步）
  F. 块07：「整个档位存入我的配方」按钮注入 + 确认框 + 建方案 + 整档填槽（复用 putRecInSlot 那唯一一份实现）
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
LOG = []

s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r47.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r47.html')


def rep(old, new, tag):
    """唯一锚点替换；已经是新内容就跳过（幂等）。"""
    global s
    if new in s:
        LOG.append('  · 已改过，跳过：' + tag)
        return
    n = s.count(old)
    assert n == 1, '!! 锚点不唯一（%d 处）：%s' % (n, tag)
    s = s.replace(old, new, 1)
    LOG.append('  ✅ ' + tag)


# ================================================================ A) CSS
CSS = (
    '/* 第 47 轮：档位推荐里「整个档位存入我的配方」那一行 */\n'
    '.omstore{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:6px 0 12px;'
    'padding:10px 12px;border-radius:10px;background:#1a2233;border:1px solid #2b5cff}\n'
    '.omtierbtn{padding:10px 14px;border-radius:9px;border:1px solid #2b5cff;background:#2b5cff;'
    'color:#fff;font-weight:700;font-size:13px;font-family:inherit}\n'
    '.omstore span{flex:1;min-width:180px;font-size:12px;color:#9fb4dd;line-height:1.55}\n'
)
OLD_CSS = '.omode{background:#1c1c1c;border:1px solid #2e2e2e;border-radius:12px;margin:12px 0;overflow:hidden}'
rep(OLD_CSS, CSS + OLD_CSS, 'CSS：.omstore / .omtierbtn')

# ================================================================ B) 块02
OLD_CLOSE = r" function close(){if(nav)nav.classList.remove('open');if(nav2)nav2.classList.remove('open');btn.textContent='\ud83d\udd0d';try{q.blur();}catch(e){}}"
NEW_CLOSE = (r" function close(){if(nav)nav.classList.remove('open');if(nav2)nav2.classList.remove('open');"
             r"btn.textContent='\ud83d\udd0d';try{q.blur();}catch(e){}"
             "/* r47：关闭必须走\"唯一主控\"（块07 的 __om3tocClose）—— 只删 .open 类没用："
             "apply() 打过内联 display:block!important，面板根本不关 */"
             "try{ if(window.__om3tocClose) window.__om3tocClose(); }catch(e2){}")
# 块02 的兜底：桌面模式（没有块07 的 __om3tocClose）下，光删 .open 类关不掉内联 !important 的面板；
# 而且 `nav2` 在解析期是 null（#toc2 由块08 注入），所以要**点击时现取**。
NEW_CLOSE2 = (NEW_CLOSE + "/* 兜底（桌面模式没有块07 的 __om3tocClose）：点击时现取 #toc2（解析期它是 null —— #toc2 由块08 注入，"
              "所以上面那两个 if(nav2) 在桌面模式一律不成立），再把两个面板都硬收一次：有的路径把 display 以内联 "
              "!important 打开过，只删 .open 类是关不掉的（第 47 轮顺手补上，用户①在桌面模式也成立） */"
              "try{ var n2b=document.getElementById('toc2');"
              " if(nav) nav.style.setProperty('display','none','important');"
              " if(n2b){ n2b.classList.remove('open'); n2b.style.setProperty('display','none','important'); } }catch(e3){}}")
# ⚠ 幂等判定按"标志片段"，不能按"新文本整体在不在"：NEW_CLOSE2 里含 NEW_CLOSE 的前缀，
#   整体判断在不同阶段会来回假阴性（第 47 轮踩过，见 SPEC §6）。
if 'var n2b=document.getElementById' in s:
    LOG.append('  · 已改过，跳过：块02：close() 走唯一主控 + 硬收两个面板')
elif "try{ if(window.__om3tocClose) window.__om3tocClose(); }catch(e2){}" in s:
    assert s.count(NEW_CLOSE) == 1, '!! 锚点不唯一：close() 第一段'
    s = s.replace(NEW_CLOSE, NEW_CLOSE2, 1)
    LOG.append('  ✅ 块02：close() 补上"硬收两个面板"（桌面模式兜底）')
else:
    assert s.count(OLD_CLOSE) == 1, '!! 锚点不唯一：close() 原样'
    s = s.replace(OLD_CLOSE, NEW_CLOSE2, 1)
    LOG.append('  ✅ 块02：close() 走唯一主控 + 硬收两个面板')

OLD_NAV2 = (" if(nav2) nav2.addEventListener('click',function(e){\n"
            "   var a=e.target.closest?e.target.closest('a'):null;\n"
            "   if(a&&nav2.contains(a)){ jumpToPane(a); close(); }\n"
            " });")
NEW_NAV2 = (" /* r47：原来这里是 `if(nav2) nav2.addEventListener(…)` —— 而 `nav2` 在解析期就是 null\n"
            "    （#toc2 是块08 注入的）⇒ 这条监听**从来没绑上**，所以\"档位推荐目录里点一条\"不会关面板\n"
            "    （用户报的\"目录点击了不会自动关\"）。改成 document 级委托 + 点击时再取元素：\n"
            "    解析顺序、以及目录内容运行时生成，都不再影响它。 */\n"
            " document.addEventListener('click',function(e){\n"
            "   var a=e.target&&e.target.closest?e.target.closest('a'):null;\n"
            "   if(!a)return;\n"
            "   var n2=document.getElementById('toc2');\n"
            "   if(n2&&n2.contains(a)){ jumpToPane(a); close(); }\n"
            " });")
rep(OLD_NAV2, NEW_NAV2, '块02：nav2 死监听 → document 级委托')

# ================================================================ C) 块07 toc 主控
OLD_TG = "    window.__om3tocToggle = toggle;"
NEW_TG = ("    window.__om3tocToggle = toggle;\n"
          "    /* r47：目录里点任意一条 → 面板自动关（用户报\"目录点击了不会自动关\"）。\n"
          "       ⚠ 为什么必须从**这里**关：① `open` 是本闭包的私有变量 —— 别处只删 .open 类的话，\n"
          "         内联的 display:block!important 还在（面板不关），而且状态错位：下次点 🔍 反而是\"关\"；\n"
          "       ② 块02 那条 nav2 监听在解析期就失效了（那时 #toc2 还不存在）。\n"
          "       所以在这里暴露一个 __om3tocClose，并用 document 级委托接住\"点目录项\"。 */\n"
          "    window.__om3tocClose = function(){ if(!open) return; open = false; apply(); };\n"
          "    document.addEventListener('click', function(ev){\n"
          "      var a = ev.target && ev.target.closest ? ev.target.closest('a') : null;\n"
          "      if(!a) return;\n"
          "      var host = a.closest ? a.closest('#toc, #toc2') : null;\n"
          "      if(!host) return;\n"
          "      window.__om3tocClose();\n"
          "    });")
rep(OLD_TG, NEW_TG, '块07：暴露 __om3tocClose + 点目录项关面板')

# ================================================================ D) 块03：槽位数改成运行时数
OLD_STRICT = ("<script>(function () {\n"
              "  'use strict';\n"
              "\n"
              "  /* ---------- 1. 顶层第三个页签（场景对比） ---------- */")
NEW_STRICT = ("<script>(function () {\n"
              "  'use strict';\n"
              "  /* r47：档位推荐到底有多少个槽位 —— **运行时数**，不再写死数字\n"
              "     （第 43–46 轮连着加了槽位，界面里那句\"21 个槽位\"早就过期了）。\n"
              "     同时把函数挂到 window，块08 生成目录时也用这一个数。 */\n"
              "  function OM3SLOTN(){ try{ return document.querySelectorAll('.oslot[id^=\"oC\"]').length || 31; }catch(e){ return 31; } }\n"
              "  window.__om3slotN = OM3SLOTN;\n"
              "\n"
              "  /* ---------- 1. 顶层第三个页签（场景对比） ---------- */")
rep(OLD_STRICT, NEW_STRICT, '块03：加 OM3SLOTN()（运行时数槽位）')

rep("'<div class=\"lbnoplan\">这一卷没进档位推荐（档位推荐只有 21 个槽位）</div>'",
    "'<div class=\"lbnoplan\">这一卷没进档位推荐（档位推荐只有 ' + OM3SLOTN() + ' 个槽位）</div>'",
    '图库弹层文案 1：21 → 运行时数')
rep("'<span class=\"scnoplan\">档位推荐 21 个槽位里没有这一卷</span>'",
    "'<span class=\"scnoplan\">档位推荐 ' + OM3SLOTN() + ' 个槽位里没有这一卷</span>'",
    '场景索引文案 2：21 → 运行时数')

# ================================================================ E) 块08：滚动归零 + 目录同步
OLD_SW_HEAD = ("  function switchPane(p){\n"
               "    if(PS.indexOf(p) < 0) return;")
NEW_SW_HEAD = ("  function switchPane(p){\n"
               "    if(PS.indexOf(p) < 0) return;\n"
               "    /* r47：只有在\"真的换了页签\"时才把滚动位置归零（点当前页签不动） */\n"
               "    var r47sw = (window.__om3cur !== p);")
rep(OLD_SW_HEAD, NEW_SW_HEAD, '块08：switchPane 记录"页签真的变了"')

OLD_SW_TAIL = ("    window.__om3cur = p;\n"
               "  }")
NEW_SW_TAIL = ("    window.__om3cur = p;\n"
               "    /* r47：切换页签 → 滚动位置归零（用户报：\"切到档位推荐会保持之前的滚动位置，可能切成空页面\"）。\n"
               "       用 behavior:'instant' 绕开 CSS 里那行 html{scroll-behavior:smooth}；老 WebView 不认就退回两参写法。\n"
               "       必须在浏览器处理锚点跳转**之前**做：目录里点一条 → 先归零 → 再走默认的 #hash 跳转。 */\n"
               "    if(r47sw){\n"
               "      try{ window.scrollTo({top: 0, left: 0, behavior: 'instant'}); }\n"
               "      catch(e){ try{ window.scrollTo(0, 0); }catch(e2){} }\n"
               "    }\n"
               "  }")
rep(OLD_SW_TAIL, NEW_SW_TAIL, '块08：切页签滚动归零')

# —— 目录：#toc2 里"候选档"那一组改成运行时生成 ——
A_SEG = '<div class="tg"><div class="tgh">总览</div>'
B_SEG = '<div class="emptytoc" id="noresult2">'
i, j = s.index(A_SEG), s.index(B_SEG)
old_seg = s[i:j]
NEW_SEG = (
    '<div class="tg"><div class="tgh">总览</div>\n'
    '<a class="lv2" href="#opick">怎么挑 5 个（10 个候选档一览）</a>\n'
    '<a class="lv2" href="#oskin">肤色风险对照</a>\n'
    '<a class="lv2" href="#omodes">10 个候选档（挑 5 个）</a>\n'
    '<a class="lv2" href="#opink">白里透红（候选）</a>\n'
    '<a class="lv2" href="#osolo">这些配方得单独占一档</a>\n'
    '<a class="lv2" href="#owb">肤色不对时怎么调白平衡</a>\n'
    '</div>\n'
    '<!-- r47：候选档那一组不再手写（手写就跟不上：第 44 轮加了 C6–C10、第 45 轮加了 #opick，\n'
    '     目录一条都没跟）——下面这个空容器由块08 按页面里的 .omode / .oslot **运行时生成**，永不失同步。 -->\n'
    '<div class="tg" id="toc2tiers" data-r47built="0"><div class="tgh">10 个候选档（挑 5 个）</div></div>\n'
    '</div>\n'
)
if 'id="toc2tiers"' in old_seg:
    LOG.append('  · 已改过，跳过：目录（#toc2）候选项组改成运行时生成')
else:
    assert old_seg.count('五个档位') == 1, 'toc2 段里"五个档位"不是 1 处'
    assert old_seg.endswith('</div>\n</div>\n'), 'toc2 段结尾结构变了：' + repr(old_seg[-24:])
    s = s[:i] + NEW_SEG + s[j:]
    LOG.append('  ✅ 目录（#toc2）候选项组改成运行时生成（删掉手写的 C1–C5 那 21 条）')

rep('只在档位推荐里搜（21 个槽位）：配方名',
    '只在档位推荐里搜：配方名', '搜索框 placeholder：去掉写死的槽位数')
rep('档位推荐 21 个槽位里没找到匹配的。',
    '档位推荐里没找到匹配的。', '空结果文案：去掉写死的槽位数')

TOC_SYNC = r"""
  /* ===== 第 47 轮：目录（#toc2）里"候选档"那一组 —— **按页面真实内容生成** =====
     用户报「档位推荐的目录页面（没）有同步新增的档位」：目录一直是手写的，第 44 轮加了 C6–C10、
     第 45 轮加了 #opick，目录一条都没跟上。现在从 DOM 读：以后加档 / 改槽名，目录自动同步。 */
  (function OM3TOCSYNC(){
    function n(){ return (window.__om3slotN ? window.__om3slotN() : 31); }
    function esc47(t){ return String(t).replace(/[&<>]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }
    function trim(t){ return String(t == null ? '' : t).replace(/^\s+|\s+$/g, ''); }
    /* 搜索框 / 空结果文案里那句槽位数：也改成运行时实数（免得下次加槽又过期） */
    try{
      var q = document.getElementById('toc2q');
      if(q) q.setAttribute('placeholder', '只在档位推荐里搜（' + n() + ' 个槽位）：配方名 / 作者 / 场景，如 人像、夜景、Portra…');
      var nr = document.getElementById('noresult2');
      if(nr) nr.textContent = '档位推荐 ' + n() + ' 个槽位里没找到匹配的。试试「人像」「夜景」「复古」，或者只搜一个字；想看全站配方请到「配方合集」页签搜。';
    }catch(e){}
    var box = document.getElementById('toc2tiers');
    if(!box || box.getAttribute('data-r47built') === '1') return;      /* 幂等：只建一次 */
    var modes = document.querySelectorAll('.omode');
    var h = [];
    for(var i = 0; i < modes.length; i++){
      var m = modes[i], id = m.id || '';
      if(!/^oC\d+$/.test(id)) continue;
      var tag = m.querySelector('.omtag'), ti = m.querySelector('.omtitle');
      var nm = trim((tag ? tag.textContent : '') + ' ' + (ti ? ti.textContent : '')) || id;
      h.push('<a class="lv2" href="#' + id + '">' + esc47(nm) + '</a>');
      var os = m.querySelectorAll('.oslot[id^="oC"]');
      for(var j2 = 0; j2 < os.length; j2++){
        var o = os[j2], oid = o.id || '';
        if(oid.indexOf(id + '-') !== 0) continue;              /* 只认这一档自己的槽 */
        var sn = o.querySelector('.osname');
        var lb = esc47(trim(sn ? sn.textContent : '') || oid);
        h.push('<a class="lv3" href="#' + oid + '">' + (/-m\d+$/.test(oid) ? ('MONO · ' + lb) : ((j2 + 1) + '. ' + lb)) + '</a>');
      }
    }
    box.innerHTML = '<div class="tgh">10 个候选档（挑 5 个）</div>' + h.join('');
    box.setAttribute('data-r47built', '1');
  })();
"""
OLD_TAIL08 = "  }, true);\n})();\n</script>\n</body></html>"
NEW_TAIL08 = "  }, true);\n" + TOC_SYNC + "})();\n</script>\n</body></html>"
rep(OLD_TAIL08, NEW_TAIL08, '块08：目录候选项组运行时生成（含槽位数文案）')

# ================================================================ F) 块07：整个档位存入我的配方
NEW_FEATURE = r"""  /* ===== 第 47 轮：档位推荐 → 每个候选档一个「整个档位存入我的配方」 =====
     用户原话：「我需要能够在档位推荐中，整个档位存入我的配方中的新建档位中，名称也继承过去。」
     用户选的做法：**先弹确认框**（方案名预填档位名、可改；写回相机的档位可挑），确认后
     新建一套方案（名字继承），把这一档的槽位整份填进去。 */

  /* 一个 .oslot → 配方对象（rec）。
     ⚠ 数值**只从页面上读**（.ovc 的 12 格 + 参数行）：① 页面显示什么就是什么；
       ② 「白里透红」那两格是本站自配，__OM3RECIPES__ 里根本没有；
       ③ 按名字查库会错配（库里有两条 Portra 400）。 */
  function pick47(t, re){ var m = re.exec(t); return m ? m[1] : ''; }
  /* 页面上有的负号是 U+2212（−）、不是 ASCII 的 -：统一成 ASCII 再取数 */
  function num47(x){ return Number(String(x === undefined || x === null ? '' : x).replace(/[−–—]/g, '-')) || 0; }
  function trim47(t){ return String(t == null ? '' : t).replace(/^\s+|\s+$/g, ''); }
  function recFromOslot(el){
    if(!el) return null;
    try{
      var bs = el.querySelectorAll('.osvals .ovc b'), v = [];
      for(var i = 0; i < bs.length && i < 12; i++) v.push(num47(bs[i].textContent));
      if(v.length < 12) return null;
      var prm = el.querySelector('.osline.prm');
      var t = String(prm ? (prm.textContent || '') : '');
      var nm = el.querySelector('.osname'), au = el.querySelector('.osauth');
      return { n: trim47(nm ? nm.textContent : ''), a: trim47(au ? au.textContent : ''), v: v,
               hi:  num47(pick47(t, /Hi\s*([+-]?\d+)/)),
               mid: num47(pick47(t, /Mid\s*([+-]?\d+)/)),
               sh:  num47(pick47(t, /Sh\s*([+-]?\d+)/)),
               eff: num47(pick47(t, /(?:阴影补偿|阴影效果)\s*([+-]?\d+)/)),
               shp: num47(pick47(t, /锐度\s*([+-]?\d+)/)),
               con: num47(pick47(t, /对比\s*([+-]?\d+)/)) };
    }catch(e){ om3err(e, 'recFromOslot'); return null; }
  }
  /* 档位卡里"要塞进方案"的槽：只认 oC<档>-<1..4>；MONO 槽（oC1-m1）不进 —— 方案只有 4 个 C 槽位 */
  function tierSlots47(m){
    var out = [], os = m.querySelectorAll('.oslot[id^="oC"]');
    for(var i = 0; i < os.length; i++){
      var mm = /^oC(\d+)-(\d+)$/.exec(os[i].id || '');
      if(mm) out.push({ n: Number(mm[2]), el: os[i] });
    }
    return out;
  }
  function tierMono47(m){
    var out = [], os = m.querySelectorAll('.oslot[id^="oC"]');
    for(var i = 0; i < os.length; i++) if(/-m\d+$/.test(os[i].id || '')) out.push(os[i]);
    return out;
  }
  function tierName47(m){
    var tag = m.querySelector('.omtag'), ti = m.querySelector('.omtitle');
    return trim47((tag ? tag.textContent : '') + ' ' + (ti ? ti.textContent : '')) || (m.id || '候选档');
  }
  /* C1–C5 直接对应相机上的 C1–C5；C6–C10 相机上没有这一档 → 先记「当前状态」 */
  function tierDefaultCam47(m){
    var r = /^oC([1-5])$/.exec(m.id || '');
    return r ? ('myset' + r[1]) : 'current';
  }

  /* 每个候选档注入一个按钮（幂等：有 .omtierbtn 就跳过；不改卡片 HTML → 重跑生成器也不会被冲掉） */
  function injectTierBtns(){
    try{
      var modes = document.querySelectorAll('.omode');
      for(var i = 0; i < modes.length; i++){
        (function(m){
          if(!/^oC\d+$/.test(m.id || '')) return;
          if(m.querySelector('.omtierbtn')) return;
          var body = m.querySelector('.ombody') || m;
          var wrap = document.createElement('div');
          wrap.className = 'omstore';
          var b = document.createElement('button');
          b.type = 'button';
          b.className = 'omtierbtn';
          b.textContent = '整个档位存入我的配方';
          b.addEventListener('click', function(ev){
            try{ ev.stopPropagation(); ev.preventDefault(); }catch(x){}
            askTierToSets(m);
          });
          var hint = document.createElement('span');
          hint.textContent = '新建一套方案，方案名跟着这一档走；之后在「我的配方 → 方案」里点它，就能整套写入相机。';
          wrap.appendChild(b); wrap.appendChild(hint);
          body.insertBefore(wrap, body.firstChild);
        })(modes[i]);
      }
    }catch(e){ log('注入「整个档位存入我的配方」失败：' + (e && e.message ? e.message : e), 'err'); }
  }

  /* 确认框 → 建方案 → 整档填进去 */
  function askTierToSets(m){
    if(!m){ log('没找到这个候选档（页面结构变了？）', 'err'); return; }
    var slots = tierSlots47(m), recs = [], miss = [];
    for(var i = 0; i < slots.length; i++){
      var r = recFromOslot(slots[i].el);
      if(r && r.v && r.v.length === 12) recs.push({ n: slots[i].n, rec: r, el: slots[i].el });
      else miss.push(slots[i].el.id);
    }
    var monos = tierMono47(m);
    var nm47 = tierName47(m), cam47 = tierDefaultCam47(m);
    var wbEl = m.querySelector('.omchip.wb');
    var wb47 = trim47(wbEl ? wbEl.textContent : '');
    if(!recs.length){
      log('⚠ 「' + nm47 + '」里没有一个槽能读出 12 个色轴值 → 这一档存不了，一套方案都没建。', 'warn');
      toastMsg('这一档没有可存的数据');
      return;
    }
    var tiers = mpTierOptions(), has47 = false;
    for(var k = 0; k < tiers.length; k++) if(tiers[k].value === cam47) has47 = true;
    var extra = [];
    if(monos.length){
      var mnm = [];
      for(var q = 0; q < monos.length; q++){
        var sn = monos[q].querySelector('.osname');
        mnm.push(trim47(sn ? sn.textContent : '') || monos[q].id);
      }
      extra.push('MONO 槽（' + mnm.join('、') + '）不进方案：方案只有 4 个 C 槽位，黑白挂在拨盘的 MONO 档上。');
    }
    if(miss.length) extra.push('有 ' + miss.length + ' 个槽读不到色轴数据（' + miss.join('、') + '）→ 会跳过。');
    if(recs.length < 4) extra.push('这一档只有 ' + recs.length + ' 个槽有数据，方案里剩下的槽留空。');
    var dup = 0;
    try{ dup = setsAll().filter(function(x){ return x && x.name === nm47; }).length; }catch(e){ om3err(e, 'silent'); }
    if(dup) extra.push('已经有一套叫「' + nm47 + '」的方案了 —— 这次会再建一套（不覆盖它）。');
    om3Ask({
      title: '整个档位存入我的配方',
      body: '把「' + nm47 + '」这一档的 ' + recs.length + ' 个槽整份存成一套新方案（12 个色轴值 + 影调 6 项 + 页面上那几行描述都会一起带过去）。'
            + (extra.length ? ('　' + extra.join('　')) : ''),
      fields: [
        { label: '方案名字（默认跟着这一档，可改）', value: nm47 },
        { label: '写回相机时写到哪个档位', options: tiers, value: has47 ? cam47 : 'myset1' }
      ],
      okText: '存入我的配方'
    }).then(function(r){
      if(!r || !r.length) return;                       /* 取消 → 一套都不建 */
      storeTierToSets(m, trim47(r[0]) || nm47, String(r[1] || cam47), wb47, recs);
    });
  }

  /* 真正落盘：新建一套方案 → 逐槽复用 putRecInSlot（**唯一那份**实现，字段与「加入我的方案」完全同构） */
  function storeTierToSets(m, name, tier, wb, recs){
    var arr = setsAll();
    arr.push({ id: 's' + Date.now(), name: name, desc: '来自档位推荐 · ' + (wb || tierLabel(tier)),
               from: tier, at: '', camera: modelNow(), slots: { 1: null, 2: null, 3: null, 4: null } });
    if(!setsSave(arr)) return false;
    var idx = arr.length - 1;
    log('✅ 已按「' + name + '」建好一套新方案（档位 ' + tierLabel(tier) + '），准备把这一档整份填进去…', 'ok');
    var ok = 0, bad = [];
    for(var i = 0; i < recs.length; i++){
      var rec = recs[i].rec;
      var done = putRecInSlot(idx, recs[i].n, rec, rec.n || ('槽' + recs[i].n), '来自档位推荐', richFromCard(recs[i].el));
      if(done === false) bad.push('槽' + recs[i].n); else ok++;
    }
    if(bad.length) log('⚠ 这几个槽没填进去：' + bad.join('、') + '（放在上面写清楚了，不静默）', 'warn');
    log('　→ 已存入「我的配方」：方案「' + name + '」 · 填好 ' + ok + '/' + recs.length + ' 个槽；'
        + '到「我的配方 → 方案」能看到它，详情页最上面那个按钮能把整套写进相机。', 'ok');
    toastMsg('已存入我的配方：' + name + '（' + ok + ' 个槽）');
    try{ mpRender(); }catch(e){ om3err(e, 'silent'); }
    return true;
  }
"""
# ⚠ 幂等判定不能用"NEW_FEATURE 整段在不在"：后面那两个小改（导出 recFromOslot、负号统一）
#   会插进这一段里 ⇒ 整段文本不再连续 ⇒ 会被误判成"没改过"而**再插一份**
#   （第 47 轮自己踩到过，记在 SPEC-round47 §6）。所以用"有没有 storeTierToSets 这个函数"来判。
FEATURE_MARK = '  function storeTierToSets(m, name, tier, wb, recs){'
if FEATURE_MARK in s:
    LOG.append('  · 已改过，跳过：块07：「整个档位存入我的配方」按钮 + 确认框 + 建方案 + 整档填槽')
else:
    _old_save = '  window.__om3saveCard = saveCardToSets;'
    assert s.count(_old_save) == 1, '!! 锚点不唯一：window.__om3saveCard'
    s = s.replace(_old_save, NEW_FEATURE + _old_save, 1)
    LOG.append('  ✅ 块07：「整个档位存入我的配方」按钮 + 确认框 + 建方案 + 整档填槽')

rep('  /* 确认框 → 建方案 → 整档填进去 */',
    '  window.__om3recFromOslot = recFromOslot;          /* r47：给验收脚本用（页面 → 配方对象的解析） */\n'
    '  /* 确认框 → 建方案 → 整档填进去 */',
    '块07：导出 recFromOslot 供验收')

rep("      var t = String(prm ? (prm.textContent || '') : '');",
    "      /* ⚠ 参数行里有的负号是 U+2212（−）、不是 ASCII 的 -：不先统一，/Hi\\s*([+-]?\\d+)/ 就匹配不上，\n"
    "         Hi 会被当成 0。这条是第 47 轮自己踩到的 —— dv_r47 里\"页面 vs 库\"的交叉验抓出来的\n"
    "         （白里透红那两格写的是 'Hi −2'）。 */\n"
    "      var t = String(prm ? (prm.textContent || '') : '').replace(/[−–—]/g, '-');",
    '块07：recFromOslot 解析前统一负号（U+2212 → ASCII -）')

rep("      log('配方卡「加入我的方案」按钮已就绪（' + cards.length + ' 张卡）');",
    "      log('配方卡「加入我的方案」按钮已就绪（' + cards.length + ' 张卡）');\n"
    "      injectTierBtns();                       /* r47：候选档卡上那个「整个档位存入我的配方」 */",
    '块07：injectMineBtns 里顺带注入档位按钮（幂等）')

# ================================================================ 写出
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n'.join(LOG))
print('写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))

# ================================================================ 自检
print('\n=== 自检 ===')
S = io.open(P, encoding='utf-8').read()
ids = set(re.findall(r'\bid="([^"]+)"', S))
print('死锚点：', sorted(l for l in set(re.findall(r'href="#([^"]+)"', S)) if l not in ids and "'" not in l) or '无')
print('还有 "21 个槽位"：', S.count('21 个槽位'))
print('还有手写的"五个档位"：', S.count('五个档位'))
print('__om3tocClose 出现：', S.count('__om3tocClose'))
print('omtierbtn 出现：', S.count('omtierbtn'))
print('toc2tiers 出现：', S.count('toc2tiers'))
