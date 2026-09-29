# -*- coding: utf-8 -*-
"""「连接相机」底栏探针：量 #barD 的定位/位置/可见按钮数，以及页面横向溢出。

用法：python scripts/dv_barprobe.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = "<script>window.__OM3_APP__=1;window.__errs=[];window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||''));});</script>"

JS = r"""
setTimeout(function(){
  var o = [];
  function R(e){ if(!e) return null; var r = e.getBoundingClientRect();
    return {x:Math.round(r.left),y:Math.round(r.top),w:Math.round(r.width),h:Math.round(r.height),bottom:Math.round(r.bottom)}; }
  function el(id){ return document.getElementById(id); }
  function barInfo(){
    var b = el('barD');
    if(!b) return '(没有 barD)';
    var cs = getComputedStyle(b);
    var btns = b.querySelectorAll('button[data-dstep]');
    var vis = [];
    for(var i=0;i<btns.length;i++){
      var r = btns[i].getBoundingClientRect();
      var seen = (Math.round(r.width) > 0 && r.right <= window.innerWidth + 1);
      vis.push(btns[i].getAttribute('data-dstep') + ':' + (seen ? '可见' : ('看不见 w=' + Math.round(r.width) + ' right=' + Math.round(r.right))));
    }
    return 'position=' + cs.position + ' display=' + cs.display + ' z=' + cs.zIndex
         + ' rect=' + JSON.stringify(R(b)) + '\n      class="' + b.className + '" 按钮=' + vis.join(' ');
  }
  function flush(extra){
    if(extra) o.push(extra);
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
  try{ document.getElementById('tabCam').click(); }catch(e){ o.push('点页签报错：' + (e && e.message ? e.message : e)); }
  setTimeout(function(){
    try{
    o.push('窗口 w=' + window.innerWidth + '  documentElement.scrollWidth=' + document.documentElement.scrollWidth
           + '  body.scrollWidth=' + document.body.scrollWidth);
    o.push('  ①连接：#barD ' + barInfo());
    /* 切到②③④各量一次 */
    var dsteps = [2,3,4];
    var k = 0;
    function step(){
      if(k >= dsteps.length){
        o.push('  其它底栏：barABC class="' + (el('barABC') ? el('barABC').className : '-') + '"  mpbar class="' + (document.querySelector('.mpbar') ? document.querySelector('.mpbar').className : '-') + '"');
        o.push('  #barD 的父节点 = ' + (el('barD').parentNode ? el('barD').parentNode.tagName + '.' + String(el('barD').parentNode.className || '') : '-'));
        var anc = el('barD').parentNode, chain = [];
        while(anc && anc !== document.documentElement){ var s = getComputedStyle(anc); chain.push(anc.tagName + '.' + String(anc.className||'').slice(0,18) + '(pos=' + s.position + ',tf=' + (s.transform !== 'none') + ',filter=' + (s.filter !== 'none') + ')'); anc = anc.parentNode; }
        o.push('  祖先链：' + chain.join(' → '));
        o.push('累计 js 报错=' + window.__errs.length);
        flush();
        return;
      }
      var n = dsteps[k++];
      try{ if(window.__camStep) window.__camStep(n); else document.querySelectorAll('#barD button[data-dstep]')[n-1].click(); }
      catch(e){ o.push('  切到第' + n + '步报错：' + (e && e.message ? e.message : e)); }
      setTimeout(function(){
        o.push('  第' + n + '步：#barD ' + barInfo());
        step();
      }, 400);
    }
    step();
    }catch(e){ flush('探针异常：' + (e && e.message ? e.message : e)); }
  }, 700);
}, 2600);
"""
tail = '<script>' + JS + '</script>'
i = src.find('<body'); j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_barprobe.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\obarprobe'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=30000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk > 0:
    print(dom[kk:].split('>', 1)[1].split('</pre>')[0])
else:
    open(TMP + r'\bp_dump.html', 'w', encoding='utf-8', newline='').write(dom)
    print('无输出 DOM=%d  DBGOUT在全文? %s  探针脚本在? %s'
          % (len(dom), 'DBGOUT' in dom, 'function barInfo' in dom))
    print('dump → ' + TMP + r'\bp_dump.html')
