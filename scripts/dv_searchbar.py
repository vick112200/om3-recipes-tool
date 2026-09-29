# -*- coding: utf-8 -*-
"""根因分析 4：搜索栏在 app 模式下是否可见、点击是否"开了又关"（两次 toggle 互相抵消）。

用法：python scripts/dv_searchbar.py [app]
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
t.append("var btn=document.getElementById('tocbtn'), t2=document.getElementById('toc2');")
t.append("var cs=btn?getComputedStyle(btn):null;")
t.append("o.push('搜索栏可见='+!!cs && cs.display!=='none' && cs.visibility!=='hidden'"
         " +' display='+(cs?cs.display:'无'));")
t.append("var r=btn?btn.getBoundingClientRect():null;")
t.append("o.push('搜索栏尺寸='+(r?Math.round(r.width)+'x'+Math.round(r.height):'无'));")
t.append("o.push('父容器 row2 可见='+!!(document.getElementById('row2')"
         " && getComputedStyle(document.getElementById('row2')).display!=='none'));")
# 观察点击后 open 类的变化序列（用 MutationObserver 记录真实的开/关轨迹）
t.append("window.__trace=[];")
t.append("new MutationObserver(function(){window.__trace.push(t2.classList.contains('open')?'open':'closed');})"
         ".observe(t2,{attributes:true,attributeFilter:['class']});")
t.append("window.__trace.push('start:'+(t2.classList.contains('open')?'open':'closed'));")
t.append("btn.click();")
t.append("setTimeout(function(){")
t.append("o.push('class 变化轨迹='+window.__trace.join(' → '));")
t.append("o.push('最终 display='+getComputedStyle(t2).display);")
t.append("o.push('运行错误数='+window.__errs.length+' '+window.__errs.join('|').slice(0,90));")
t.append("var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);")
t.append("},700);},2400);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + (r'\dv_sba.html' if appmode else r'\dv_sb.html')
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + (r'\osba' if appmode else r'\osb')
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
