# -*- coding: utf-8 -*-
"""第 42 轮：`dv_r33` 里那 3 条「滑动夹取」断言已过期 —— 第 41 轮按用户要求
「回到最初那版」把 JS 夹取整套删了（改成原生吸附 + CSS `scroll-snap-stop:always`）。
这里把它们换成现在的契约：**不再有 JS 夹取**、一次滑动由 CSS 原生保证只停一张。
"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\workspace\om3-handbook\scripts\dv_r33.py'
s = io.open(p, encoding='utf-8').read()
reps = [
 ("ok(calls.indexOf(st * per) >= 0, '★一下滑过 5 屏 → 被夹回\"只跨一屏\"（目标第 ' + per + ' 屏）');",
  "ok(calls.length === 0, '★第 41 轮起：**不再有 JS 夹取**（一下滑过 5 屏时 JS 不得动 scrollLeft；实测调用 ' + calls.length + ' 次）');"),
 ("ok(calls.indexOf(st * per * 2) >= 0, '★夹取按\"上次位置 ± 一屏\"算，不会一路弹回开头（目标第 ' + (per * 2) + ' 屏）');",
  "ok(calls.length === 0, '★同上：JS 全程不干预（调用 ' + calls.length + ' 次）');"),
 ("ok(calls.length === 0, '★正常跨一屏不触发夹取（不乱动用户的位置）');",
  "ok(('scroll-snap-stop:always' in __import__('io').open(r'D:\\workspace\\om3-handbook\\app\\base.html', encoding='utf-8').read()), '★\"一次只停一张\"改由 CSS `scroll-snap-stop:always` 保证（不再用 JS）');"),
]
n = 0
for a, b in reps:
    if a in s:
        s = s.replace(a, b, 1); n += 1
    else:
        print('  ⚠ 没找到：%s' % a[:60])
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('dv_r33 已更新 %d 处（夹取 → 原生吸附契约）' % n)
