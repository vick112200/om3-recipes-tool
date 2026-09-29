# -*- coding: utf-8 -*-
"""第 41 轮（用户反馈：「滑动还是不行，回到最初那版，只把滑动换成最初对比的那个」）：

做法 —— **把 JS 拦滚动整套删掉，回到最初那版原生滑动**：
  · 翻页 = 浏览器原生拖动 + CSS `scroll-snap-type:x mandatory`（最初那版就是这套）
  · `scroll` 事件只用来**更新位置标签**（"3 – 3 / 50"），不碰 scrollLeft
  · `‹ ›` 按钮回到最初那种"翻一屏"：`scrollBy({left: ±(clientWidth+12)})`
  · 删掉：touchstart/touchmove/touchend 手势、wheel 拦、scGo 强制落点、380ms 兜底 —— 这些会跟原生拖动打架

同时保留"一次滑一张"的诉求，但改用**纯 CSS、原生**的方式：
  `.scslide{scroll-snap-stop:always}`  ← 浏览器自己就会在一次滑动里**只停一个吸附点**，
  不需要 JS 介入（Chrome/Android WebView 75+ 支持；不支持就退化成自由滚，也就是最初那版行为，不会坏）。
"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()

# ---------- ① 删掉整套 JS 手势，换成最初那版 ----------
i0 = s.find('    /* ===== 第 40 轮：一屏一张、一次手势只换一张')
i1 = s.find("    window.addEventListener('resize', function () { setTimeout(upd, 60); });", i0)
assert i0 > 0 and i1 > i0, '手势段落定位失败 (%d,%d)' % (i0, i1)
orig = r"""    /* ===== 滑动：**回到最初那版**（用户 2026-09-24「滑动还是不行，回到最初那版」）=====
       最初那版 = 浏览器原生拖动 + CSS `scroll-snap-type:x mandatory`，JS 只做两件事：
         · scroll 事件里更新位置标签（不碰 scrollLeft）
         · ‹ › 按钮翻一屏
       第 40 轮我加的手势拦截（touchstart/end + 强制落点 + 380ms 兜底）会把原生拖动顶掉，
       真机上表现为"滑不动" —— 所以整套删掉。
       "一次只换一张"改用纯 CSS：`.scslide{scroll-snap-stop:always}`（原生吸附，不拦手势）。 */
    var scLast = 0;
    pager.addEventListener('scroll', function () {
      clearTimeout(pager._t);
      pager._t = setTimeout(function () {
        var s0 = pager.querySelector('.scslide');
        var w = s0 ? s0.getBoundingClientRect().width : 0;
        if (w > 40) scLast = Math.round(pager.scrollLeft / (w + 12));   /* 只记账，不滚动 */
        upd();
      }, 90);
    }, false);
    document.getElementById('scprev').addEventListener('click', function () { pager.scrollBy({ left: -pager.clientWidth - 12, behavior: 'smooth' }); });
    document.getElementById('scnext').addEventListener('click', function () { pager.scrollBy({ left: pager.clientWidth + 12, behavior: 'smooth' }); });
"""
s = s[:i0] + orig + s[i1:]

# ② 暴露给探针的 __scIdx / __scGo：保留 __scIdx（纯读取），去掉会滚动的 __scGo
s = s.replace("    window.__scGo = scGo;\n    window.__scIdx = function () { return scLast; };   /* 给探针：当前索引（逻辑值） */",
              "    window.__scIdx = function () { return scLast; };   /* 给探针：当前索引（只读，不滚动） */")

# ---------- ③ CSS：原生吸附"一次只停一张" ----------
old_css = '.scslide{flex:0 0 100%;scroll-snap-align:start;background:#1c1c1c;border:1px solid #2e2e2e;border-radius:12px;overflow:hidden}'
new_css = ('.scslide{flex:0 0 100%;scroll-snap-align:start;scroll-snap-stop:always;background:#1c1c1c;'
           'border:1px solid #2e2e2e;border-radius:12px;overflow:hidden}\n'
           '/* 第 41 轮：`scroll-snap-stop:always` = 浏览器自己保证"一次滑动只停一个吸附点"，'
           '纯 CSS、不拦手势（不支持就退化成自由滚，不会坏） */')
assert s.count(old_css) == 1, 'slide CSS 锚点 %d' % s.count(old_css)
s = s.replace(old_css, new_css, 1)

# ④ 提示文案：说明现在怎么滑
s = s.replace('左右滑动一次换一张</span>', '左右滑动自由翻（原生吸附，不会一甩跳好几张）</span>')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('✅ 已回到最初那版原生滑动：JS 手势整套删除 + scroll-snap-stop:always')
print('   还剩这些引用检查：__scGo=%d 个（应为 0）' % s.count('__scGo'))
