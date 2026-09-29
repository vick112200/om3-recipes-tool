# -*- coding: utf-8 -*-
"""搜索功能实测：用真实用户路径（点「人像」建议按钮 + 手动输入）看结果进了哪个面板。

用法：python scripts/dv_tocsearch.py [app] [源文件路径]
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
args = sys.argv[1:]
appmode = 'app' in args
srcpath = next((a for a in args if a.endswith('.html')), r'D:\workspace\om3-handbook\app\base.html')
src = open(srcpath, encoding='utf-8').read()
print('[源=%s] [app=%s]' % (srcpath.split('\\')[-1], appmode))

head = ("<script>" + ("window.__OM3_APP__=1;" if appmode else "")
        + "window.__errs=[];window.__step='(load)';"
        "window.addEventListener('error',function(e){"
        "  try{ window.__errs.push('['+window.__step+'] '+String(e.message)); }catch(x){}"
        "});</script>")

t = []
t.append("setTimeout(function(){var o=[];")
t.append("function step(s){window.__step=s;}")
t.append("function snap(tag){")
t.append("  var a=document.getElementById('tocres'), b=document.getElementById('toc2res');")
t.append("  o.push(tag+' | #tocres 链接='+(a?a.querySelectorAll('a').length:'无')+' class='+(a?a.className:'无')")
t.append("        +' || #toc2res 链接='+(b?b.querySelectorAll('a').length:'无')+' class='+(b?b.className:'无'));")
t.append("}")
t.append("step('打开面板'); document.getElementById('tocbtn').click();")
t.append("setTimeout(function(){")
# 真实路径 1：点 #toc2chips 里的「人像」
t.append("step('点 toc2 的「人像」建议按钮');")
t.append("var ch=document.querySelector('#toc2chips button[data-q=\"人像\"]');")
t.append("o.push('找到建议按钮='+!!ch);")
t.append("if(ch) ch.click();")
t.append("setTimeout(function(){")
t.append("o.push('搜索框值='+JSON.stringify(document.getElementById('toc2q').value));")
t.append("snap('点建议后');")
# 真实路径 2：直接手动输入并派发 input
t.append("step('手动输入人像');")
t.append("var inp=document.getElementById('toc2q');")
t.append("inp.value='人像'; inp.dispatchEvent(new Event('input',{bubbles:true}));")
t.append("setTimeout(function(){")
t.append("snap('手动输入后');")
t.append("o.push('错误数='+window.__errs.length+' '+window.__errs.join(' | ').slice(0,120));")
t.append("var d=document.createElement('pre');d.id='DBGOUT';d.textContent=o.join('\\n');document.body.appendChild(d);")
t.append("},450);},450);},450);},2400);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_tocsearch.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\otocsearch'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--user-data-dir=' + ud,
                    '--window-size=412,900', '--virtual-time-budget=13000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=200)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print(dom[k:].split('>', 1)[1].split('</pre>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
