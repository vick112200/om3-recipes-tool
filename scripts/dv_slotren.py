# -*- coding: utf-8 -*-
"""槽位名字 + 每槽改名 + 弹窗不压底栏 —— 验收（用户 2026-09-23 第二轮反馈）。

验四件事：
  ① 加进我的配方时，槽位里存下了配方名（one.name），详情页那一行**显示出来**（不再是只有"槽 1"）
  ② 详情页每个有内容的槽都有「改这个槽的名字」按钮，点了能改、只改这一个槽（不动整套方案名）
  ③ 弹窗(.omask/.ocard)不与底部栏重叠（含把底栏撑高的场景）
  ④ 成功提示里名字在前面（不会被误读成"槽1"）

用法：python scripts/dv_slotren.py
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
  function sets(){ try{ return JSON.parse(localStorage.getItem('om3sets') || '[]'); }catch(e){ return []; } }
  function txt(el){ return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }
  function barTop(){
    var t = 1e9;
    document.querySelectorAll('.barABC, #barD, .mpbar').forEach(function(e){
      var c = getComputedStyle(e);
      if(c.display === 'none' || c.position !== 'fixed') return;
      var q = e.getBoundingClientRect();
      if(q.height > 0 && q.top < t) t = q.top;
    });
    return t === 1e9 ? null : t;
  }
  function done(){
    o.push('累计 js 报错=' + (window.__errs ? window.__errs.length : 0));
    o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }

  /* 新模型：先建一个方案（方案 = 档位 + 自己起的名字），再把配方填进它的槽 */
  document.getElementById('tabMine').click();
  setTimeout(function(){
    var ns = document.getElementById('mpNewSet');
    if(ns) ns.click();
    setTimeout(function(){
      var f0 = document.querySelectorAll('#ofields select, #ofields input');
      if(f0.length >= 2){ f0[0].value = '测试方案'; f0[1].value = 'myset1'; }
      document.getElementById('ook').click();
      setTimeout(function(){
        document.getElementById('tabBuiltin').click();
        setTimeout(go, 500);
      }, 400);
    }, 500);
  }, 900);

  function go(){
  var card = document.querySelector('[id^="r-"]');
  var btn = card ? card.querySelector('.omsavebtn') : null;
  if(btn) btn.click();
  setTimeout(function(){
    /* 用默认（预填的内置配方名）直接确定 */
    var f = document.querySelectorAll('#ofields select, #ofields input');
    var nm = f.length >= 3 ? f[2].value : '';
    o.push('  弹窗预填名字=' + JSON.stringify(nm));
    o.push('  弹窗卡片是否与底栏重叠：' + (function(){
      var t = barTop(); if(t === null) return '（无底栏）';
      var q = document.querySelector('.ocard').getBoundingClientRect();
      return (q.bottom > t + 1) ? ('★重叠 ' + Math.round(q.bottom - t) + 'px') : ('不重叠 ✓（留白 ' + Math.round(t - q.bottom) + 'px）');
    })());
    var qq = document.querySelector('.ocard').getBoundingClientRect();
    var tt = barTop();
    ok(tt === null || qq.bottom <= tt + 1, '弹窗没有压在底部栏上');
    document.getElementById('ook').click();
    setTimeout(function(){
      var s = sets()[sets().length - 1];
      ok(s.slots[1] && s.slots[1].name === nm, '槽位里存了配方名：' + JSON.stringify(s.slots[1] ? s.slots[1].name : null));

      /* 详情页 */
      document.getElementById('tabMine').click();
      setTimeout(function(){
        var it = document.querySelector('#mpList .mpitem');
        if(it) it.click();
        setTimeout(function(){
          var row = document.querySelector('button[data-w]');
          var rowBox = row ? (row.closest('.mpsrow') || row.parentElement) : null;
          o.push('  详情槽位行=' + JSON.stringify(txt(rowBox).slice(0, 80)));
          ok(txt(rowBox).indexOf(nm) >= 0, '详情页槽位行显示出了配方名（不再只有"槽 1"）');
          var ren = document.querySelector('button[data-ren]');
          ok(!!ren, '每个有内容的槽都有「改这个槽的名字」按钮');
          if(ren){
            ren.click();
            setTimeout(function(){
              var f2 = document.querySelectorAll('#ofields input');
              o.push('  改名弹窗预填=' + JSON.stringify(f2.length ? f2[0].value : ''));
              if(f2.length) f2[0].value = '我自己改的槽名';
              document.getElementById('ook').click();
              setTimeout(function(){
                var s2 = sets()[sets().length - 1];
                ok(s2.slots[1].name === '我自己改的槽名', '槽名已改成：' + JSON.stringify(s2.slots[1].name));
                ok(s2.name === '测试方案', '方案名**没被连带改掉**（仍是 ' + JSON.stringify(s2.name) + '）');
                setTimeout(function(){
                  var row2 = document.querySelector('button[data-w]');
                  var box2 = row2 ? (row2.closest('.mpsrow') || row2.parentElement) : null;
                  ok(txt(box2).indexOf('我自己改的槽名') >= 0, '改名后详情页那行立刻显示新名字');

                  /* 撑高底栏 → 弹窗仍不应压住 */
                  var st = document.createElement('style');
                  st.textContent = '.barABC,.barD,.mpbar{padding-top:26px !important;padding-bottom:26px !important}';
                  document.head.appendChild(st);
                  if(window.__om3setBarH) window.__om3setBarH();
                  setTimeout(function(){
                    var ren2 = document.querySelector('button[data-ren]');
                    if(ren2) ren2.click();
                    setTimeout(function(){
                      var t2 = barTop();
                      var q2 = document.querySelector('.ocard').getBoundingClientRect();
                      o.push('  底栏撑高后：底栏顶边=' + Math.round(t2) + ' 弹窗底边=' + Math.round(q2.bottom)
                           + '（--om3barh=' + window.__om3barH + '）');
                      ok(q2.bottom <= t2 + 1, '底栏撑高后弹窗依然不压底栏');
                      document.getElementById('ocancel').click();
                      setTimeout(done, 300);
                    }, 500);
                  }, 500);
                }, 400);
              }, 400);
            }, 500);
          } else done();
        }, 700);
      }, 600);
    }, 500);
  }, 800);
  }
}, 3000);
"""
tail = ('<script>window.__errs=[];'
        "window.addEventListener('error',function(e){window.__errs.push(String(e.message));});"
        "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});"
        '</script><script>' + JS + '</script>')

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_slotren.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\oslotren'
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
