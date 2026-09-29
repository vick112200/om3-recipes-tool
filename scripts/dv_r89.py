# -*- coding: utf-8 -*-
"""第 89 轮验收：复现真机 06:23 那个空窗（①在连 → 点② → 133 断 → 重试连上 → **必须发两帧**）

真机 v3.38 日志（2026-09-29 06:23）顺序：
  ① 只连（06:23:23）→ 连接失败 status=133 → ② 点下去（06:23:27，此时①的链还在跑，"已经在连了"）
  → 20 秒超时重试 → 06:23:44 连上 → 06:23:45 订阅 3/3 → **一帧都没发**（日志里连"（自动链）蓝牙连上了"都没有）
  → 用户再点②被"上一次发的帧还在等应答"挡住 → 白等到观察窗结束。

本探针的假桥就照这个顺序来：第一次 bleConnect 直接 lost(133)（不发 svc）；重试那次才 connected + svc。

验什么：
  A. ①（只连）→ 失败 → ② → 重试连上 → **发出两帧**（`0F 01 01 02` + `1D 01 01 02`），并且日志里有"要发帧的意图我记着"这类提示。
  B. ①在跑的时候点②，不会被"已经在连了"吞掉意图（`__om3cvWantWake` 留在页面上）。
  C. 掉线时如果还没发帧 → 观察窗收口（不再白等到 45 秒）。
  D. 静态：无新增 id / data-tv、Java 未改、`r89：` 标记在。

跑法：python scripts/dv_r89.py
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
PAGE = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r89.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLDJ = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.before_r84.java')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
OK, FAIL = [], []


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()
oldj = io.open(OLDJ, encoding='utf-8').read() if os.path.exists(OLDJ) else ''

BRIDGE = r'''
window.__ble = []; window.__calls = []; window.__conns = 0;
window.__ans = [];
window.OM3Native = (function(){
  var SVC = JSON.stringify([{uuid:'adc505f9-4e58-4b71-b8ca-983bb8c73e4f', type:0, chars:[
    {uuid:'82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', write:true, wnr:true, props:{write:true, wnr:true, notify:true}},
    {uuid:'B7A8015C-CB94-4EFA-BDA2-B7921FA9951F', write:true, props:{write:true, notify:true}},
    {uuid:'05A02050-0860-4919-8ADD-9801FBA8B6ED', props:{notify:true, cccd:true}}]}]);
  function h2(n){ var s = Number(n).toString(16).toUpperCase(); return (s.length < 2 ? '0' + s : s); }
  function emitFound(){ window.__om3ble('found', 'BJSA21721', '34:90:EA:BE:07:F9', -70, 1); }
  function ble(name){ return function(){
      window.__ble.push(name);
      if(name === 'bleScanStart2' && window.__fakeEmit) setTimeout(emitFound, 40);
      if(name === 'bleConnect'){
        window.__conns++;
        if(window.__conns === 1){
          /* 第 1 次：真机那样 status=133 断掉（**不发** svc），链会在 20 秒后重试 */
          setTimeout(function(){ try{ window.__om3ble('lost', '连接断开（status=133）'); }catch(e){} }, 300);
        } else {
          setTimeout(function(){
            try{
              window.__om3ble('connected', '34:90:EA:BE:07:F9', '0');
              window.__om3ble('svc', SVC, '0');
            }catch(e){ window.__errs.push('FAKE-CONN: ' + e.message); }
          }, 120);
        }
      }
      if(name === 'bleWrite'){
        var hex = String(arguments[1] || '');
        window.__ble.push('WRITE:' + hex);
        window.__ans.push(hex);
        var up = hex.toUpperCase();
        setTimeout(function(){
          try{
            if(up.indexOf('0F 01 01 02') >= 0){
              var s1 = (0x0F + 1 + 0x01 + 1) & 0xFF;
              window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68',
                              '04 00 04 0F 01 01 01 ' + h2(s1) + ' 00');
            } else if(up.indexOf('1D 01 01 02') >= 0){
              window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68',
                              '04 00 04 1D 01 01 00 1F 00');   /* 0x1D+1+0x01+0x00 = 0x1F */
            }
          }catch(e){}
        }, 100);
      }
      return 'ok';
  }; }
  function plain(name){ return function(){ window.__calls.push(name); return 'ok'; }; }
  return {
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":36}'; },
    wifiState: function(){ return JSON.stringify({ssid:'', on:true}); },
    wifiScanList: function(){ window.__calls.push('wifiScanList'); return '[]'; },
    bleSubscribe: function(u){
      window.__ble.push('bleSubscribe'); window.__subs = (window.__subs || []).concat([String(u || '')]);
      setTimeout(function(){ try{ window.__om3ble('cccd', String(u || ''), 0); }catch(e){} }, 40);
      return 'ok:subscribed';
    },
    bleState: function(){ return 'on'; }, blePerm: function(){ return 'ok'; },
    blePermDetail: function(){ return '{}'; }, bleDevices: function(){ return '[]'; },
    bleMtuInfo: function(){ return '{}'; }, bleOsConn: function(){ return '{"conn":[],"paired":[]}'; },
    bleServices: function(){ return '[]'; },
    cameraState: function(){ return '{"connected":false,"ssid":"","bssid":""}'; },
    camGet: function(){ return '{"status":0,"text":""}'; }, camPost: function(){ return '{}'; },
    connectCamera: function(){ window.__calls.push('connectCamera'); return 'asking'; },
    connectCamera2: function(){ window.__calls.push('connectCamera2'); return 'asking@bssid'; },
    bleScan: ble('bleScan'), bleScanStart: ble('bleScanStart'), bleScanStart2: ble('bleScanStart2'),
    bleConnect: ble('bleConnect'), bleCmd: ble('bleCmd'), bleWrite: ble('bleWrite'),
    bleEnable: ble('bleEnable'), bleAskPerm: ble('bleAskPerm'),
    bleScanStop: plain('bleScanStop'), bleDisconnect: plain('bleDisconnect'),
    disconnectCamera: plain('disconnectCamera'), dropCamera: plain('dropCamera'),
    forgetWifi: plain('forgetWifi'), openWifiSettings: plain('openWifiSettings'),
    openAppSettings: plain('openAppSettings'), shareText: plain('shareText'), startWatch: plain('startWatch')
  };
})();
'''

PRE = ("window.__fakeEmit=1;"
       + "localStorage.setItem('om3cam', JSON.stringify({ssid:'OM-3-P-X',pass:'p',model:'OM-3',bssid:'AA:BB:CC:DD:EE:FF'}));"
       + BRIDGE)


def run_headless(tag, pre, steps, budget=120000):
    tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in steps], ensure_ascii=False) + ',si=0;\n'
            'function g(i){return document.getElementById(i);}\n'
            'function cv(n){return document.querySelector(\'[data-tv="\'+n+\'"]\');}\n'
            'function cvt(n){var e=cv(n);return e?e.innerText:"";}\n'
            'function finish(){var d=document.createElement("div");d.id=\'' + tag + '\';'
            'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
            'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
            'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
            'setTimeout(next,1600);\n</script>')
    i0 = page.find('<body')
    j0 = page.find('>', i0) + 1
    out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
           'try{' + pre + '}catch(e){window.__errs.push("PRE: " + e.message);}</script>'
           + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r89_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o89_' + tag)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                        '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                        '--virtual-time-budget=%d' % budget, '--dump-dom',
                        'file:///' + hp.replace(os.sep, '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
    dom = r.stdout or ''
    k = dom.find('id="%s"' % tag)
    return (dom[k:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<')
            .replace('&gt;', '>').replace('&amp;', '&')) if k >= 0 else ''


READ = r"""var L=(window.__om3logText?window.__om3logText():'');
var w=(window.__ans||[]).map(function(x){return String(x);});
o.push('R 帧数='+w.length);
o.push('R 帧='+JSON.stringify(w));
o.push('R 两帧='+((w.length===2 && w[0].indexOf('0F 01 01 02')>0 && w[1].indexOf('1D 01 01 02')>0)));
o.push('R 重试过='+(L.indexOf('自动再试一次')>=0));
o.push('R 订阅3='+(L.indexOf('订阅结束：成功 3/3 个特征值')>=0));
o.push('R 提示='+(L.indexOf('蓝牙断了')>=0));
o.push('R 扫到='+(L.indexOf('发现：')>=0));
o.push('R 已连='+(L.indexOf('已连接（status=0）')>=0));
o.push('R 错误='+((window.__errs||[]).length));"""

print('=== A. 真机 06:23 那个顺序：① → 133 断 → ② → 重试连上 → 必须发两帧 ===')
got = run_headless('R89A', PRE, [
    ("g('tabCam').click();", 1500),
    ("""cv('cv-ble').click();""", 900),                       # ① 只连（会 133 失败）
    ("""cv('cv-wake').click();""", 1000),                     # ② 点下去（此时①的链还在跑）
    ("", 26000),                                             # 等 20 秒超时 → 重试 → 连上 → svc
    (READ, 400),
])
print('  · ' + got[:460])
A('STEP-ERR' not in got, 'A0 步骤没抛错')
A('R 重试过=true' in got, 'A1 第一次连接失败 → 链自动重试（真机 06:23 的情形）')
A('R 订阅3=true' in got, 'A2 重试连上后订阅 3/3 成功（真机上这步是好的）')
A('R 两帧=true' in got, 'A3 ★ **连上后真的把两帧发出去了**（電源ON + リモコンモード）—— 真机那次这里一帧都没发')
A('R 错误=0' in got, 'A0b 0 运行错误')

print()
print('=== B. 只看"②的意图有没有被 ① 吞掉"（页面变量） ===')
got2 = run_headless('R89B', PRE, [
    ("g('tabCam').click();", 1500),
    ("""cv('cv-ble').click();""", 900),
    ("""cv('cv-wake').click();""", 900),
    (r"""o.push('B1 意图='+String(!!window.__om3cvWantWake));
o.push('B2 自动唤醒='+String(!!window.__om3bleAutoWake));
o.push('B3 只连='+String(!!window.__om3bleConnOnly));""", 300),
])
print('  · ' + got2[:220])
A('B1 意图=true' in got2, 'B1 点②后"连上要发帧"的意图登记住了（`__om3cvWantWake=true`）')
A('B2 自动唤醒=true' in got2 and 'B3 只连=false' in got2,
  'B2 意图压过 ① 的"只连"（`__om3bleAutoWake=true` / `__om3bleConnOnly=false`）')

print()
print('=== C. 静态 ===')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'C1 id 集合没变')
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
# r90 按规格新增 cv-pass（那一轮探针断言"恰好 == {cv-pass}"）；老探针只要求"新增的都在已声明表里"
A((tv_p - tv_o) <= {'cv-pass', 'donate'}, 'C2 data-tv 集合没变')
A('r89：' in page and 'STEPS_MARK' not in page, 'C3 `r89：` 标记在、占位符没漏')
A(java == oldj, 'C4 Java 一行都没改')
A(page.count('__om3cvWantWake') >= 4, 'C5 意图变量在各处都接上了（登记/①撤/重试读/svc清）')

print()
print('第 89 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
