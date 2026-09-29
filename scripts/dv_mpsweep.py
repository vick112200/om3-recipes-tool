# -*- coding: utf-8 -*-
"""按巡检脚本的页签顺序逐步排查「我的配方」为什么没渲染（每步打：__om3mpInit 是否存在、
日志尾、paneE 高度、列表条目数）。

用法：python scripts/dv_mpsweep.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = "<script>window.__OM3_APP__=1;</script>"

JS = r"""
setTimeout(function(){
  var o = [];
  function snap(tag){
    var pe = document.getElementById('paneE'), L = document.getElementById('mpList');
    var lb = document.getElementById('camOut3');
    var logt = lb ? (lb.textContent||'').replace(/\s+/g,' ') : '';
    o.push(tag);
    o.push('   __om3mpInit=' + (typeof window.__om3mpInit)
         + '  __om3cur=' + JSON.stringify(window.__om3cur)
         + '  paneE.hide=' + (pe ? pe.classList.contains('hide') : '?')
         + '  高=' + (pe ? pe.offsetHeight : -1));
    o.push('   mpList 条目=' + (L ? L.querySelectorAll('.mpitem').length : -1)
         + '  文字=' + JSON.stringify(L ? (L.textContent||'').replace(/\s+/g,' ').slice(0,50) : ''));
    o.push('   日志里出现「我的配方」已就绪=' + (logt.indexOf('「我的配方」已就绪') >= 0));
  }
  try{ localStorage.setItem('om3sets', JSON.stringify([
    {id:'t1',name:'甲',desc:'a',from:'myset1',camera:'OM-3',
     slots:{1:{vivid:[1,2,3,0,0,0,0,0,0,0,0,0],raw:{},used:3}}},
    {id:'t2',name:'乙',desc:'b',from:'myset2',camera:'OM-3',slots:{1:null,2:null,3:null,4:null}}
  ])); }catch(e){}
  snap('0) 刚塞完 2 套方案（还没点任何页签）');

  document.querySelector('.tabs.mod button[data-p="A"]').click();
  setTimeout(function(){
    snap('1) 点了 内置配方(A)');
    document.querySelector('.tabs.mod button[data-p="B"]').click();
    setTimeout(function(){
      snap('2) 点了 优化版(B)');
      document.querySelector('.tabs.mod button[data-p="C"]').click();
      setTimeout(function(){
        snap('3) 点了 场景对比(C)');
        document.getElementById('tabMine').click();
        setTimeout(function(){
          snap('4) 点了 我的配方(tabMine)  ← 关键');
          /* 再点一次，看是不是"第二次才生效" */
          document.querySelector('.tabs.mod button[data-p="A"]').click();
          setTimeout(function(){
            document.getElementById('tabMine').click();
            setTimeout(function(){
              snap('5) 又切走再点一次 我的配方');
              var d=document.createElement('pre');d.id='DBGOUT';d.textContent=o.join('\n');
              document.body.appendChild(d);
            }, 700);
          }, 400);
        }, 700);
      }, 400);
    }, 400);
  }, 400);
}, 2800);
"""
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_mpsweep.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ompsweep'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=22000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
