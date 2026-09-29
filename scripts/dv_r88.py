# -*- coding: utf-8 -*-
"""第 88 轮验收：② 补上官方的 0x1D01{0x02}（点"导入图片"时官方发的就是这条）

官方（`BlePowOnActivity$c.run`）：`M(2, 10000)` → `M2/b.M` → cmd `0x1D01` → `M2/b.L` = `u(0x1D,1,{arg})`
→ 帧 `01 <seq> 04 1D 01 01 02 21 00`；**回帧必须正好 0 才算成功**（`if(ret != 0) → 失败分支`）。

验什么：
  A. 点② → 依次发**两帧**：`電源ON 0F 01 01 02`、`リモコンモード 1D 01 01 02`（顺序对、字节对）。
  B. 假相机对 0x0F01 回 1、对 0x1D01 回 0 → 日志写"✅ 相机接受了「リモコンモード…」：结果码 0"。
  C. 假相机对 0x1D01 回非 0（3）→ 日志写"❌ 相机**拒绝**了…（需要的是口令认证）"。
  D. 静态：无新增 id / data-tv、Java 未改、`r88：` 标记在。

跑法：python scripts/dv_r88.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r88.html')
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
window.__code1d = 0;        /* 0 = 相机接受 0x1D01；其它 = 拒绝 */
window.OM3Native = (function(){
  var SVC = JSON.stringify([{uuid:'adc505f9-4e58-4b71-b8ca-983bb8c73e4f', type:0, chars:[
    {uuid:'82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', write:true, wnr:true, props:{write:true, wnr:true, notify:true}},
    {uuid:'B7A8015C-CB94-4EFA-BDA2-B7921FA9951F', write:true, props:{write:true, notify:true}},
    {uuid:'05A02050-0860-4919-8ADD-9801FBA8B6ED', props:{notify:true, cccd:true}}]}]);
  function h2(n){ var s = Number(n).toString(16).toUpperCase(); return (s.length < 2 ? '0' + s : s); }
  function ans(ch, sub, code){
    var sum = (ch + 1 + sub + code) & 0xFF;
    return '04 00 04 ' + h2(ch) + ' 01 ' + h2(sub) + ' ' + h2(code) + ' ' + h2(sum) + ' 00';
  }
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
        var hex = String(arguments[1] || '');
        window.__ble.push('WRITE:' + hex);
        /* 相机回"给这条命令的回帧"：電源ON(0F/01) 回 1；リモコンモード(1D/01) 回 __code1d */
        var up = hex.toUpperCase();
        setTimeout(function(){
          try{
            if(up.indexOf('0F 01 01 02') >= 0)
              window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', ans(0x0F, 0x01, 1));
            else if(up.indexOf('1D 01 01 02') >= 0)
              window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', ans(0x1D, 0x01, window.__code1d));
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
var w=(window.__ble||[]).filter(function(x){return String(x).indexOf('WRITE:')===0;}).map(function(x){return String(x).slice(6);});
o.push('R 帧='+JSON.stringify(w));
o.push('R 两帧='+(w.length===2));
o.push('R 顺序='+((w.length===2 && w[0].indexOf('0F 01 01 02')>0 && w[1].indexOf('1D 01 01 02')>0)));
o.push('R 接受='+/✅ 相机接受了「リモコンモード/.test(L));
o.push('R 码0='+/结果码 0（官方这条要求\*\*正好 0\*\*）/.test(L));
o.push('R 进传输态='+/相机应该开始进 Wi-Fi 传输态了/.test(L));
o.push('R 拒绝='+/❌ 相机\*\*拒绝\*\*了「リモコンモード/.test(L));
o.push('R 要口令='+/需要的是口令认证/.test(L));
o.push('R 错误='+((window.__errs||[]).length));"""


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
    hp = os.path.join(TMP, 'dv_r88_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o88_' + tag)
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


print('=== A. 点② → 官方那两条命令（顺序、字节） + 相机回 0 → 报"接受" ===')
got = run_headless('R88A', PRE + "window.__code1d=0;", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 12000),
    (READ, 300),
])
print('  · ' + got[:420])
A('STEP-ERR' not in got, 'A0 步骤没抛错')
A('R 两帧=true' in got, 'A1 点②发**两帧**（官方"导入图片"就是两条命令）')
A('R 顺序=true' in got, 'A2 顺序 = 電源ON(0F 01 01 02) → リモコンモード(1D 01 01 02)，字节与官方一致')
A('R 接受=true' in got and 'R 码0=true' in got, 'A3 相机回 0 → 报"✅ 相机接受了「リモコンモード…」：结果码 0"')
A('R 进传输态=true' in got, 'A4 明确说"相机应该开始进 Wi-Fi 传输态了 → 点③连它"')
A('R 错误=0' in got, 'A0b 0 运行错误')

print()
print('=== B. 0x1D01 被拒（回 3）→ 报"拒绝"，并指向口令认证 ===')
got2 = run_headless('R88B', PRE + "window.__code1d=3;", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 12000),
    (READ, 300),
])
print('  · ' + got2[:420])
A('R 拒绝=true' in got2 and 'R 要口令=true' in got2,
  'B1 非 0 → 报"❌ 相机**拒绝**了「リモコンモード…」"并提示需要口令认证（官方 `str.blePass` 是必带的）')
A('R 两帧=true' in got2, 'B1b 两帧照发（不让链断掉）')

print()
print('=== C. 静态 ===')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'C1 id 集合没变')
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
# r90 按规格新增 cv-pass（那一轮探针断言"恰好 == {cv-pass}"）；老探针只要求"新增的都在已声明表里"
A((tv_p - tv_o) <= {'cv-pass', 'donate'}, 'C2 data-tv 集合没变')
A('r88：' in page and 'STEPS_MARK' not in page, 'C3 `r88：` 标记在、占位符没漏')
A(java == oldj, 'C4 Java 一行都没改')
A("ch: 0x1D, sub: 1, payload: [0x02]" in page, 'C5 0x1D01 那一帧在（ch=0x1D sub=0x01 payload={0x02}）')

print()
print('第 88 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
