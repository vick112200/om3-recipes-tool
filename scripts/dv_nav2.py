# -*- coding: utf-8 -*-
"""根因分析 3：确认 nav2 在两种模式下是否为 null，以及"点搜索栏"在桌面模式是否真的失效。

用法：python scripts/dv_nav2.py [app]
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

appmode = len(sys.argv) > 1 and sys.argv[1] == 'app'

head = ("<script>" + ("window.__OM3_APP__=1;" if appmode else "")
        + "window.__errs=[];"
        "window.addEventListener('error',function(e){window.__errs.push(String(e.message));});"
        "</script>")

t = []
t.append("setTimeout(function(){var o=[];")
t.append("var t2 = document.getElementById('toc2');")
t.append("o.push('DOM 里 #toc2 存在='+!!t2);")
t.append("o.push('有 #tocbtn='+!!document.getElementById('tocbtn'));")
# 点搜索栏，看面板是否真的打开、是否报错
t.append("var before = t2 ? t2.classList.contains('open') : null;")
t.append("document.getElementById('tocbtn').click();")
t.append("setTimeout(function(){")
t.append("var after = t2 ? t2.classList.contains('open') : null;")
t.append("o.push('点之前 open='+before+' → 点之后 open='+after+'（期望 true）');")
t.append("o.push('面板计算样式 display='+(t2?getComputedStyle(t2).display:'无'));")
t.append("o.push('有关闭按钮='+!!(t2&&t2.querySelector('.om3tocclose')));")
t.append("o.push('运行错误数='+window.__errs.length+' 内容='+window.__errs.join(' | ').slice(0,110));")
t.append("var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);")
t.append("},600);},2400);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + (r'\dv_nav2a.html' if appmode else r'\dv_nav2.html')
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + (r'\onav2a' if appmode else r'\onav2')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--user-data-dir=' + ud,
                    '--window-size=412,900', '--virtual-time-budget=12000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=200)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print('[模式=%s] ' % ('app' if appmode else '桌面/无标记')
      + (dom[k:].split('>', 1)[1].split('</div>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom))))
