# -*- coding: utf-8 -*-
""""点了没反应"体检（**行为**检查，不是看代码）：逐个点 paneD/paneT 里可见的按钮，
看点了之后有没有**任何可观察的变化**（日志多了一行 / DOM 变了 / 浮层开了 / 调了原生）。

需求方 2026-09-28：「点了没啥反应」——根因是第 74 轮把「扫码连接」按钮放回来时**没接上功能**
（它的 click 只有 `showStep(1)`）。`scripts/audit_buttons.py` 只能筛"完全没人引用"的按钮，
**筛不出"有处理器但什么都没做"**——所以要有这个行为版。

判定：点之前记 (日志长度, body HTML 摘要, 可见浮层集合, 原生调用数)；点后等 400ms 再记一次；
四项全都没变 → 记"无可见反应"。有些按钮在特定状态下本来就"没必要反应"（如"停止"没在跑时），
所以输出是**给人看的清单**，不是断言。

用法：python scripts/audit_deadclicks.py [paneD paneT]
"""
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
PAGE = os.path.join(ROOT, 'app', 'base.html')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')

page = io.open(PAGE, encoding='utf-8').read()

# 假桥：把原生调用记下来（既能保证不报错，也能当"有反应"的依据）
BRIDGE = r'''
window.__calls = [];
window.OM3Native = (function(){
  function rec(n){ return function(){ window.__calls.push(n); return '{"s":200,"t":"ok"}'; }; }
  var API = {
    permState: function(){ window.__calls.push('permState'); return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
    wifiState: function(){ window.__calls.push('wifiState'); return JSON.stringify({ssid:'我家WiFi', on:true}); },
    wifiScanList: function(){ window.__calls.push('wifiScanList'); return JSON.stringify([{ssid:'OM-3', bssid:'AA:BB:CC:DD:EE:FF', level:-42, cam:true}]); },
    cameraState: function(){ window.__calls.push('cameraState'); return '{"connected":false,"ssid":"","bssid":""}'; },
    blePermDetail: function(){ window.__calls.push('blePermDetail'); return '{}'; },
    startWatch: rec('startWatch'), ensureCamera: rec('ensureCamera'), camGet: rec('camGet'),
    camGetAsync: function(p){ window.__calls.push('camGetAsync'); var id='s'+window.__calls.length; setTimeout(function(){ try{ window.__om3http(id, {s:200,t:'{"result":"ok"}'}); }catch(e){} }, 20); return id; },
    camPost: rec('camPost'), camPostAsync: function(p,b){ window.__calls.push('camPostAsync'); var id='p'+window.__calls.length; setTimeout(function(){ try{ window.__om3http(id, {s:200,t:'{"result":"ok"}'}); }catch(e){} }, 20); return id; },
    bleScanStop: rec('bleScanStop'), bleDisconnect: rec('bleDisconnect'), dropCamera: rec('dropCamera'),
    forgetWifi: rec('forgetWifi'), openWifiSettings: rec('openWifiSettings'), openAppSettings: rec('openAppSettings'),
    shareText: rec('shareText'), disconnectCamera: rec('disconnectCamera'), bleScanStart: rec('bleScanStart'),
    bleConnect: rec('bleConnect'), bleCmd: rec('bleCmd'), bleWrite: rec('bleWrite'), bleAskPerm: rec('bleAskPerm')
  };
  return API;
})();
'''

STEP = r'''
var IDS = __IDS__;
var i = 0, RES = [];
function snapshot(){
  var vis = [];
  var all = document.querySelectorAll('div[id$="Mask"], div[id*="Mask"], #omask, #taskMask, #scanMask, #toc, #toc2, #lb, #camMenuDrop');
  for(var k = 0; k < all.length; k++){
    try{ var c = getComputedStyle(all[k]); if(c.display !== 'none' && c.visibility !== 'hidden') vis.push(all[k].id); }catch(e){}
  }
  return { log: (window.__om3logText ? window.__om3logText().length : 0),
           html: document.body.innerHTML.length,
           vis: vis.join(','),
           calls: (window.__calls || []).length };
}
function same(a, b){ return a.log === b.log && a.html === b.html && a.vis === b.vis && a.calls === b.calls; }
function step(){
  if(i >= IDS.length){ done(); return; }
  var id = IDS[i++];
  var el = document.getElementById(id);
  if(!el){ RES.push(id + '=没这个元素'); setTimeout(step, 5); return; }
  var c = getComputedStyle(el);
  if(c.display === 'none' || c.visibility === 'hidden' || el.getBoundingClientRect().height === 0){
    RES.push(id + '=不可见(跳过)'); setTimeout(step, 5); return;
  }
  var before = snapshot();
  try{ el.click(); }catch(e){ RES.push(id + '=点出错:' + e.message); setTimeout(step, 5); return; }
  setTimeout(function(){
    var after = snapshot();
    RES.push(id + (same(before, after) ? '=**无可见反应**' : '=有反应'));
    setTimeout(step, 5);
  }, 420);
}
function done(){
  var dead = RES.filter(function(x){ return /无可见反应|点出错|没这个元素/.test(x); });
  var d = document.createElement('div'); d.id = 'RAD';
  d.textContent = '共 ' + IDS.length + ' 个｜可疑 ' + dead.length + '：' + dead.join(' ｜ ');
  document.body.appendChild(d);
}
setTimeout(step, 1200);
'''


def main():
    panes = sys.argv[1:] or ['paneD', 'paneT']
    s = page
    i0 = s.index('<div id="paneD"')
    i1 = s.index('<div id="paneE"')
    seg = s[i0:i1]
    import re
    ids = re.findall(r'<button[^>]*\bid="([A-Za-z0-9_]+)"', seg)
    ids = [x for x in ids if x not in ('tvBack',)]          # tvBack 会切走页面，跳过
    tail = '<script>' + BRIDGE + STEP.replace('__IDS__', json.dumps(ids)) + '</script>'
    j0 = s.find('>', s.find('<body')) + 1
    out = s[:j0] + tail + s[j0:]
    hp = os.path.join(TMP, 'audit_clicks.html')
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'oaudit')
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                        '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,900',
                        '--virtual-time-budget=120000', '--dump-dom',
                        'file:///' + hp.replace(os.sep, '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=600)
    dom = r.stdout or ''
    k = dom.find('id="RAD"')
    txt = (dom[k:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<').replace('&gt;', '>')
           .replace('&amp;', '&')) if k >= 0 else '（没拿到结果 —— 可能页面报错了）'
    print('=== "点了没反应"行为体检（%s）===' % '+'.join(panes))
    # 先切到连接相机页（客户页），再逐个点
    for part in txt.split(' ｜ '):
        print('   ' + part)
    return 0


if __name__ == '__main__':
    sys.exit(main())
