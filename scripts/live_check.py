# -*- coding: utf-8 -*-
"""在无头 Chrome 里跑这个 app，抓运行时报错 + 页签状态"""
import subprocess
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'      # 只用来放临时产物
SRC = r'D:\workspace\om3-handbook'               # 真源：app/base.html
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

probe_lines = []
probe_lines.append("window.__errs=[];")
probe_lines.append("window.addEventListener('error',function(e){window.__errs.push('ERR: '+(e.message||'')+' @'+(e.lineno||0));});")
probe_lines.append("window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ: '+String(e.reason));});")
probe = '<script>' + ''.join(probe_lines) + '</script>'

tail = []
tail.append("setTimeout(function(){var o=[];")
tail.append("o.push('错误数='+(window.__errs?window.__errs.length:0));")
tail.append("if(window.__errs) for(var i=0;i<Math.min(4,window.__errs.length);i++) o.push(window.__errs[i].slice(0,120));")
tail.append("o.push('om3errs='+(window.__om3errs||0)+' 缺元素='+(window.__om3miss||0));")
tail.append("var bar=document.getElementById('om3errBar'); o.push('错误条='+(bar?bar.textContent.slice(0,60):'无'));")
tail.append("o.push('兜底脚本='+(typeof window.__om3cur));")
tail.append("try{ document.querySelector('.tabs.mod button[data-p=E]').click(); }catch(e){ o.push('点我的配方异常:'+e.message); }")
tail.append("setTimeout(function(){")
tail.append("var pe=document.getElementById('paneE');")
tail.append("o.push('我的配方 paneE 可见='+(pe?!pe.classList.contains('hide'):'无元素'));")
tail.append("o.push('paneA 可见='+!document.getElementById('paneA').classList.contains('hide'));")
tail.append("o.push('mpList 有内容='+((document.getElementById('mpList')||{}).textContent||'').slice(0,40));")
tail.append("o.push('底栏 barD 显示='+document.getElementById('barD').classList.contains('show'));")
tail.append("var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);")
tail.append("},600);},2600);")
probe2 = '<script>' + ''.join(tail) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + probe + src[j:].replace('</body>', probe2 + '</body>', 1)
open(TMP + r'\dv_live.html', 'w', encoding='utf-8', newline='').write(out)

ud = TMP + r'\olive'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=9000', '--dump-dom',
                    'file:///' + (TMP + r'\dv_live.html').replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=180)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
if k < 0:
    print('（没拿到探针输出；DOM 长度 %d）' % len(dom))
    print(dom[:400].replace('\n', ' '))
else:
    seg = dom[k:k + 1600]
    print(seg.split('>', 1)[1].split('</div>')[0])
