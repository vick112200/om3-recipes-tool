# -*- coding: utf-8 -*-
"""第 40 轮补充：
 ① `scGo` 的落点要有保障 —— `scrollTo({behavior:'smooth'})` 在部分环境（headless、snap 容器）会被吞掉，
    加一个 380ms 兜底：还没到位就**直接跳**到目标位。
 ② 暴露 `window.__scIdx()`（当前索引），让探针能分别验证「逻辑」与「动画落点」。
 ③ 探针改成：逻辑用 __scIdx 断言，落点用 scrollLeft 断言（带容差），并等更久。
"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()
old = """      var left = i * st;
      try { pager.scrollTo({ left: left, behavior: smooth ? 'smooth' : 'auto' }); }
      catch (e) { pager.scrollLeft = left; }
      scLast = i; upd();"""
new = """      var left = i * st;
      try { pager.scrollTo({ left: left, behavior: smooth ? 'smooth' : 'auto' }); }
      catch (e) { pager.scrollLeft = left; }
      if (smooth) {
        /* 第 40 轮兜底：某些环境（headless / snap 容器）会吞掉 smooth 滚动 → 380ms 后还没到位就直接跳。
           没有这一步，用户会看到"滑了没动"或"停在半路"。 */
        (function (want, step) {
          setTimeout(function () {
            if (Math.abs(pager.scrollLeft - want) > Math.max(8, step * 0.35)) {
              try { pager.scrollLeft = want; } catch (e2) {}
              upd();
            }
          }, 380);
        })(left, st);
      }
      scLast = i; upd();"""
assert s.count(old) == 1, 'scGo 锚点 %d' % s.count(old)
s = s.replace(old, new, 1)
old2 = "    window.__scGo = scGo;"
assert s.count(old2) == 1
s = s.replace(old2, old2 + "\n    window.__scIdx = function () { return scLast; };   /* 给探针：当前索引（逻辑值） */", 1)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('✅ scGo 已加落点兜底 + 暴露 __scIdx')

# 探针：逻辑断言用 __scIdx，落点断言放大等待
Q = r'D:\workspace\om3-handbook\scripts\dv_scene40.py'
t = io.open(Q, encoding='utf-8').read()
t = t.replace("    setTimeout(cb, 620);", "    setTimeout(cb, 1100);")
t = t.replace("ok(i1 === 1, '② **一次手势只换一张**：idx 0 → ' + i1 + '（' + pos() + '）');",
              "var L1 = window.__scIdx();\n            ok(L1 === 1 && Math.abs(pg.scrollLeft - st1) < 40,\n               '② **一次手势只换一张**：逻辑 idx ' + i1 + ' / 内部 ' + L1 + ' / 落点 ' + Math.round(pg.scrollLeft) + '（' + pos() + '）');")
t = t.replace("          var total = document.querySelectorAll('#scpager .scslide').length;",
              "          var total = document.querySelectorAll('#scpager .scslide').length;\n          var st1 = 0;\n          (function(){ var s1 = pg.querySelector('.scslide'); st1 = s1 ? (s1.getBoundingClientRect().width + 12) : 0; })();")
t = t.replace("ok(i3 === 3, '② 连续三次手势 → 第 4 张（idx=' + i3 + '）');",
              "ok(i3 === 3 && window.__scIdx() === 3, '② 连续三次手势 → 第 4 张（idx=' + i3 + ' / 内部 ' + window.__scIdx() + '）');")
t = t.replace("ok(idx() === 2, '② 反向滑一次 → 回第 3 张（idx=' + idx() + '）');",
              "ok(idx() === 2 && window.__scIdx() === 2, '② 反向滑一次 → 回第 3 张（idx=' + idx() + ' / 内部 ' + window.__scIdx() + '）');")
io.open(Q, 'w', encoding='utf-8', newline='').write(t)
print('✅ 探针已改（逻辑/落点分开断言）')
