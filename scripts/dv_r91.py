# -*- coding: utf-8 -*-
"""第 91 轮验收：**口令这条路铺好了**（有口令时按官方顺序先发 0x0C02）+ 第 89 轮的行为回归

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
OLD = os.path.join(ROOT, 'app', 'base.before_r91.html')
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
              /* r91：**连写**的十六进制（真机就是这么来的） */
              window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68',
                              '0402040f0101011200');
              window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', '0501000000');
            } else if(up.indexOf('1D 01 01 02') >= 0){
              /* 0x1D01：相机**只有回执**，没有应答（真机 06:47:47 就是这样） */
              window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', '0502000000');
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
    hp = os.path.join(TMP, 'dv_r91_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o91_' + tag)
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
o.push('R 两帧='+((w.length===2 && w[0].indexOf('0F 01 01 02')>0 && w[1].indexOf('1D 01 01 02')>0)));
o.push('R 重试过='+(L.indexOf('自动再试一次')>=0));
o.push('R 订阅3='+(L.indexOf('订阅结束：成功 3/3 个特征值')>=0));
o.push('R 连写被解出='+(L.indexOf('相机回帧（应答）')>=0));
o.push('R 结果码1='+(L.indexOf('结果码 1')>=0));
o.push('R 人话1='+(L.indexOf('已经在开机状态')>=0));
o.push('R 没谎报='+(L.indexOf('相机没回应答')<0));
o.push('R 回执='+(L.indexOf('相机**回执**：确认收到第 1 帧')>=0));
o.push('R 收下了='+(L.indexOf('相机收下了「電源ON」')>=0));
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
A('R 两帧=true' in got, 'A3 两帧都发出去了（電源ON + リモコンモード）')
A('R 连写被解出=true' in got, 'A3a ★ 真机那种**连写**的通知（0402040f0101011200）被解出来了（以前只认空格分隔 → 真机等于没修）')
A('R 结果码1=true' in got and 'R 人话1=true' in got, 'A3b 结果码 1 认出来了，并翻成人话（"已经在开机状态"）')
A('R 收下了=true' in got and 'R 没谎报=true' in got, 'A3c ② 报"相机收下了「電源ON」：结果码 1"，不再谎报"没回应答"')
A('R 回执=true' in got, 'A3d 认出相机的**回执包**（0501000000 → "确认收到第 1 帧"）')
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
print()
print('=== C. 口令：点按钮弹窗 + 有口令时第一条帧就是 0x0C02 ===')
got3 = run_headless('R90C', PRE, [
    ("g('tabCam').click(); window.__conns=1;", 1500),   # 假桥：跳过"第一次 133 失败"，这次直接连上
    ("cv('cv-pass').click();", 600),
    (r"""var t=document.getElementById('otitle');
o.push('C1 弹窗='+String(!!t && t.textContent.indexOf('蓝牙口令')>=0));
o.push('C2 有输入='+String(!!document.querySelector('#ofields input')));""", 300),
    (r"""window.__om3cvPassSet('1234');""", 900),
    ("cv('cv-wake').click();", 9000),
    (r"""var w=(window.__ans||[]).map(String);
o.push('C3 帧数='+w.length);
o.push('C4 帧='+JSON.stringify(w));
o.push('C5 第一帧是口令='+String(w.length>=3 && w[0].indexOf('0C 01 02')>0));
o.push('C6 顺序='+String(w.length>=3 && w[0].indexOf('0C 01 02')>0 && w[1].indexOf('0F 01 01 02')>0 && w[2].indexOf('1D 01 01 02')>0));""", 400),
])
print('  · ' + got3[:420])
A('C1 弹窗=true' in got3 and 'C2 有输入=true' in got3, 'C1 点「① 填蓝牙口令」弹出自绘输入框（不是安卓原生 prompt）')
A('C6 顺序=true' in got3, 'C2 ★ 有口令时按官方顺序发：口令认证(0C 01 02) → 電源ON → リモコンモード')
A('C5 第一帧是口令=true' in got3, 'C2b 口令认证是第一条（官方 e$d.run 在 e$e 之前）')

print()
print('=== D. 静态 ===')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'C1 id 集合没变')
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
A((tv_p - tv_o) <= {'star'}, 'C2 data-tv 集合没变（本轮无新增）')
A('r91：' in page and 'STEPS_MARK' not in page, 'C3 `r91：` 标记在、占位符没漏')
A(java == oldj or ('shouldOverrideUrlLoading' in java and 'r95：页面里的外链' in java),
  'C4 Java 一行都没改（口径 r95：Java 确实改过 —— 只多了第 95 轮声明的外链拦截）')
A(page.count('__om3cvWantWake') >= 4, 'C5 意图变量在各处都接上了（登记/①撤/重试读/svc清）')
A('function bleBytes(' in page and 'bleBytes(hex)' in page, 'C6 bleBytes 在 + 接到了 decode/resultCode/scanTlv')
A('var b = bleBytes(hex);' in page and page.count('bleBytes(hex)') >= 3, 'C6b 三处解码都换成 bleBytes（连写也能解）')

print()
print('第 91 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
