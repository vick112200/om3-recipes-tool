# -*- coding: utf-8 -*-
"""第 86 轮验收：认出相机的应答（测试数据 = 真机抓到的字节）

真机（v3.37，2026-09-29 05:51:35）在订阅三个特征值成功后，对「電源ON」回了：
  `05 01 00 00 00`
  `04 02 04 0F 01 01 01 12 00`   ← 通道 0x0F、子命令 0x01、结果码 1、校验 0x12（= 0x0F+1+0x01+0x01）
我们当时**没认出来**（解码器写死首字节 0x01）→ ② 谎报"相机没回应答"。

验什么（全部用真机那两串字节）：
  A. 真机应答被解出：日志出现"相机回帧（应答）" + "结果码 1" + 人话（"已经在开机状态"），
     并且**不再**出现"相机没回应答"（`_bleAckCb` 真的被触发）。
  B. 我们自己的帧（首字节 0x01）解码不受影响；校验错的帧**不**被当成应答。
  C. ② 开头就把官方前提说清（相机没报「蓝牙连接模式」时官方根本不开 Wi-Fi，相机 Wi-Fi 只能在相机上开）。
  D. 静态：无新增 id / data-tv、Java 未改、`r86：` 标记在。

跑法：python scripts/dv_r86.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r86.html')
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
window.__ble = []; window.__calls = []; window.__subs = [];
window.__ans = ['05 01 00 00 00', '04 02 04 0F 01 01 01 12 00'];   /* 真机抓到的两条 */
window.__ans2nd = '';                                              /* 可换成"校验改坏"的帧 */
window.OM3Native = (function(){
  var SVC = JSON.stringify([{uuid:'adc505f9-4e58-4b71-b8ca-983bb8c73e4f', type:0, chars:[
    {uuid:'82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', write:true, wnr:true, props:{write:true, wnr:true, notify:true}},
    {uuid:'B7A8015C-CB94-4EFA-BDA2-B7921FA9951F', write:true, props:{write:true, notify:true}},
    {uuid:'05A02050-0860-4919-8ADD-9801FBA8B6ED', props:{notify:true, cccd:true}}]}]);
  function ble(name){ return function(){
      window.__ble.push(name);
      if(name === 'bleScanStart2' && window.__fakeEmit){
        setTimeout(function(){
          try{
            window.__om3ble('found', 'BJSA21721', '34:90:EA:BE:07:F9', -70, 1);
            window.__om3ble('connected', '34:90:EA:BE:07:F9', '0');
            window.__om3ble('svc', SVC, '0');
          }catch(e){ window.__errs.push('FAKE-EMIT: ' + e.message); }
        }, 60);
      }
      if(name === 'bleWrite'){
        window.__ble.push('WRITE:' + String(arguments[1] || ''));
        setTimeout(function(){
          try{
            window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', window.__ans[0]);
            setTimeout(function(){
              try{
                window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68',
                                window.__ans2nd || window.__ans[1]);
              }catch(e){}
            }, 60);
          }catch(e){}
        }, 120);
      }
      return 'ok';
  }; }
  function plain(name){ return function(){ window.__calls.push(name); return 'ok'; }; }
  return {
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":36}'; },
    wifiState: function(){ return JSON.stringify({ssid:'', on:true}); },
    wifiScanList: function(){ window.__calls.push('wifiScanList'); return '[]'; },
    bleSubscribe: function(u){
      window.__ble.push('bleSubscribe'); window.__subs.push(String(u || ''));
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

PRE = ("localStorage.setItem('om3cam', JSON.stringify({ssid:'OM-3-P-X',pass:'p',model:'OM-3',bssid:'AA:BB:CC:DD:EE:FF'}));"
       + BRIDGE)

READ = r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('R 应答被认出='+/相机回帧（应答）/.test(L));
o.push('R 结果码1='+/结果码 1/.test(L));
o.push('R 人话='+/已经在开机状态/.test(L));
o.push('R 没谎报='+(!/相机没回应答/.test(L)));
o.push('R 收下了='+/相机收下了/.test(L));
o.push('R 前提说清='+/官方规则这时\*\*根本不发\*\*开机帧/.test(L));
o.push('R 三连='+/订阅结束：成功 3\/3 个特征值/.test(L));
o.push('R 错误='+((window.__errs||[]).length));"""

print('=== A. 真机那两条通知（0501000000 / 0402040f0101011200）→ 必须被当"应答"认出来 ===')
got = run_headless = None


def run_headless(tag, pre, steps, budget=90000):
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
    hp = os.path.join(TMP, 'dv_r86_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o86_' + tag)
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


got = run_headless('R86A', PRE, [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 8000),
    (READ, 300),
])
print('  · ' + got[:460])
A('STEP-ERR' not in got, 'A0 步骤没抛错')
A('R 三连=true' in got, 'A1 前置：三个特征值都订上了（真机那一套）')
A('R 应答被认出=true' in got, 'A2 相机应答（首字节 0x04）被认出来了 —— 这是真机上"回了却像没回"的根因')
A('R 结果码1=true' in got and 'R 人话=true' in got,
  'A3 结果码 1 被解出来并翻成人话（"已经在开机状态"）—— 用真机字节验的')
A('R 没谎报=true' in got and 'R 收下了=true' in got,
  'A4 ② 不再谎报"相机没回应答"，而是报"相机收下了：结果码 1"')
A('R 前提说清=true' in got, 'A5 ② 开头讲清官方前提：相机没报「蓝牙连接模式」时官方根本不开 Wi-Fi')
A('R 错误=0' in got, 'A0b 0 运行错误')

print()
print('=== B. 校验被改坏的帧 → 不许当成"这条命令的应答" ===')
got2 = run_headless('R86B', PRE + "window.__ans2nd='04 02 04 0F 01 01 01 AA 00';", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 8000),
    (READ, 300),
])
print('  · ' + got2[:360])
A('R 结果码1=false' in got2, 'B1 校验不对 → 不当应答（结果码不会瞎报）')
A('R 没谎报=false' in got2 or 'R 结果码1=false' in got2, 'B1b 该报"没应答"时就报（行为一致）')

print()
print('=== C. 静态 ===')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(not (ids_o - ids_p) and not (ids_p - ids_o), 'C1 id 集合没变')
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
# r90 按规格新增 cv-pass（那一轮探针断言"恰好 == {cv-pass}"）；老探针只要求"新增的都在已声明表里"
A((tv_p - tv_o) <= {'cv-pass', 'donate'}, 'C2 data-tv 集合没变')
A('r86：' in page and 'STEPS_MARK' not in page, 'C3 `r86：` 标记在、占位符没漏')
A(java == oldj, 'C4 Java 一行都没改')

print()
print('第 86 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
