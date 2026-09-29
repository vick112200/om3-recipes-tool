# -*- coding: utf-8 -*-
"""查「我的配方」列表渲染：为什么塞了 2 套方案却显示 0 条。
同时把 om3err 的内部计数和相机日志尾部打出来（我的巡检脚本之前漏了这两项）。

用法：python scripts/dv_mpcheck.py
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
  function cnt(){ var L=document.getElementById('mpList');
    return L ? L.querySelectorAll('.mpitem').length : -1; }
  function snap(tag){
    var L = document.getElementById('mpList');
    o.push(tag + ' → 条目=' + cnt()
      + '  om3errs=' + (window.__om3errs||0)
      + '  文字=' + JSON.stringify((L?(L.textContent||''):'').replace(/\s+/g,' ').slice(0,70)));
  }
  function logTail(){
    var lb = document.getElementById('camOut3');
    return lb ? (lb.textContent||'').replace(/\s+/g,' ').slice(-260) : '(无日志)';
  }
  function set(key, val){ try{ localStorage.setItem(key, JSON.stringify(val)); }catch(e){} }

  var S1 = [{id:'t1',name:'甲',desc:'a',from:'myset1',camera:'OM-3',
    slots:{1:{vivid:[1,2,3,0,0,0,0,0,0,0,0,0],raw:{'MODE_COLOR_CREATOR_2_VIVID_SET1_1':'MODE_STEP_P1'},used:3}}}];
  var S2 = S1.concat([{id:'t2',name:'乙',desc:'b',from:'myset2',camera:'OM-3',
    slots:{1:null,2:null,3:null,4:null}}]);

  /* A) 1 套方案，直接点我的配方 */
  set('om3sets', S1);
  document.getElementById('tabMine').click();
  setTimeout(function(){
    snap('A: 1 套 / 直接点我的配方');

    /* B) 2 套方案，重新点一次 */
    set('om3sets', S2);
    document.querySelector('.tabs.mod button[data-p="A"]').click();
    setTimeout(function(){
      document.getElementById('tabMine').click();
      setTimeout(function(){
        snap('B: 2 套 / 从内置配方切过来');

        /* C) 2 套，且先走一遍 B、C 子页签 */
        document.querySelector('.tabs.mod button[data-p="B"]').click();
        setTimeout(function(){
          document.querySelector('.tabs.mod button[data-p="C"]').click();
          setTimeout(function(){
            document.getElementById('tabMine').click();
            setTimeout(function(){
              snap('C: 2 套 / 先走 B、C 再切过来');
              o.push('--- 相机日志尾 ---');
              o.push(logTail());
              var d=document.createElement('pre');d.id='DBGOUT';d.textContent=o.join('\n');
              document.body.appendChild(d);
            }, 700);
          }, 400);
        }, 400);
      }, 700);
    }, 400);
  }, 700);
}, 2800);
"""
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_mpcheck.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ompcheck'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=20000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
