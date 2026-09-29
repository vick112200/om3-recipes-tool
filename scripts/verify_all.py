# -*- coding: utf-8 -*-
"""逐条验收：把你提过的问题在无头环境里实测一遍"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'      # 只用来放临时产物
SRC = r'D:\workspace\om3-handbook'               # 真源：app/base.html
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = ("<script>window.__OM3_APP__=1;"          # 必须带！否则相机模块直接 return，会得到"0 个按钮/1 个错误"的假象
        "window.__errs=[];"
        "window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||'')+' @'+(e.lineno||0));});"
        "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});</script>")

t = []
t.append("setTimeout(function(){var o=[];")
# vis() 必须查"真的看得见"：只看 hide 类是不够的 —— 元素可能被某个 display:none 的祖先藏住
# （「连接相机」页签空白就是这么漏掉的：paneD 自己没 hide，但被嵌在 display:none 的 paneB 里）
t.append("function vis(id){var e=document.getElementById(id);if(!e)return false;"
         "if(e.classList.contains('hide'))return false;"
         "var s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&e.offsetHeight>0;}")
t.append("function shown(id){var e=document.getElementById(id);return !!e && e.classList.contains('show');}")
# 1 页签三模块
t.append("o.push('顶栏模块数='+document.querySelectorAll('.tabs.mod button[data-p]').length);")
# 2 底栏固定 + 四项
t.append("var bd=document.getElementById('barD'); o.push('底栏定位='+getComputedStyle(bd).position+' 页签数='+bd.querySelectorAll('button[data-dstep]').length);")
# 3 搜索面板 + 关闭按钮
#   v2.19：面板跟着页签 —— A（原版方案/内置配方）→ #toc，B（优化版）→ #toc2。
#   以前这里写死 #toc2（块07 在捕获阶段独占 #tocbtn，块02 的 panel() 根本没机会跑），
#   于是在 A 页签点开的是**优化版**目录（用户 2026-09-24 报的就是这条）。
t.append("function disp(id){var e=document.getElementById(id);return e?getComputedStyle(e).display:'(无)';}")
t.append("document.getElementById('tocbtn').click();")
t.append("setTimeout(function(){")
t.append("var p=document.getElementById('toc');")
t.append("o.push('搜索面板[A 页签应开 #toc] #toc='+disp('toc')+' #toc2='+disp('toc2')+' 有内容='+(p.textContent.length>80)+' 有关闭按钮='+!!p.querySelector('.om3tocclose'));")
t.append("var x=p.querySelector('.om3tocclose'); if(x) x.click();")
t.append("setTimeout(function(){")
t.append("o.push('✕关闭后 #toc='+disp('toc')+' #toc2='+disp('toc2'));")
# 4 各页签可达
t.append("document.querySelector('.tabs.mod button[data-p=B]').click();")
t.append("setTimeout(function(){ o.push('优化版 paneB='+vis('paneB'));")
t.append("document.getElementById('tocbtn').click();")
t.append("setTimeout(function(){ o.push('搜索面板[B 页签应开 #toc2] #toc='+disp('toc')+' #toc2='+disp('toc2'));")
t.append("var x2=document.getElementById('toc2').querySelector('.om3tocclose'); if(x2) x2.click();")
t.append("document.getElementById('tabMine').click();")
t.append("setTimeout(function(){ o.push('我的配方 paneE='+vis('paneE')+' mpList有字='+((document.getElementById('mpList')||{}).textContent||'').trim().slice(0,24));")
t.append("document.getElementById('tabCam').click();")
t.append("setTimeout(function(){ o.push('连接相机 paneD='+vis('paneD')+' 底栏显示='+shown('barD'));")
# 5 置灰
t.append("var on=document.body.classList.contains('cam-on');")
t.append("var dis=0; bd.querySelectorAll('button[data-dstep]').forEach(function(b){ if(Number(b.getAttribute('data-dstep'))>=2 && b.classList.contains('dis')) dis++; });")
t.append("o.push('未连接时置灰项数='+dis+'（应为3）');")
# 6 配方卡按钮 + 堆叠
t.append("o.push('配方卡数='+document.querySelectorAll('.card[id^=r-]').length+' 加入方案按钮='+document.querySelectorAll('.omsavebtn').length);")
t.append("o.push('卡片堆叠='+(getComputedStyle(document.querySelector('.cbody')||document.body).flexDirection==='column'));")
# 7 错误数
t.append("o.push('运行错误='+window.__errs.length+' om3errs='+(window.__om3errs||0));")
t.append("var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);")
t.append("},400);},400);},400);},400);},400);},400);},2400);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
open(TMP + r'\dv_verify.html', 'w', encoding='utf-8', newline='').write(out)

ud = TMP + r'\overify'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=12000', '--dump-dom',
                    'file:///' + (TMP + r'\dv_verify.html').replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=200)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
if k < 0:
    print('未取到输出（DOM %d 字符）' % len(dom))
else:
    print(dom[k:].split('>', 1)[1].split('</div>')[0])
