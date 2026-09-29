# -*- coding: utf-8 -*-
"""第 39 轮：第 37 轮探针里针对「场景索引列表(#scidx)」的断言，已由 #scsel 下拉取代 ——
把这些断言改成**新 UI 的等价断言**（并且因为 #scidx 现在是注释掉的，不能再去查它的 DOM）。"""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\workspace\om3-handbook\scripts\dv_r37.py'
s = io.open(p, encoding='utf-8').read()

s = s.replace("A('id=\"scidxbar\"' in src and 'id=\"scidxlist\"' in src, '④ 场景索引容器 #scidxbar / #scidxlist 在')",
              "A('<select id=\"scsel\"' in src and 'window.__OM3SC__' in src,\n"
              "  '④ 第 39 轮起：场景索引列表(#scidx)已由 **#scsel 下拉 + __OM3SC__ 表**取代')")

# 运行时那一段（#scidxlist/.scidxrow 相关）→ 换成 select + 表
i = s.find("    var chips = document.querySelectorAll('#scidxbar button');")
j = s.find("    /* ⑥ 跳转/高亮", i)
if j < 0:
    j = s.find("    ok(window.__errs.length === 0", i)
assert i > 0 and j > i, '运行时段落定位失败'
new = r"""    /* 第 39 轮：#scidx 列表已换成 #scsel 下拉；场景数据在 window.__OM3SC__ 里 */
    var sel4 = document.getElementById('scsel');
    ok(!!sel4, '④ #scsel 下拉在');
    ok(sel4 && sel4.options.length === 27, '④ 下拉 27 项（6 实拍 + 21 场景，实测 ' + (sel4 ? sel4.options.length : -1) + '）');
    var TB = window.__OM3SC__ || [];
    ok(TB.length === 21, '④ __OM3SC__ 21 个场景（实测 ' + TB.length + '）');
    var zero = [];
    for (var q4 = 0; q4 < TB.length; q4++) if (!TB[q4].items || !TB[q4].items.length) zero.push(TB[q4].k);
    ok(zero.length === 0, '④ 每个场景都有条目（空场景：' + JSON.stringify(zero) + '）');
    var sum = 0, withImg = 0;
    for (var q5 = 0; q5 < TB.length; q5++) for (var q6 = 0; q6 < TB[q6 === 0 ? 0 : q5].items.length; q6++) {
      sum++; if (TB[q5].items[q6].f) withImg++;
    }
    ok(sum > 0 && withImg === sum, '④ 场景条目 ' + sum + ' 条，**每条都带图**（' + withImg + '/' + sum + '）');
    var multi = 0, seen = {};
    for (var q7 = 0; q7 < TB.length; q7++) for (var q8 = 0; q8 < TB[q7].items.length; q8++) {
      var hh = TB[q7].items[q8].i; if (hh) seen[hh] = (seen[hh] || 0) + 1;
    }
    for (var kk2 in seen) if (seen[kk2] > 1) multi++;
    ok(multi > 50, '④ 一条配方可属多个场景（' + multi + ' 条进了 ≥2 个场景）');
    var b0 = document.querySelector('#scpager .scjump');
    ok(!!b0, '④ 场景 slide 里有跳转按钮（data-jump）');
"""
s = s[:i] + new + s[j:]
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('dv_r37.py 的场景断言已换成新 UI')
