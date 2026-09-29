# -*- coding: utf-8 -*-
"""根因分析 2：verify_all 的交互序列在**非 app 模式**（桌面 HTML）下会报 1 个错，
抓它的消息 + 调用栈，定位是哪一步、哪个函数。

用法：python scripts/dv_noapp_seq.py [app]   —— 加 app 则设 __OM3_APP__=1 对照
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

appmode = len(sys.argv) > 1 and sys.argv[1] == 'app'

head = ("<script>" + ("window.__OM3_APP__=1;" if appmode else "")
        + "window.__errs=[];window.__step='(load)';"
        "window.addEventListener('error',function(e){"
        "  try{ window.__errs.push('['+window.__step+'] '+String(e.message)+'\\n'"
        "       + ((e.error&&e.error.stack)?String(e.error.stack).split('\\n').slice(0,8).join('\\n'):'(no stack)'));"
        "  }catch(x){} });"
        "window.addEventListener('unhandledrejection',function(e){"
        "  window.__errs.push('['+window.__step+'] REJ '+String(e.reason)); });"
        "</script>")

t = []
t.append("setTimeout(function(){var o=[];")
t.append("function step(s){window.__step=s;}")
t.append("function vis(id){var e=document.getElementById(id);return !!(e && !e.classList.contains('hide'));}")
t.append("step('点搜索面板'); document.getElementById('tocbtn').click();")
t.append("setTimeout(function(){")
t.append("var p=document.getElementById('toc2');")
t.append("var x=p.querySelector('.om3tocclose'); step('关搜索面板'); if(x) x.click();")
t.append("setTimeout(function(){")
t.append("step('切换到 优化版 paneB'); document.querySelector('.tabs.mod button[data-p=B]').click();")
t.append("setTimeout(function(){ o.push('优化版 paneB='+vis('paneB'));")
t.append("step('切换到 我的配方 tabMine'); document.getElementById('tabMine').click();")
t.append("setTimeout(function(){ o.push('我的配方 paneE='+vis('paneE'));")
t.append("step('切换到 连接相机 tabCam'); document.getElementById('tabCam').click();")
t.append("setTimeout(function(){ o.push('连接相机 paneD='+vis('paneD'));")
t.append("step('读置灰项');")
t.append("var bd=document.getElementById('barD'); var dis=0;")
t.append("bd.querySelectorAll('button[data-dstep]').forEach(function(b){ if(Number(b.getAttribute('data-dstep'))>=2 && b.classList.contains('dis')) dis++; });")
t.append("o.push('置灰项数='+dis);")
t.append("o.push('配方卡='+document.querySelectorAll('.card[id^=r-]').length+' 按钮='+document.querySelectorAll('.omsavebtn').length);")
t.append("o.push('运行错误='+window.__errs.length);")
t.append("for(var i=0;i<window.__errs.length;i++) o.push('--- ERR'+i+': '+window.__errs[i]);")
t.append("var d=document.createElement('pre');d.id='DBGOUT';d.textContent=o.join('\\n');document.body.appendChild(d);")
t.append("},500);},500);},500);},500);},500);},2200);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + (r'\dv_seq_app.html' if appmode else r'\dv_seq.html')
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + (r'\oseqa' if appmode else r'\oseq')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--user-data-dir=' + ud,
                    '--window-size=412,900', '--virtual-time-budget=13000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=200)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print('[模式=%s]' % ('app' if appmode else '桌面/无标记'))
print(dom[k:].split('>', 1)[1].split('</pre>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
