# -*- coding: utf-8 -*-
"""第 40 轮（用户反馈）：
  ① 「下拉用的安卓原生的太丑了」 → 原生 <select> 藏起来当"逻辑源"，上面盖一个**自绘下拉**（自绘面板/分组/选中态）
  ② 「场景一次性能滑动好几个」   → 原来是靠 `scroll-snap-type:x mandatory` 交给浏览器 + 140ms 防抖事后拉回，
     一甩到底就拦不住。改成**手势级**：touchstart/end 判方向，自己滚**恰好一格**。
  ③ 「滑完了会自动回到第一个」   → 元凶：`scStepW()` 在页签隐藏/未布局时量到宽度 0，于是返回 `0+12=12`
     （假有效值）→ `scrollLeft = (scLast±1)*12 ≈ 12px` → 正好是第一张。
     修：量不到有效宽度（<40）或 pager 不可见时**直接不动作**；索引以我们自己的 scLast 为准，并夹在 [0, n-1]。
"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()
n = 0

# ---------------- ① 自绘下拉 ----------------
old_sel = ('<div class="scselwrap">'
           '<label class="scsellab" for="scsel">看哪个场景</label>'
           '<select id="scsel" class="scsel" aria-label="选择场景">')
new_sel = ('<div class="scselwrap">'
           '<label class="scsellab" for="scsel">看哪个场景</label>'
           # 自绘按钮 + 面板（原生 select 藏在下层，只当"逻辑源"）
           '<button type="button" class="scselbtn" id="scselbtn" aria-haspopup="listbox" aria-expanded="false">'
           '<span class="scseltxt" id="scseltxt">实拍对比</span><span class="scselcar">▾</span></button>'
           '<div class="scmenu" id="scmenu" role="listbox" aria-label="选择场景"></div>'
           '<select id="scsel" class="scselnative" aria-label="选择场景（原生控件，仅作逻辑源）" tabindex="-1">')
assert s.count(old_sel) == 1, '下拉锚点 %d' % s.count(old_sel)
s = s.replace(old_sel, new_sel, 1); n += 1

# CSS：原生 select 视觉隐藏；自绘按钮/面板做成深色卡片风
css = ('\n/* 第 40 轮：场景下拉改成**自绘**（原生控件太丑，只留作逻辑源） */\n'
       '.scselnative{position:absolute!important;width:1px!important;height:1px!important;opacity:0!important;'
       'pointer-events:none!important;left:-9999px!important}\n'
       '.scselbtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(180deg,#232b30,#1d2327);'
       'color:#eaf6f1;border:1px solid #2f8f74;border-radius:12px;padding:13px 14px;font-size:15px;font-weight:600;'
       'font-family:inherit;box-shadow:0 2px 10px rgba(0,0,0,.35)}\n'
       '.scselbtn:active{background:#263039}\n'
       '.scselbtn .scseltxt{flex:1 1 auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n'
       '.scselbtn .scselcar{flex:0 0 auto;color:#7ed3bd;font-size:14px;transition:transform .18s}\n'
       '.scselbtn[aria-expanded="true"] .scselcar{transform:rotate(180deg)}\n'
       '.scselbtn[aria-expanded="true"]{border-color:#7ed3bd;box-shadow:0 0 0 3px rgba(47,143,116,.25)}\n'
       '.scmenu{display:none;position:absolute;left:0;right:0;top:calc(100% - 4px);z-index:60;background:#1c2226;'
       'border:1px solid #2f8f74;border-radius:12px;box-shadow:0 14px 34px rgba(0,0,0,.55);max-height:58vh;overflow-y:auto;'
       'padding:6px;-webkit-overflow-scrolling:touch}\n'
       '.scmenu.open{display:block}\n'
       '.scmenu .scg{font-size:11.5px;color:#7ed3bd;font-weight:700;letter-spacing:.4px;padding:9px 10px 5px;opacity:.85}\n'
       '.scmenu button{display:flex;align-items:center;gap:8px;width:100%;text-align:left;background:transparent;color:#e6e6e6;'
       'border:0;border-radius:9px;padding:11px 10px;font-size:14px;font-family:inherit;line-height:1.35}\n'
       '.scmenu button:active{background:#2a3a36}\n'
       '.scmenu button.on{background:#26443c;color:#fff;font-weight:700}\n'
       '.scmenu button .ck{margin-left:auto;color:#7ed3bd;font-size:13px}\n'
       '.scmenu button .sub{color:#8d8d8d;font-size:11.5px;margin-left:6px}\n')
assert s.count('</style>') >= 1
s = s.replace('</style>', css + '</style>', 1); n += 1

# ---------------- ②③ 重写翻页逻辑 ----------------
i0 = s.find('    /* ===== 一次滑动只换一张')
i1 = s.find("    window.addEventListener('resize', function () { setTimeout(upd, 60); });", i0)
assert i0 > 0 and i1 > i0, '翻页逻辑段落定位失败'
new_js = r"""    /* ===== 第 40 轮：一屏一张、一次手势只换一张（自己控制，不交给 scroll-snap）=====
       为什么重写：原来把翻页交给 CSS `scroll-snap-type:x mandatory`，再用 140ms 防抖"事后拉回"——
       一甩到底根本拦不住（用户："一次性能滑动好几个"）。而且旧代码 `scStepW()` 在页签隐藏/未布局时
       量到宽度 0 会返回 `0+12=12` 这个假有效值，`scrollLeft=(scLast±1)*12≈12px` 正好是**第一张** ——
       这就是用户报的"滑完了自动回到第一个"。现在：量不到有效宽度或 pager 不可见 → 直接不动作。 */
    var scLast = 0;
    function scStepW() {
      var s0 = pager.querySelector('.scslide');
      if (!s0) return 0;
      var w = s0.getBoundingClientRect().width;
      if (!(w > 40)) return 0;                  /* 隐藏/未布局：0 或极小 → 视为无效，别拿它算 */
      var gap = 12;
      if (pager.scrollWidth > pager.clientWidth + 4) {
        var per = Math.max(1, Math.round((pager.clientWidth + gap) / (w + gap)));
        return (pager.clientWidth + gap) / per - gap + gap;   /* 一"屏"的步长（手机=一张） */
      }
      return w + gap;
    }
    function scCount() { return (SC[cur] && SC[cur].items) ? SC[cur].items.length : 0; }
    function scGo(i, smooth) {
      if (!pager.offsetParent) return;          /* 页签不可见 → 不动作（避免隐藏时把自己拽走） */
      var st = scStepW(); if (!st) return;
      var cnt = scCount(); if (!cnt) return;
      i = Math.max(0, Math.min(cnt - (perView() > 1 ? perView() : 1), i));
      var left = i * st;
      try { pager.scrollTo({ left: left, behavior: smooth ? 'smooth' : 'auto' }); }
      catch (e) { pager.scrollLeft = left; }
      scLast = i; upd();
    }
    window.__scGo = scGo;
    var scX0 = null, scY0 = null, scMoved = false;
    pager.addEventListener('touchstart', function (e) {
      if (e.touches.length !== 1) { scX0 = null; return; }
      scX0 = e.touches[0].clientX; scY0 = e.touches[0].clientY; scMoved = false;
    }, { passive: true });
    pager.addEventListener('touchmove', function (e) {
      if (scX0 == null || e.touches.length !== 1) return;
      var dx = e.touches[0].clientX - scX0, dy = e.touches[0].clientY - scY0;
      if (Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(dy)) scMoved = true;
    }, { passive: true });
    pager.addEventListener('touchend', function (e) {
      if (scX0 == null) return;
      var x0 = scX0; scX0 = null;
      if (!scMoved) return;                     /* 轻点不翻页（点图是全屏放大） */
      var t = (e.changedTouches && e.changedTouches[0]) ? e.changedTouches[0].clientX : x0;
      var dx = t - x0;
      if (Math.abs(dx) < 24) return;
      scGo(scLast + (dx < 0 ? 1 : -1), true);   /* 一次手势**只走一格** */
    }, { passive: true });
    /* 鼠标滚轮横滚（桌面/平板）也按一格走 */
    pager.addEventListener('wheel', function (e) {
      var dx = e.deltaX, dy = e.deltaY;
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 4) {
        e.preventDefault();
        clearTimeout(pager._wt);
        pager._wt = setTimeout(function () { scGo(scLast + (dx > 0 ? 1 : -1), true); }, 40);
      }
    }, { passive: false });
    pager.addEventListener('scroll', function () { clearTimeout(pager._t); pager._t = setTimeout(upd, 90); }, false);
    document.getElementById('scprev').addEventListener('click', function () { scGo(scLast - 1, true); });
    document.getElementById('scnext').addEventListener('click', function () { scGo(scLast + 1, true); });
