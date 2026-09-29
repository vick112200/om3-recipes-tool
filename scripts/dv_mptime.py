# -*- coding: utf-8 -*-
"""点「我的配方」后按时间采样列表条目数，并用日志计数判断 mpInit 到底跑了几次。

用法：python scripts/dv_mptime.py [gap_ms]   gap_ms = 每次点页签的间隔（默认 700，与巡检脚本一致）
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

gap = sys.argv[1] if len(sys.argv) > 1 else '700'

head = "<script>window.__OM3_APP__=1;</script>"
_m = sys.argv[2] if len(sys.argv) > 2 else ''
if _m:
    # 逐步加回巡检脚本注入的东西，用来定位"是哪一个把初始化搞坏了"
    parts = ["window.__OM3_APP__=1;"]
    if 'err' in _m or 'both' in _m:
        parts.append("window.__sweepErr=[];window.__sweepStep='(load)';"
                     "window.addEventListener('error',function(e){window.__sweepErr.push(window.__sweepStep+' :: '+String(e.message));});"
                     "window.addEventListener('unhandledrejection',function(e){window.__sweepErr.push(window.__sweepStep+' :: REJ '+String(e.reason));});")
    if 'patch' in _m or 'both' in _m:
        parts.append("window.__listeners=0;"
                     "(function(){var a=EventTarget.prototype.addEventListener;"
                     "EventTarget.prototype.addEventListener=function(){window.__listeners++;return a.apply(this,arguments);};})();")
    head = '<script>' + ''.join(parts) + '</script>'

JS = r"""
setTimeout(function(){
  var o = [], GAP = __GAP__;
  function initRuns(){
    var lb = document.getElementById('camOut3');
    var t = lb ? (lb.textContent||'') : '';
    return (t.match(/「我的配方」已就绪/g) || []).length;
  }
  function items(){
    var L = document.getElementById('mpList');
    return L ? L.querySelectorAll('.mpitem').length : -1;
  }
  try{ localStorage.setItem('om3sets', JSON.stringify([
    {id:'t1',name:'甲',desc:'a',from:'myset1',camera:'OM-3',slots:{1:{vivid:[1,2,3,0,0,0,0,0,0,0,0,0],raw:{},used:3}}},
    {id:'t2',name:'乙',desc:'b',from:'myset2',camera:'OM-3',slots:{1:null,2:null,3:null,4:null}}
  ])); }catch(e){}
  o.push('塞完方案后：mpInit 跑过 ' + initRuns() + ' 次，条目=' + items());

  document.querySelector('.tabs.mod button[data-p="A"]').click();
  setTimeout(function(){
    document.querySelector('.tabs.mod button[data-p="B"]').click();
    setTimeout(function(){
      document.querySelector('.tabs.mod button[data-p="C"]').click();
      setTimeout(function(){
        var before = initRuns();
        o.push('点 tabMine 之前：mpInit 跑过 ' + before + ' 次，条目=' + items());
        var tab = document.getElementById('tabMine');
        o.push('tabMine 有 data-p=' + JSON.stringify(tab ? tab.getAttribute('data-p') : null)
             + '  存在=' + !!tab);
        tab.click();
        var n = 0;
        var iv = setInterval(function(){
          n++;
          if(n <= 12) o.push('  +' + (n*150) + 'ms  mpInit次数=' + initRuns() + '  条目=' + items()
                             + '  paneE高=' + (document.getElementById('paneE')||{}).offsetHeight);
          if(n >= 12){
            clearInterval(iv);
            o.push('最终：mpInit 跑过 ' + initRuns() + ' 次，条目=' + items());
            var d=document.createElement('pre');d.id='DBGOUT';d.textContent=o.join('\n');
            document.body.appendChild(d);
          }
        }, 150);
      }, GAP);
    }, GAP);
  }, GAP);
}, 2800);
"""
JS = JS.replace('__GAP__', gap)
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_mptime.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\omptime'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=24000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print('gap=%sms' % gap)
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
