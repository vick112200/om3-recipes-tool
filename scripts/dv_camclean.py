# -*- coding: utf-8 -*-
"""「连接相机」页按钮太乱 → 优化后的验收：首屏只留少数按钮 + 折叠能展开 + 功能一个都没丢。

用法：python scripts/dv_camclean.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = ("<script>window.__OM3_APP__=1;"
        "window.__errs=[];"
        "window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||''));});"
        "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});</script>")

JS = r"""
function vis(e){
  if(!e) return false;
  if(e.classList && e.classList.contains('hide')) return false;
  var s = getComputedStyle(e);
  if(s.display === 'none' || s.visibility === 'hidden') return false;
  return e.offsetHeight > 0 || e.getClientRects().length > 0;
}
/* <details> 关着的时候，里面的东西 getClientRects 也是 0 → 用"祖先有没有关着的 details"再判一次 */
function inClosedFold(e){
  var n = e;
  while(n && n !== document.body){
    if(n.tagName === 'DETAILS' && !n.open) return true;
    n = n.parentNode;
  }
  return false;
}
function visReal(e){ return vis(e) && !inClosedFold(e); }

setTimeout(function(){
  var o = [], fails = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }

  try{ localStorage.clear(); }catch(e){}
  document.getElementById('tabCam').click();

  setTimeout(function(){
    var pd = document.getElementById('paneD');

    /* ① 首屏可见按钮数（用户抱怨的核心指标） */
    var all = pd.querySelectorAll('button');
    var shown = [], hidden = [];
    for(var i = 0; i < all.length; i++){
      var b = all[i];
      if(b.classList.contains('dis')) continue;            /* 置灰的不算"乱" */
      if(visReal(b)) shown.push((b.id || '?') + '「' + String(b.textContent).trim().slice(0, 14) + '」');
      else hidden.push(b.id || '?');
    }
    o.push('  首屏(未连相机)可见按钮 ' + shown.length + ' 个：\n      ' + shown.join('\n      '));
    o.push('  被折叠/隐藏的按钮 ' + hidden.length + ' 个：' + hidden.slice(0, 30).join(' '));
    ok(shown.length <= 6, '★首屏可见按钮 ≤ 6 个（实际 ' + shown.length + '）');

    /* ② 功能一个都不能丢：全都还在（只是折叠了） */
    var must = ['camGateScan','camGateConn','camGateManual','camAutoToggle','camScan','camScanHelp',
                'camJoin','camWifiSettings','camForget','camConnect','camDisconnect','camForgetSaved',
                'camCheck','camWifi','bleScan','bleStop','bleDiagCopy','bleDis','bleWake','blep3','blep2','blep1',
                'camBackup','camWrite','camPreview2'];
    var miss = [];
    for(var k = 0; k < must.length; k++) if(!document.getElementById(must[k])) miss.push(must[k]);
    ok(miss.length === 0, '★24 个按钮/控件一个没丢（缺：' + (miss.join(',') || '无') + '）');

    /* ③ 蓝牙那 8 个按钮默认收在折叠里（这是最大的那坨） */
    ok(!visReal(document.getElementById('bleScan')) && !visReal(document.getElementById('bleWake')),
       '★蓝牙工具默认折叠（扫描/唤醒首屏看不见）');
    ok(!!document.getElementById('bleFold'), '蓝牙折叠区在');

    /* ④ gate 的次要入口也在折叠里 */
    ok(!visReal(document.getElementById('camGateManual')), '★「手动填 SSID/密码」首屏不占位（收进"连不上？更多方式"）');
    ok(!visReal(document.getElementById('camScan')) && !visReal(document.getElementById('camCheck')),
       '★和 gate 重复的"扫码/检测"不再同时出现（收进"连接详情"）');

    /* ⑤ 折叠能展开：gate 的"更多方式" → 手动填卡片（要自动展开 + 滚动） */
    var sums = pd.querySelectorAll('details > summary');
    var gateSum = null, bleSum = null, v1Sum = null;
    for(var q = 0; q < sums.length; q++){
      var tx = String(sums[q].textContent);
      if(tx.indexOf('连不上？更多方式') >= 0) gateSum = sums[q];
      else if(tx.indexOf('蓝牙工具') >= 0) bleSum = sums[q];
      else if(tx.indexOf('连接详情') >= 0) v1Sum = sums[q];
    }
    ok(!!gateSum && !!bleSum && !!v1Sum, '三个折叠的标题都在');

    if(gateSum) gateSum.click();
    setTimeout(function(){
      ok(visReal(document.getElementById('camGateManual')), '★点开"连不上？更多方式"→ 手动填按钮出现');
      document.getElementById('camGateManual').click();
      setTimeout(function(){
        ok(vis(document.getElementById('camManualCard')), '★点「手动填 SSID/密码」→ 手动填卡片**自动展开**（不会被折叠藏住）');
        ok(visReal(document.getElementById('camSsid')) && visReal(document.getElementById('camJoin')),
           '手动填里面的 SSID 输入框 / 「记住并连接」都看得见');

        if(bleSum) bleSum.click();
        setTimeout(function(){
          ok(visReal(document.getElementById('bleScan')) && visReal(document.getElementById('bleWake')),
             '★点开"蓝牙工具"→ 扫描 / 唤醒 按钮出现');
          var n2 = 0, a2 = pd.querySelectorAll('button');
          for(var z = 0; z < a2.length; z++) if(!a2[z].classList.contains('dis') && visReal(a2[z])) n2++;
          o.push('  展开两个折叠后可见按钮 ' + n2 + ' 个');

          /* ⑥ 功能真的还能用：没连蓝牙时点「唤醒」→ 只提示、不发帧 */
          window.__bleWrote = 0;
          window.OM3Native = { bleWrite: function(){ window.__bleWrote++; return 'ok'; },
                               bleDisconnect: function(){}, bleScan: function(){}, bleStop: function(){} };
          document.getElementById('bleWake').click();
          setTimeout(function(){
            ok(window.__bleWrote === 0, '★折叠不影响功能：没连蓝牙时点「唤醒」仍然一帧不发');
            ok(String(document.getElementById('bleGatt').textContent).indexOf('相机蓝牙') >= 0,
               '并且明确提示了蓝牙这一步（v2.17 起：没扫到相机时提示"先扫一下蓝牙，找 📷 那条"）');

            /* ⑦ 展开折叠不该把别的页签/状态搞坏 */
            ok(document.getElementById('paneD') && !document.getElementById('paneD').classList.contains('hide'),
               '连接相机页签还在');
            o.push('  累计 js 报错=' + window.__errs.length + '（' + window.__errs.slice(0, 2).join(' | ') + '）');
            ok(window.__errs.length === 0, '无 js 报错');
            o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
            finish(o);
          }, 300);
        }, 250);
      }, 350);
    }, 250);
  }, 900);

  function finish(o){
    var d = document.createElement('pre');
    d.id = 'DBGOUT';
    d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
}, 2400);
"""
tail = '<script>' + JS + '</script>'
i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_camclean.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ocamclean'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,1400',
                    '--virtual-time-budget=20000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=240)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print(dom[k:].split('>', 1)[1].split('</pre>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
