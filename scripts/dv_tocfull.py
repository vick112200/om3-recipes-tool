# -*- coding: utf-8 -*-
"""搜索/目录面板功能验收：开 → 输关键字出结果 → ✕ 关闭 → Esc 关闭，两种模式各跑一遍。

用法：python scripts/dv_tocfull.py [app]
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
t.append("function st(){return {t2:document.getElementById('toc2').classList.contains('open'),"
         "legacy:document.getElementById('toc').classList.contains('open'),"
         "disp:getComputedStyle(document.getElementById('toc2')).display};}")
t.append("var s0=st(); o.push('① 初始 t2open='+s0.t2+' 老面板open='+s0.legacy);")
# ② 点搜索栏
t.append("document.getElementById('tocbtn').click();")
t.append("setTimeout(function(){")
t.append("var s1=st(); o.push('② 点搜索栏后 t2open='+s1.t2+' display='+s1.disp+' 老面板open='+s1.legacy+'（老面板应为 false）');")
t.append("o.push('   关闭按钮='+!!document.querySelector('#toc2 .om3tocclose'));")
# ③ 输入关键字，看是否出结果
t.append("var inp=document.getElementById('toc2q');")
t.append("try{ inp.value='人像'; inp.dispatchEvent(new Event('input',{bubbles:true})); }catch(e){ o.push('输入异常='+e.message); }")
t.append("setTimeout(function(){")
t.append("var res=document.getElementById('toc2res');")
t.append("var n=res?res.querySelectorAll('a').length:0;")
t.append("o.push('③ 搜\"人像\" → 结果条数='+n+'（应>0） 列表display='+(res?getComputedStyle(res).display:'无'));")
# ④ 点 ✕ 关闭
t.append("var x=document.querySelector('#toc2 .om3tocclose');")
t.append("if(x) x.click();")
t.append("setTimeout(function(){")
t.append("var s2=st(); o.push('④ 点✕后 t2open='+s2.t2+' display='+s2.disp+' 老面板open='+s2.legacy+'（老面板也应为 false）');")
# ⑤ Esc 关闭（先再打开一次）
t.append("document.getElementById('tocbtn').click();")
t.append("setTimeout(function(){")
t.append("var s3=st(); var openAgain=s3.t2;")
t.append("try{ document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); }catch(e){ o.push('Esc 异常='+e.message); }")
t.append("setTimeout(function(){")
t.append("var s4=st(); o.push('⑤ 再打开='+openAgain+' → 按 Esc 后 t2open='+s4.t2+' display='+s4.disp);")
t.append("o.push('运行错误数='+window.__errs.length+' '+window.__errs.join('|').slice(0,100));")
t.append("var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join('\\n');document.body.appendChild(d);")
t.append("},400);},400);},500);},500);},400);},2400);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + (r'\dv_tocfa.html' if appmode else r'\dv_tocf.html')
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + (r'\otocfa' if appmode else r'\otocf')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--user-data-dir=' + ud,
                    '--window-size=412,900', '--virtual-time-budget=14000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=200)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print('[模式=%s]' % ('app' if appmode else '桌面/无标记'))
print(dom[k:].split('>', 1)[1].split('</pre>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
