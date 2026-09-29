# -*- coding: utf-8 -*-
"""抓搜索面板流程里那个 `Cannot read properties of null (reading 'style')` 的调用栈 + 发生步骤。

用法：python scripts/dv_tocerr.py [app|desktop] [源文件路径] [补丁名]
  补丁名 dollar = 先只把 $() 自递归修掉（用于对比"我的 TOC 改动前后"）
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
args = sys.argv[1:]
appmode = 'app' in args
srcpath = next((a for a in args if a.endswith('.html')), r'D:\workspace\om3-handbook\app\base.html')
patch = 'dollar' if 'dollar' in args else None

src = open(srcpath, encoding='utf-8').read()
if patch == 'dollar':
    old = "  function $(id){\n    var el = $(id);"
    new = "  function $(id){\n    var el = document.getElementById(id);"
    assert src.count(old) == 1, 'dollar 补丁匹配数=%d' % src.count(old)
    src = src.replace(old, new)
print('[源=%s] [app=%s] [补丁=%s]' % (srcpath.split('\\')[-1], appmode, patch or '无'))

head = ("<script>" + ("window.__OM3_APP__=1;" if appmode else "")
        + "window.__errs=[];window.__step='(load)';"
        "window.addEventListener('error',function(e){"
        "  try{ window.__errs.push('['+window.__step+'] '+String(e.message)+'\\n'+"
        "   ((e.error&&e.error.stack)?String(e.error.stack).split('\\n').slice(0,7).join('\\n'):'(no stack)'));"
        "  }catch(x){} });"
        "</script>")

t = []
t.append("setTimeout(function(){var o=[];")
t.append("function step(s){window.__step=s;}")
t.append("step('点搜索栏'); document.getElementById('tocbtn').click();")
t.append("setTimeout(function(){")
t.append("var inp=document.getElementById('toc2q');")
t.append("step('往搜索框输入');")
t.append("try{ inp.value='人像'; inp.dispatchEvent(new Event('input',{bubbles:true})); }catch(e){ o.push('输入异常='+e.message); }")
t.append("setTimeout(function(){")
t.append("var res=document.getElementById('toc2res');")
t.append("o.push('结果条数='+(res?res.querySelectorAll('a').length:0));")
t.append("step('点✕关闭');")
t.append("var x=document.querySelector('#toc2 .om3tocclose'); if(x) x.click();")
t.append("setTimeout(function(){")
t.append("o.push('✕后 t2open='+document.getElementById('toc2').classList.contains('open'));")
t.append("o.push('错误数='+window.__errs.length);")
t.append("for(var i=0;i<window.__errs.length;i++) o.push('--- ERR'+i+': '+window.__errs[i]);")
t.append("var d=document.createElement('pre');d.id='DBGOUT';d.textContent=o.join('\\n');document.body.appendChild(d);")
t.append("},450);},450);},450);},2400);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_tocerr.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\otocerr'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--user-data-dir=' + ud,
                    '--window-size=412,900', '--virtual-time-budget=13000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=200)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print(dom[k:].split('>', 1)[1].split('</pre>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
