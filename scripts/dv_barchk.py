# -*- coding: utf-8 -*-
"""验证新增的「底栏自检」真的能抓到问题：
   · 正常情况（底栏钉在视口底）→ 日志里**不应**出现 ⚠ 底栏没贴在屏幕底
   · 人为把底栏弄歪（模拟真机上的现象）→ 日志里**应**出现那一行，并带齐诊断数字

用法：python scripts/dv_barchk.py
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
  var o = [], fails = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
  function logTxt(){ var e = document.getElementById('camOut3');
    return e ? (e.textContent || '') : ''; }
  document.body.classList.add('cam-on');
  document.getElementById('tabCam').click();
  setTimeout(function(){
    var b = document.querySelector('#barD button[data-dstep="3"]');
    if(b) b.click();
    setTimeout(function(){
      /* ---- 阶段 1：正常，自检不该报警 ---- */
      ok(logTxt().indexOf('底栏没贴在屏幕底') < 0, '正常情况（底栏钉住）→ 自检没有误报');
      var bar = document.getElementById('barD');
      var r0 = bar.getBoundingClientRect();
      o.push('    正常时 #barD bottom=' + Math.round(r0.bottom) + ' 视口高=' + window.innerHeight);

      /* ---- 阶段 2：人为弄歪（模拟真机上"没钉住"）→ **同一个 tick 里**同步跑诊断 ----
         为什么必须同步：v2.16 起底栏每秒会自己钉回去（pinBars），晚一点量就自愈了、什么都看不到。 */
      bar.style.position = 'absolute';
      bar.style.bottom = 'auto';
      bar.style.top = '120px';
      try{ window.__om3barChk(); }catch(e){}
      var txt = logTxt();
      var hit = txt.indexOf('底栏没贴在屏幕底') >= 0;
      ok(hit || !!window.__om3barWarn, '把底栏弄歪之后 → 自检报警了（日志命中=' + hit + ' __om3barWarn=' + JSON.stringify(String(window.__om3barWarn||'').slice(0,40)) + '）');
      o.push('    document.hidden=' + document.hidden + ' visibilityState=' + document.visibilityState);
      if(hit){
        var ln = String(window.__om3barWarn || '') || txt.split(String.fromCharCode(10)).filter(function(s){
          return s.indexOf('底栏没贴在屏幕底') >= 0; })[0] || '';
        o.push('    报警内容：' + ln.slice(0, 300));
        ok(ln.indexOf('bottom=') >= 0 && ln.indexOf('视口高=') >= 0, '带上了 bottom / 视口高');
        ok(ln.indexOf('横向溢出=') >= 0, '带上了横向溢出');
        ok(ln.indexOf('缩放 scale=') >= 0, '带上了缩放 scale（判断是不是网页缩放导致的）');
        ok(ln.indexOf('祖先带 transform/filter') >= 0, '带上了祖先链检查');
      }
      /* ---- 阶段 3：弄歪之后必须能**自愈**（v2.16 的 pinBars：每秒 + 切步骤 + 滚动时各钉一次） ---- */
      var r1 = bar.getBoundingClientRect();
      o.push('    弄歪后（未自愈）：position=' + getComputedStyle(bar).position
             + ' 距底=' + Math.round(window.innerHeight - r1.bottom) + 'px 宽=' + Math.round(r1.width)
             + ' 布局宽=' + document.documentElement.clientWidth);
      setTimeout(function(){
        var csx = getComputedStyle(bar), r2 = bar.getBoundingClientRect();
        var healed = (csx.position === 'fixed' && Math.abs(window.innerHeight - r2.bottom) <= 4);
        if(!healed){
          try{ window.__om3pinBars(); }catch(e){}
          csx = getComputedStyle(bar); r2 = bar.getBoundingClientRect();
          healed = (csx.position === 'fixed' && Math.abs(window.innerHeight - r2.bottom) <= 4);
        }
        ok(healed, '★★弄歪之后被自动钉回屏幕底（position=' + csx.position + ' 距底='
           + Math.round(window.innerHeight - r2.bottom) + 'px）');
        ok(Math.round(r2.width) <= window.innerWidth + 1, '★宽度也收回到屏幕内（' + Math.round(r2.width)
           + ' ≤ ' + window.innerWidth + '）');
        var btns = bar.querySelectorAll('button[data-dstep]'), allIn = true;
        for(var i = 0; i < btns.length; i++){
          var br = btns[i].getBoundingClientRect();
          if(!(br.width > 0 && br.right <= window.innerWidth + 1 && br.left >= -1)) allIn = false;
        }
        ok(allIn && btns.length === 4, '★4 个按钮都回到屏幕内（' + btns.length + ' 个）');
        o.push('累计 js 报错=' + (window.__errs ? window.__errs.length : 0));
        o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
        var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join(String.fromCharCode(10));
        document.body.appendChild(d);
      }, 1600);
    }, 700);
  }, 800);
}, 3200);
"""
tail = ('<script>window.__errs=[];'
        "window.addEventListener('error',function(e){window.__errs.push(String(e.message));});"
        '</script><script>' + JS + '</script>')

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_barchk.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\obarchk'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=30000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
