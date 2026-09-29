# -*- coding: utf-8 -*-
"""根因分析：抓 `Maximum call stack size exceeded` 的真实调用栈（看是哪两个函数在互相递归）"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

# 放在 <body> 之后、主脚本之前：先装好捕获器
# 用法：python dv_stack.py [noapp]   —— 加 noapp 则不设 __OM3_APP__（模拟桌面 HTML）
head = (
    "<script>" + ("" if (len(sys.argv) > 1 and sys.argv[1] == 'noapp') else "window.__OM3_APP__=1;")
    + "window.__stacks=[];window.__errs=[];"
    "window.addEventListener('error',function(e){"
    "  try{"
    "    window.__errs.push(String(e.message));"
    "    var s=(e.error&&e.error.stack)?String(e.error.stack):'(no stack)';"
    "    window.__stacks.push(s);"
    "  }catch(x){}"
    "});"
    "</script>"
)

tail = (
    "<script>setTimeout(function(){"
    "var o=[];"
    "o.push('错误数='+window.__errs.length);"
    "for(var i=0;i<window.__errs.length;i++){"
    "  o.push('--- ERROR '+i+': '+window.__errs[i]);"
    "  var L=(window.__stacks[i]||'').split('\\n');"
    "  for(var j=0;j<Math.min(L.length,26);j++) o.push('  F'+j+' '+L[j].slice(0,160));"
    "}"
    "var d=document.createElement('pre');d.id='DBGOUT';d.textContent=o.join('\\n');document.body.appendChild(d);"
    "},2600);</script>"
)

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
open(TMP + r'\dv_stack.html', 'w', encoding='utf-8', newline='').write(out)

subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', TMP + r'\ostk'], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--user-data-dir=' + TMP + r'\ostk',
                    '--window-size=412,900', '--virtual-time-budget=14000', '--dump-dom',
                    'file:///' + (TMP + r'\dv_stack.html').replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print(dom[k:].split('>', 1)[1].split('</pre>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
