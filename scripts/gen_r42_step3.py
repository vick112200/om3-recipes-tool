# -*- coding: utf-8 -*-
"""第 42 轮 · 步骤 3：清掉最后几处死代码/注释（都不影响功能，但留着容易误读）
 · `.om3labshot` 两条 CSS（只服务于已删的模拟预览图）
 · `#toc3:not(.open)` 残留选择器
 · `#toc3q/#toc3res/...` 那组死变量与死监听（usePanel 已不再引用）
 · paneF 的残留注释、showPane 里的 'F' 映射
"""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()
n = 0
pairs = [
 ('  /* 第 38 轮：模拟预览只有一张图，别缩成小格 —— 铺满所在列 */\n'
  '  .om3labshot figure{flex:1 1 100%;max-width:100%}\n'
  '  .om3labshot img{border-color:#3a4a52}\n', ''),
 ('#toc2:not(.open),#toc3:not(.open){display:none !important}', '#toc2:not(.open){display:none !important}'),
 ('<!-- ===== 第 39 轮：本站设计独立页签（pane F）===== -->\n', ''),
 ("    try{ pane = (p === 'F') ? 'F' : ((p === 'A') ? 'A' : 'B'); }catch(e0){}   /* 目录面板跟着页签走（三份：A 原版 / F 本站设计 / B 优化版） */",
  "    try{ pane = (p === 'A') ? 'A' : 'B'; }catch(e0){}      /* 目录面板跟着页签走 */"),
]
for a, b in pairs:
    if a in s:
        s = s.replace(a, b, 1); n += 1
    else:
        print('  ⚠ 没找到：%s' % a[:60].replace('\n', '⏎'))
# 死变量 + 死监听
s2 = re.sub(r'/\* 第三份：本站设计（[^)]*\) \*/\n(var q3=document\.getElementById\([^;]*;\n[^;]*;\n function empty3El\(\)\{[^}]*\}\n)', '', s)
if s2 != s:
    s = s2; n += 1
    print('  ✅ 删掉 toc3 的死变量组')
s2 = s.replace(" if(q3){ q3.addEventListener('input',function(){run(q3);}); q3.addEventListener('search',function(){run(q3);}); }\n", '')
if s2 != s:
    s = s2; n += 1
    print('  ✅ 删掉 toc3 的死监听')
# 清掉 toc3chips（那组按钮还在页面里？没有 toc3 面板了，若存在也删）
if 'toc3chips' in s:
    s = re.sub(r'<div class="chips" id="toc3chips">.*?</div>\n', '', s, count=1, flags=re.S)
    n += 1
    print('  ✅ 删掉 toc3chips')
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('✅ 步骤 3 完成（%d 处）。残留自查：' % n)
for kw in ('om3lab', 'oLAB', 'toc3', 'paneF', '本站设计'):
    print('   %-8s %d 处' % (kw, s.count(kw)))
