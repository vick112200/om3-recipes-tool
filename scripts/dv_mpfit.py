# -*- coding: utf-8 -*-
"""量「我的配方」详情行的真实宽度，找出是谁把行撑出屏幕的。

用法：python scripts/dv_mpfit.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = "<script>window.__OM3_APP__=1;</script>"

JS = r"""
try{ localStorage.setItem('om3sets', JSON.stringify([{id:'v1',name:'量',desc:'d',from:'myset1',camera:'OM-3',
  slots:{1:{vivid:[3,2,1,1,1,5,4,5,2,0,3,3],raw:{},used:9},2:null,3:null,4:null}}])); }catch(e){}
document.getElementById('tabMine').click();
setTimeout(function(){ document.querySelector('#mpList .mpitem').click(); }, 500);
setTimeout(function(){
  var o = [];
  function m(tag, el){
    if(!el){ o.push('  ' + tag + ' = 不存在'); return; }
    var r = el.getBoundingClientRect();
    o.push('  ' + tag + ' = left ' + Math.round(r.left) + ' → right ' + Math.round(r.right)
         + '  宽 ' + Math.round(r.width) + '  高 ' + Math.round(r.height));
  }
  function probe(tag){
    o.push('【' + tag + '】');
    var pane = document.getElementById('paneE');
    m('#paneE', pane);
    m('#mpList', document.getElementById('mpList'));
    m('.mpsrow', document.querySelector('#mpList .mpsrow'));
    m('.mpmain', document.querySelector('#mpList .mpmain'));
    m('.mpwheel', document.querySelector('#mpList .mpwheel'));
    var r0 = document.querySelector('#mpList .mpmain .r');
    m('.r（按钮行）', r0);
    var right = pane.getBoundingClientRect().right, over = [];
    var bs = document.querySelectorAll('#mpList .mpmain .r button');
    for(var i = 0; i < bs.length; i++){
      var b = bs[i].getBoundingClientRect();
      o.push('    按钮' + (i+1) + ' ' + bs[i].textContent.slice(0, 10) + ' 右边缘 ' + Math.round(b.right));
      if(b.right > right + 0.5) over.push(i + 1);
    }
    o.push('  超出 #paneE 右边缘的按钮：' + (over.length ? (over.join(',') + ' ← 溢出！') : '无 ✓'));
    if(r0) o.push('  .r 高=' + Math.round(r0.getBoundingClientRect().height) + '（换行会变高）');
    o.push('  documentElement.scrollWidth=' + document.documentElement.scrollWidth
         + '  innerWidth=' + window.innerWidth);
  }
  o.push('注意：--window-size 并不等于 CSS 视口，所以下面同时按"真机 412"复测一次。');
  probe('当前宽度');
  document.getElementById('paneE').style.width = '388px';   /* 412 - 页边距 24 */
  probe('强制 388px（≈真机 412 视口）');
  document.getElementById('paneE').style.width = '';
  var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
  document.body.appendChild(d);
}, 1400);
"""
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_mpfit.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ompfit'
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
