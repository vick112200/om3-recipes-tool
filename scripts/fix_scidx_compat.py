# -*- coding: utf-8 -*-
"""第 39 轮：给 window.__om3scIdx 加向后兼容 shim（旧的场景索引 JS 随 #scidx 一起被注释掉了，
但旧探针/旧代码还在用它；这里用新的权威表 __OM3SC__ 把它重建出来）。"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(p, encoding='utf-8').read()
a = '    var SCTAB = window.__OM3SC__ || [], SCR = {};\n'
assert s.count(a) == 1, '锚点 %d 个' % s.count(a)
b = a + '''    /* 第 39 轮：旧的 #scidx 索引列表换成了 #scsel 下拉，而 #scidx 那段 JS 也一起被注释掉了。
       这里用新的权威表把 window.__om3scIdx 重新搭起来（向后兼容旧代码 / 旧探针）。 */
    window.__om3scIdx = (function () {
      var counts = {}, seen = {}, order = [];
      for (var i = 0; i < SCTAB.length; i++) {
        var x = SCTAB[i]; order.push(x.k); counts[x.k] = x.items.length;
        for (var j = 0; j < x.items.length; j++) { var h = x.items[j].i; if (h) seen[h] = (seen[h] || 0) + 1; }
      }
      var multi = 0; for (var k in seen) if (seen[k] > 1) multi++;
      return { scenes: order, labels: {}, counts: counts, pairs: seen, multi: multi,
               cur: function () { return ''; }, show: function (k) { return window.__scShowScene(k); },
               rows: function () { return []; } };
    })();
'''
s = s.replace(a, b, 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('✅ 已加 __om3scIdx 兼容 shim')
