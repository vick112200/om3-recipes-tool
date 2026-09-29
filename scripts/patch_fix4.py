# -*- coding: utf-8 -*-
"""修四个问题：
   1) 优化版/场景对比 点了不切换 → 根因：底部按钮只改了高亮，没有真正驱动原页签逻辑
      （顶栏已把 B/C 拿掉，所以要放两个隐藏代理按钮，点它们才会走原有切换流程）
   2) 删掉页面最底部那两行小字（.foot 之类的 */
   3) 底部切换栏改为"始终固定在屏幕最底"
   4) 蓝牙实验块从「我的配方」搬到「连接相机」里面
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- 1) 隐藏代理按钮（让原有页签逻辑能驱动 B/C） ----------
old_tabs = '<button type="button" data-p="D" id="tabCam">连接相机</button>'
assert h.count(old_tabs) == 1, h.count(old_tabs)
h = h.replace(old_tabs, old_tabs + '''
      <!-- 隐藏代理：底部"优化版/场景对比"通过点它们来走原有切换逻辑 -->
      <button type="button" data-p="B" id="tabB" style="display:none">优化版</button>
      <button type="button" data-p="C" id="tabC" style="display:none">场景对比</button>''', 1)

# 底部按钮的委托逻辑：B/C/A 分别派发到对应代理
old_click = """    if(dp){
      /* 复用原有页签逻辑：模拟点击顶栏对应按钮 */
      var top = document.getElementById(dp === 'E' ? 'tabMine' : (dp === 'D' ? 'tabCam' : 'tabBuiltin'));
      if(top && top !== btn){ top.click(); }
      setTimeout(function(){ applyModule(dp); }, 20);
      return;
    }"""
assert h.count(old_click) == 1, h.count(old_click)
h = h.replace(old_click, """    if(dp){
      /* 一律派发到"有 data-p 的真实按钮"上，走原有页签逻辑（B/C 用隐藏代理） */
      var top = document.getElementById(dp === 'E' ? 'tabMine' : (dp === 'D' ? 'tabCam' : (dp === 'B' ? 'tabB' : (dp === 'C' ? 'tabC' : 'tabBuiltin'))));
      if(top && top !== btn){ top.click(); }
      setTimeout(function(){ applyModule(dp); }, 30);
      return;
    }""", 1)

# ---------- 2) 删掉最底部的小字（footer 类） ----------
removed = 0
for pat in [r'\n\s*<div class="foot"[\s\S]*?</div>\s*(?=\n\s*<)', r'\n\s*<footer[\s\S]*?</footer>']:
    for mm in list(re.finditer(pat, h)):
        h = h[:mm.start()] + h[mm.end():]
        removed += 1
# 常见"小字"文案兜底
for txt in ['数据来源 om-recipes.com', '仅供个人离线使用', '本页为离线单文件']:
    for mm in list(re.finditer(r'\n\s*<div[^>]*>[^<]*' + re.escape(txt) + r'[^<]*</div>', h)):
        h = h[:mm.start()] + h[mm.end():]
        removed += 1

# ---------- 3) 底部切换栏固定在最底部 ----------
old_bar_css = '.barABC,.barD{display:none;gap:6px;position:sticky;bottom:0;z-index:55;background:#101010;border-top:1px solid #242424;padding:8px 4px;margin-top:10px}'
assert h.count(old_bar_css) == 1, h.count(old_bar_css)
h = h.replace(old_bar_css, '.barABC,.barD{display:none;gap:6px;position:fixed;left:0;right:0;bottom:0;z-index:9000;background:#101010;border-top:1px solid #242424;padding:8px 4px}', 1)
h = h.replace('.mpbar{display:flex;gap:6px;position:sticky;bottom:0;background:#101010;border-top:1px solid #242424;padding:8px 4px;margin-top:10px}',
              '.mpbar{display:flex;gap:6px;position:fixed;left:0;right:0;bottom:0;z-index:9000;background:#101010;border-top:1px solid #242424;padding:8px 4px}', 1)
# 给内容留出底部空间，避免被固定栏挡住
k = h.find('</style>')
h = h[:k] + """
body{padding-bottom:66px}
.barABC:not(.show){display:none}
""" + h[k:]

# ---------- 4) 蓝牙块搬到「连接相机」里 ----------
m = re.search(r'<!-- 蓝牙（实验） -->\s*<div class="mpcard" id="bleCard"[\s\S]*?</div>\s*\n\s*</div>\s*\n', h)
if not m:
    m = re.search(r'<!-- 蓝牙（实验） -->[\s\S]*?id="bleList"[^>]*>[^<]*</div>\s*</div>\s*\n', h)
assert m, 'ble card not found'
ble = m.group(0)
h = h[:m.start()] + h[m.end():]
mD = re.search(r'<div id="paneD"[^>]*>', h)
assert mD, 'paneD not found'
h = h[:mD.end()] + '\n' + ble + h[mD.end():]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('已修：代理切换 / 删底部小字(%d 处) / 底栏固定 / 蓝牙搬家（+%d 字节）' % (removed, len(h) - n0))
