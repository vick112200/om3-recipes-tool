# -*- coding: utf-8 -*-
"""带 __OM3_APP__=1 的实测（与手机上一致的环境）：查按钮注入/方案列表/错误数

用法：python scripts/check_app.py [要测的 html 路径]
  不给路径 → 测 app/base.html；也可传 app/index.html 或 apk/assets/index.html（最终产物）
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'      # 只用来放临时产物
SRC = r'D:\workspace\om3-handbook'               # 真源：app/base.html
path = sys.argv[1] if len(sys.argv) > 1 else (SRC + r'\app\base.html')
print('[被测文件] %s' % path)
src = open(path, encoding='utf-8').read()

head = ("<script>window.__OM3_APP__=1;window.__errs=[];window.__errMsg={};"
        "window.addEventListener('error',function(e){var m=(e.message||'');window.__errs.push(m+' @'+(e.lineno||0));window.__errMsg[m]=(window.__errMsg[m]||0)+1;});"
        "window.addEventListener('unhandledrejection',function(e){var m=String(e.reason);window.__errs.push('REJ '+m);window.__errMsg['REJ '+m]=(window.__errMsg['REJ '+m]||0)+1;});</script>")

t = []
t.append("setTimeout(function(){var o=[];")
t.append("o.push('__OM3_APP__='+window.__OM3_APP__);")
t.append("o.push('配方卡='+document.querySelectorAll('.card[id^=r-]').length+' 加入方案按钮='+document.querySelectorAll('.omsavebtn').length);")
t.append("o.push('优化版槽位='+document.querySelectorAll('.oslot').length);")
# 存一套方案，看列表能不能渲染出来
t.append("try{ localStorage.setItem('om3sets', JSON.stringify([{id:'t1',name:'测试方案',desc:'描述X',from:'myset1',camera:'OM-3',slots:{1:{vivid:[1,2,3,0,0,0,0,0,0,0,0,0],raw:{'MODE_COLOR_CREATOR_2_VIVID_SET1_1':'MODE_STEP_P1'},used:3}}}])); }catch(e){}")
t.append("document.getElementById('tabMine').click();")
t.append("setTimeout(function(){")
t.append("var L=document.getElementById('mpList');")
t.append("o.push('我的配方 列表内容='+((L||{}).textContent||'').replace(/\\s+/g,'').slice(0,40));")
t.append("o.push('方案条目数='+(L?L.querySelectorAll('.mpitem').length:0));")
t.append("document.getElementById('tabCam').click();")
t.append("setTimeout(function(){")
t.append("var vis=[];for(var k=1;k<=4;k++){var v=document.getElementById('camV'+k);if(v&&!v.classList.contains('hide'))vis.push(k);}")
t.append("o.push('连接相机 可见步骤='+JSON.stringify(vis));")
t.append("o.push('om3errs='+(window.__om3errs||0)+' 运行错误='+window.__errs.length);")
t.append("var top='',mx=0;for(var k in window.__errMsg){if(window.__errMsg[k]>mx){mx=window.__errMsg[k];top=k;}}")
t.append("o.push('最高频错误 x'+mx+'='+String(top).slice(0,100));")
t.append("var lb=document.getElementById('camOut3');if(lb)o.push('日志尾='+(lb.textContent||'').replace(/\\s+/g,' ').slice(-90));")
t.append("var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);")
t.append("},700);},700);},2800);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
open(TMP + r'\dv_app.html', 'w', encoding='utf-8', newline='').write(out)
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', TMP + r'\oapp'], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + TMP + r'\oapp', '--window-size=412,900',
                    '--virtual-time-budget=14000', '--dump-dom',
                    'file:///' + (TMP + r'\dv_app.html').replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print(dom[k:].split('>', 1)[1].split('</div>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
