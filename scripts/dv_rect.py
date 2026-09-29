# -*- coding: utf-8 -*-
"""量任意元素的**真实几何 + 父链**（布局问题用数字说话，不靠肉眼）。

用法：python scripts/dv_rect.py "sel1|sel2|…" [宽=412] [pre-js]
输出：每个选择器的 rect(x,y,w,h)、display、position，以及它的父链（id/class）。
也会打印"从上一个元素底边到下一个元素顶边"的间隙（找空位用）。
"""
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
SRC = r'D:\workspace\om3-handbook'
src = open(os.path.join(SRC, 'app', 'base.html'), encoding='utf-8').read()

sels = (sys.argv[1] if len(sys.argv) > 1 else '.topbar|#row2|.scselwrap').split('|')
w = sys.argv[2] if len(sys.argv) > 2 else '412'
prejs = sys.argv[3] if len(sys.argv) > 3 else ''
print('[%s @ %spx] pre-js=%s' % (' / '.join(sels), w, prejs or '无'))

head = ("<script>window.__OM3_APP__=1;window.__errs=[];"
        "window.addEventListener('error',function(e){window.__errs.push(e.message);});</script>"
        "<script>setTimeout(function(){try{%s}catch(e){}},1500);</script>" % prejs)

t = ["setTimeout(function(){var o=[];",
     "function chain(el){var L=[],i=0;while(el&&el.tagName&&i++<6){var d=el.tagName.toLowerCase()"
     "+(el.id?('#'+el.id):'')+(el.className&&typeof el.className==='string'?('.'+el.className.trim().split(/\\s+/).join('.')):'');"
     "L.push(d);el=el.parentElement;}return L.join(' < ');}" ]
for s in sels:
    t.append("var e=document.querySelector(%r);" % s)
    t.append("if(!e){o.push(%r + ' → 找不到');}else{var r=e.getBoundingClientRect();var cs=getComputedStyle(e);"
             "o.push(%r + ' → x=' + Math.round(r.left) + ' y=' + Math.round(r.top + window.pageYOffset)"
             " + ' w=' + Math.round(r.width) + ' h=' + Math.round(r.height)"
             " + ' display=' + cs.display + ' position=' + cs.position"
             " + ' marginTop=' + cs.marginTop + ' paddingTop=' + cs.paddingTop);"
             "o.push('     父链：' + chain(e));}" % (s, s))
t.append("o.push('滚动高度=' + document.documentElement.scrollHeight + ' 视口=' + window.innerHeight);")
t.append("o.push('错误=' + (window.__errs||[]).length);")
t.append("var d=document.createElement('div');d.id='RTOUT';d.textContent=o.join('\\n');document.body.appendChild(d);")
t.append("},2600);")
tail = '<script>' + ''.join(t) + '</script>'
i = src.find('<body'); j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
hp = os.path.join(TMP, 'dv_rect.html')
open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'orect')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=%s,900' % w,
                    '--virtual-time-budget=14000', '--dump-dom',
                    'file:///' + hp.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=240)
dom = r.stdout or ''
k = dom.find('id="RTOUT"')
if k < 0:
    print('没拿到输出（DOM %d 字节）' % len(dom))
    print((r.stderr or '')[-400:])
    sys.exit(1)
print(dom[k:].split('>', 1)[1].split('</div>')[0].replace('&#10;', '\n'))
