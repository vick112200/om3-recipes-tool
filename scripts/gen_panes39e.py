# -*- coding: utf-8 -*-
"""第 39 轮（A5）：点底栏「本站设计」时，转发逻辑会去点顶栏的"隐藏代理按钮"——
   而 `dp==='F'` 的三元表达式**兜底到了 tabBuiltin（=data-p="A"）** → 于是 A 页签被一起点亮。
   修法：顶栏 `.tabs.mod` 里补一个隐藏代理 `#tabF`（和 B/C 同款），并把三元表达式加一环；
   顺带把 14972 行那个"页签联动"清单也补上 paneF。
"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()
n = 0

# ① 顶栏补隐藏代理 #tabF
old = '      <button type="button" data-p="B" id="tabB" style="display:none">优化版</button>'
new = ('      <button type="button" data-p="F" id="tabF" style="display:none">本站设计</button>\n' + old)
assert s.count(old) == 1, 'tabB 代理锚点不唯一'
s = s.replace(old, new, 1); n += 1

# ② 转发三元表达式加 F 这一环
old2 = "var top = $(dp === 'E' ? 'tabMine' : (dp === 'D' ? 'tabCam' : (dp === 'B' ? 'tabB' : (dp === 'C' ? 'tabC' : 'tabBuiltin'))));"
new2 = ("var top = $(dp === 'E' ? 'tabMine' : (dp === 'D' ? 'tabCam' : (dp === 'B' ? 'tabB' : "
        "(dp === 'C' ? 'tabC' : (dp === 'F' ? 'tabF' : 'tabBuiltin')))));   /* 第 39 轮：F 也要转发到自己的代理，"
        "否则会兜底到「内置配方」→ 把 A 页签一起点亮 */")
assert s.count(old2) == 1, '转发表达式锚点不唯一'
s = s.replace(old2, new2, 1); n += 1

# ③ 页签联动清单加 paneF
old3 = "var ids = ['paneA', 'paneB', 'paneC', 'paneD', 'paneE'];"
new3 = "var ids = ['paneA', 'paneF', 'paneB', 'paneC', 'paneD', 'paneE'];   /* 第 39 轮：加 paneF */"
assert s.count(old3) == 1, 'pane 联动清单锚点不唯一'
s = s.replace(old3, new3, 1); n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('✅ A5 完成，共改 %d 处（顶栏 #tabF 代理 + 转发映射 + 联动清单）' % n)