"""
s = s[:i0] + new_js + s[i1:]; n += 1

# build() 里同步 scLast（原来只 try{scLast=0}）
s = s.replace("      pager.scrollLeft = 0;\n      try { scLast = 0; } catch (e0) {}",
              "      pager.scrollLeft = 0;\n      try { scLast = 0; } catch (e0) {}\n      if (window.__scGo) { try { scLast = 0; } catch (e0) {} }", 1)

# ---------------- 自绘下拉的运行时（在 select 的 change 之后接上）----------------
anchor = "    var scsel = document.getElementById('scsel');\n    if (scsel) {"
add = r"""    /* ===== 第 40 轮：自绘下拉（原生 select 只当逻辑源，任何改 value 都走它的 change）===== */
    (function () {
      var btn = document.getElementById('scselbtn'), menu = document.getElementById('scmenu'),
          txt = document.getElementById('scseltxt'), sel = document.getElementById('scsel');
      if (!btn || !menu || !sel) return;
      function render() {
        var h = '';
        var groups = sel.querySelectorAll('optgroup');
        for (var g = 0; g < groups.length; g++) {
          h += '<div class="scg">' + groups[g].getAttribute('label') + '</div>';
          var op = groups[g].querySelectorAll('option');
          for (var i = 0; i < op.length; i++) {
            h += '<button type="button" role="option" data-v="' + op[i].value + '">' + op[i].textContent +
                 (op[i].value === sel.value ? '<span class="ck">✓</span>' : '') + '</button>';
          }
        }
        menu.innerHTML = h;
      }
      function label() { var o = sel.options[sel.selectedIndex]; txt.textContent = o ? o.textContent : '看哪个场景'; }
      function open(v) {
        menu.classList.toggle('open', !!v);
        btn.setAttribute('aria-expanded', v ? 'true' : 'false');
        if (v) { render(); var on = menu.querySelector('button.on') || menu.querySelector('button'); }
      }
      btn.addEventListener('click', function (e) { e.stopPropagation(); open(!menu.classList.contains('open')); });
      menu.addEventListener('click', function (e) {
        var b = e.target.closest ? e.target.closest('button[data-v]') : null;
        if (!b) return;
        e.stopPropagation();
        sel.value = b.getAttribute('data-v');
        label();
        open(false);
        sel.dispatchEvent(new Event('change', { bubbles: true }));
      });
      document.addEventListener('click', function () { if (menu.classList.contains('open')) open(false); });
      sel.addEventListener('change', label);
      label(); render();
      window.__scMenu = { open: open, render: render };
    })();
"""
assert s.count(anchor) == 1, '自绘下拉接入点 %d' % s.count(anchor)
s = s.replace(anchor, add + anchor, 1); n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('✅ 第 40 轮已改 %d 处：自绘下拉 + 手势级翻页（一格一张 / 隐藏时不动作）' % n)
