# -*- coding: utf-8 -*-
"""改前验证：在**临时副本**上试打补丁，看四数是否达标（不动 app/base.html）

用法：python scripts/dv_probe_fix.py [补丁名]
  补丁名: none = 不打补丁（基线） / dollar = 只修 $() 自递归
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

which = sys.argv[1] if len(sys.argv) > 1 else 'dollar'

PATCHES = {
    'dollar': [("""  function $(id){
    var el = $(id);""",
                """  function $(id){
    var el = document.getElementById(id);""")],
}

applied = []
for old, new in PATCHES.get(which, []):
    n = src.count(old)
    if n != 1:
        print('!! 补丁匹配 %d 次（应为 1），已中止' % n)
        sys.exit(1)
    src = src.replace(old, new)
    applied.append(n)
print('[补丁=%s] 应用 %d 处' % (which, len(applied)))

head = ("<script>window.__OM3_APP__=1;window.__errs=[];window.__errMsg={};"
        "window.addEventListener('error',function(e){var m=(e.message||'');window.__errs.push(m);"
        "window.__errMsg[m]=(window.__errMsg[m]||0)+1;});"
        "window.addEventListener('unhandledrejection',function(e){var m='REJ '+String(e.reason);"
        "window.__errs.push(m);window.__errMsg[m]=(window.__errMsg[m]||0)+1;});</script>")

t = []
t.append("setTimeout(function(){var o=[];")
t.append("o.push('配方卡='+document.querySelectorAll('.card[id^=r-]').length"
         "+' 加入方案按钮='+document.querySelectorAll('.omsavebtn').length);")
# 存一套方案，看列表能不能渲染
t.append("try{ localStorage.setItem('om3sets', JSON.stringify([{id:'t1',name:'测试方案',desc:'描述X',"
         "from:'myset1',camera:'OM-3',slots:{1:{vivid:[1,2,3,0,0,0,0,0,0,0,0,0],"
         "raw:{'MODE_COLOR_CREATOR_2_VIVID_SET1_1':'MODE_STEP_P1'},used:3}}}])); }catch(e){}")
t.append("document.getElementById('tabMine').click();")
t.append("setTimeout(function(){")
t.append("var L=document.getElementById('mpList');")
t.append("o.push('方案条目数='+(L?L.querySelectorAll('.mpitem').length:0));")
t.append("o.push('列表首行='+((L||{}).textContent||'').replace(/\\s+/g,' ').slice(0,50));")
# 点第 1 个「加入我的方案」，看是否真的存进方案库
t.append("var sb=document.querySelectorAll('.omsavebtn')[0];")
t.append("o.push('第1个按钮文字='+(sb?sb.textContent:'无'));")
t.append("try{ if(sb) sb.click(); }catch(e){ o.push('点按钮异常='+e.message); }")
# 直接调 $ 检查兜底：不存在的 id 应返回 OM3NULL，不递归
t.append("try{ var z=window.__om3$('__no_such_el__');"
         "o.push('$(不存在)='+(z===null?'null':(typeof z)+'/'+(z&&z.id===undefined?'OM3NULL?':'x')));"
         "}catch(e){ o.push('$ 调用异常='+e.message); }")
t.append("setTimeout(function(){")
t.append("o.push('点按钮后方案条目数='+(L?L.querySelectorAll('.mpitem').length:0));")
t.append("o.push('om3errs='+(window.__om3errs||0)+' 运行错误='+window.__errs.length);")
t.append("var top='',mx=0;for(var k in window.__errMsg){if(window.__errMsg[k]>mx){mx=window.__errMsg[k];top=k;}}")
t.append("o.push('最高频错误 x'+mx+'='+String(top).slice(0,90));")
t.append("var lb=document.getElementById('camOut3');")
t.append("if(lb){var tx=(lb.textContent||'').replace(/\\s+/g,' ');"
         "o.push('含注入失败='+(tx.indexOf('注入')>=0));}")
t.append("var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);")
t.append("},900);},700);},2800);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
open(TMP + r'\dv_fix.html', 'w', encoding='utf-8', newline='').write(out)
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', TMP + r'\ofix'], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--user-data-dir=' + TMP + r'\ofix',
                    '--window-size=412,900', '--virtual-time-budget=16000', '--dump-dom',
                    'file:///' + (TMP + r'\dv_fix.html').replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print(dom[k:].split('>', 1)[1].split('</div>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
