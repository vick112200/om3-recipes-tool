# -*- coding: utf-8 -*-
"""忠实截图：不搬动元素，先执行一段 pre-js（如点某个页签），再整页截图。
元素保持在原容器里 → 宽度/布局与真机一致。

用法：python scripts/dv_pane_shot.py 输出png "pre-js" [宽] [高]
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

out = sys.argv[1]
prejs = sys.argv[2] if len(sys.argv) > 2 else ''
w = sys.argv[3] if len(sys.argv) > 3 else '412'
h = sys.argv[4] if len(sys.argv) > 4 else '2600'

head = "<script>window.__OM3_APP__=1;</script>"

# 先等渲染，执行 pre-js，把顶部栏/底栏收掉（只留内容），再滚到顶
tail = ("<script>setTimeout(function(){"
        "try{%s}catch(e){document.title='PREJS-ERR';}"
        "setTimeout(function(){"
        "try{"
        "  var tb=document.querySelector('.topbar');if(tb)tb.style.display='none';"
        "  var r2=document.getElementById('row2');if(r2)r2.style.display='none';"
        "  var gs=document.getElementById('gStatusBar');if(gs)gs.style.display='none';"
        "  var bd=document.getElementById('barD');if(bd)bd.style.display='none';"
        "  document.querySelectorAll('.barABC').forEach(function(x){x.style.display='none';});"
        "  window.scrollTo(0,0);"
        "}catch(e){}"
        "},900);"
        "},2600);</script>") % prejs

i = src.find('<body')
j = src.find('>', i) + 1
out_html = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_pane.html'
open(p, 'w', encoding='utf-8', newline='').write(out_html)

ud = TMP + r'\opane'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                '--user-data-dir=' + ud, '--window-size=%s,%s' % (w, h),
                '--virtual-time-budget=16000', '--screenshot=' + out,
                'file:///' + p.replace('\\', '/')],
               capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
print('pre-js = %s' % prejs)
print('截图 →', out)
