# -*- coding: utf-8 -*-
"""第 39 轮（修回归）：gen_recipes.py 的插入点还在 paneA —— 只要重跑生成器，
「本站设计」那 12 张卡就被搬回 paneA（#paneF 空了）。改成插进 **#paneF 的 .wrap 末尾**。"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\workspace\om3-handbook\scripts\gen_recipes.py'
s = io.open(p, encoding='utf-8').read()
old = """    # paneA 的 HTML 本身是"错位"的（最后一个分区 #howto 没有自己的 </details>，那对标签被用来收了 paneA）。
    # 所以**不能**按 paneA 的收尾插：实测会插进上一个卡片/盒子内部（藏在折叠里，看不见）。
    # 正确做法：插到**最后一个同级 <details class="sec"> 之前**（同一层级，和别的分区并列）。
    ib = s.find('<div id="paneB"')
    assert ib > 0
    secs = [m.start() for m in re.finditer(r'<details class="sec"', s[:ib])]
    assert len(secs) >= 5, '没找到同级分区（只有 %d 个）' % len(secs)
    ins = secs[-1]"""
new = """    # ⚠ 第 39 轮：这一段已经**搬进独立页签 #paneF**（用户要求「原版和优化版中间加一个本站设计」）。
    # 所以插入点是 #paneF 的 .wrap 末尾 —— 不能再按 paneA 插，否则重跑生成器会把卡片搬回 paneA。
    ipf = s.find('<div id="paneF"')
    assert ipf > 0, '找不到 #paneF（第 39 轮新加的页签）'
    ipb = s.find('<div id="paneB"', ipf)
    assert ipb > ipf, '找不到 #paneB（#paneF 的收尾）'
    ins = s.rfind('\\n</div>\\n</div>\\n', ipf, ipb)
    assert ins > ipf, '#paneF 收尾定位失败'
    ins += 1"""
assert s.count(old) == 1, '锚点 %d 个' % s.count(old)
s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('✅ gen_recipes.py 插入点已改为 #paneF 的 .wrap 末尾')
