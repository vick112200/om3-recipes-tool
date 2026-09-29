# -*- coding: utf-8 -*-
"""量「贴底浮层」有没有被底部栏盖住（用户 2026-09-23 报：展开全部的气泡被底部栏盖住）。

检查对象：#foldbar（展开全部/说明）、#foldtip、#top（回到顶部）、.taskpill、.gstatus、toast。
方法：把每个浮层强制显示（加 .on / 去掉 hide），量它的 rect 与当前可见底部栏的 rect，
      算重叠高度；再按 z-index 判断谁盖住谁。

用法：python scripts/dv_float.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()
head = "<script>window.__OM3_APP__=1;</script>"

JS = r"""
window.onerror = function(m){ var d=document.createElement('pre'); d.id='DBGOUT'; d.textContent='JS 报错: '+m; document.body.appendChild(d); };
setTimeout(function(){
  var o = [], fails = [], warn = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
  function rect(sel){
    var e = document.querySelector(sel);
    if(!e) return null;
    var q = e.getBoundingClientRect(), c = getComputedStyle(e);
    return { e:e, q:q, z:c.zIndex, pos:c.position, disp:c.display,
             tag:(sel + ' h=' + Math.round(q.height) + ' bottom=' + Math.round(q.bottom) + ' z=' + c.zIndex) };
  }
  /* 找出当前可见的底部栏（有多条：barABC / barD / mpbar） */
  function bars(){
    var out = [];
    ['.barABC', '#barD', '.mpbar'].forEach(function(sel){
      document.querySelectorAll(sel).forEach(function(e){
        var c = getComputedStyle(e);
        if(c.display === 'none' || c.position !== 'fixed') return;
        var q = e.getBoundingClientRect();
        if(q.height <= 0) return;
        out.push({ sel:sel, q:q, z:+c.zIndex, e:e });
      });
    });
    return out;
  }
  function checkFloats(tag){
    var b = bars();
    o.push('【' + tag + '】可见底部栏：' + (b.length ? b.map(function(x){
      return x.sel + '(h=' + Math.round(x.q.height) + ',top=' + Math.round(x.q.top) + ',z=' + x.z + ')'; }).join(' ') : '无'));
    if(!b.length){ o.push('  （没有底部栏，跳过）'); return; }
    var topOfBar = Math.min.apply(null, b.map(function(x){ return x.q.top; }));
    var maxZ = Math.max.apply(null, b.map(function(x){ return x.z; }));
    ['#foldbar', '#foldtip', '#top', '.taskpill', '.gstatus'].forEach(function(sel){
      var r = rect(sel);
      if(!r){ o.push('  ' + sel + ' 不在页面上'); return; }
      if(r.disp === 'none'){ o.push('  ' + sel + ' display=none（本次没显示，跳过）'); return; }
      var overlap = Math.max(0, Math.min(r.q.bottom, Math.max.apply(null, b.map(function(x){ return x.q.bottom; }))) - Math.max(r.q.top, topOfBar));
      var covered = overlap > 0 && r.z !== '' && (+r.z) < maxZ;
      var msg = '  ' + r.tag + ' 与底栏重叠=' + Math.round(overlap) + 'px'
              + '（底栏顶边=' + Math.round(topOfBar) + '）'
              + (overlap > 0 ? (covered ? ' ★被底栏盖住（z 比底栏小）' : '（z 比底栏大，浮在上面）') : ' ✓不重叠');
      o.push(msg);
      if(covered) warn.push(sel + ' 被盖住 ' + Math.round(overlap) + 'px');
    });
  }

  /* 先进我的配方（有 .mpbar）再进原版方案（有 .barABC），两种底栏都量 */
  document.getElementById('tabMine').click();
  setTimeout(function(){
    /* 强制把浮层显示出来 */
    var fb = document.getElementById('foldbar'); if(fb){ fb.classList.add('on'); fb.style.display = 'flex'; }
    var ft = document.getElementById('foldtip'); if(ft) ft.style.display = 'block';
    var tp = document.getElementById('top'); if(tp) tp.style.display = 'block';
    var pill = document.getElementById('taskPill'); if(pill){ pill.classList.remove('hide'); pill.style.display = 'block'; }
    setTimeout(function(){
      checkFloats('我的配方页（.mpbar 底栏）');
      document.getElementById('tabBuiltin').click();
      setTimeout(function(){
        var fb2 = document.getElementById('foldbar'); if(fb2) fb2.style.display = 'flex';
        var tp2 = document.getElementById('top'); if(tp2) tp2.style.display = 'block';
        setTimeout(function(){
          checkFloats('原版方案页（.barABC 底栏）');
          document.getElementById('tabCam').click();
          setTimeout(function(){
            document.body.classList.add('cam-on');
            var b3 = document.querySelector('#barD button[data-dstep="3"]');
            if(b3) b3.click();
            var fb3 = document.getElementById('foldbar'); if(fb3) fb3.style.display = 'flex';
            setTimeout(function(){
              checkFloats('连接相机·写入页（#barD 底栏）');
              o.push('第 3 轮累计：' + (warn.length ? ('★有 ' + warn.length + ' 处浮层被底栏盖住') : '没有被盖住的浮层 ✓'));

              /* 第 4 轮：把底栏人为撑高（模拟系统字体放大 / 大字号手机）——
                 这才是用户真机上"展开全部被盖住"的成因：浮层必须跟着让位。 */
              var st = document.createElement('style');
              st.textContent = '.barABC,.barD,.mpbar{padding-top:24px !important;padding-bottom:24px !important}';
              document.head.appendChild(st);
              setTimeout(function(){
                if(window.__om3setBarH) window.__om3setBarH();
                setTimeout(function(){
                  var before = warn.length;
                  checkFloats('底栏被撑高之后（模拟大字号）');
                  o.push('—— 撑高后新增被盖住：' + (warn.length - before) + ' 处'
                       + (warn.length === before ? ' ✓（浮层跟着让位了）' : ' ★（没让位）'));
                  o.push('--om3barh=' + (window.__om3barH === undefined ? '未设置' : window.__om3barH + 'px'));
                  o.push('--- 结果：' + (warn.length ? ('失败 —— 仍有 ' + warn.length + ' 处被盖住')
                        : '全部通过（三种底栏 + 撑高场景都没有浮层被盖住）') + ' ---');
                  var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
                  document.body.appendChild(d);
                }, 600);
              }, 500);
            }, 700);
          }, 700);
        }, 700);
      }, 700);
    }, 600);
  }, 2500);
}, 3000);
"""
tail = '<script>' + JS + '</script>'
k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_float.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ofloat'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
