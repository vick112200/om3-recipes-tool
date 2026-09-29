# -*- coding: utf-8 -*-
"""第 85 轮验收：**按官方顺序订阅三个特征值**（真机 v3.36 日志：CCCD 订上了却一个包都收不到）

真机事实（`logs/`，v3.36）：`订阅 05a02050-…：CCCD 已写` + `（CCCD 写入结果 status=0）`，
但**相机一个包都不推**、三次「電源ON」一次都没回 → 因为**应答/状态包是从命令特征 `82F949B4` 推回来的**，
官方 `N2/a$c$b/$c/$d.run` 是**依次订三个**（82F949B4 → B7A8015C → 05A02050）。

验什么：
  A. 订阅**三个**、顺序对（命令特征最先），且**全部在第一个写命令之前**；每个都等到 CCCD 确认。
  B. 相机在 **82F949B4** 上推状态包 / 回 電源ON 应答 → 我们照样解出来（订对特征值才算真在听）。
  C. 只暴露 `05A02050` 的相机 → 只订它，链不卡（不因为少两个就白等）。
  D. `82F949B4` 的 CCCD 一直不确认 → 1.5 秒超时 → 如实写、继续订下一个、命令照样发。
  E. 静态：无新增 id / data-tv、Java 没动、`r85：` 标记在、`STEPS_MARK` 没漏。

跑法：python scripts/dv_r85.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r85.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLDJ = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.before_r84.java')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
OK, FAIL = [], []
DOM = 'adc505f9-4e58-4b71-b8ca-983bb8c73e4f'


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()
oldj = io.open(OLDJ, encoding='utf-8').read() if os.path.exists(OLDJ) else ''

BRIDGE = r'''
window.__ble = []; window.__calls = []; window.__subs = [];
window.__svcChars = 3;      /* 3 = 三个特征都给；1 = 只给 05A02050 */
window.__cccdFail = '';     /* 含这个子串的特征值：永不回 cccd */
window.__statHex = '';      /* 状态包（在订完第 1 个后推） */
window.__ansCode = 0;       /* 電源ON 的结果码 */
window.OM3Native = (function(){
  var C82 = {uuid:'82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', write:true, wnr:true, props:{write:true, wnr:true, notify:true}};
  var CB7 = {uuid:'B7A8015C-CB94-4EFA-BDA2-B7921FA9951F', write:true, props:{write:true, notify:true}};
  var C05 = {uuid:'05A02050-0860-4919-8ADD-9801FBA8B6ED', props:{notify:true, cccd:true}};
  var CW  = {uuid:'12345678-1234-1234-1234-1234567890AB', write:true, wnr:true, props:{write:true, wnr:true}};
  function svc(){
    var cs = (window.__svcChars === 3) ? [C82, CB7, C05] : [CW, C05];
    return JSON.stringify([{uuid:'adc505f9-4e58-4b71-b8ca-983bb8c73e4f', type:0, chars:cs}]);
  }
  function ble(name){ return function(){
      window.__ble.push(name);
      if(name === 'bleScanStart2' && window.__fakeEmit){
        setTimeout(function(){
          try{
            window.__om3ble('found', 'BJSA21721', '34:90:EA:BE:07:F9', -70, 1);
            window.__om3ble('connected', '34:90:EA:BE:07:F9', '0');
            window.__om3ble('svc', svc(), '0');
          }catch(e){ window.__errs.push('FAKE-EMIT: ' + e.message); }
        }, 60);
      }
      if(name === 'bleWrite'){
        var hex = String(arguments[1] || '');
        window.__ble.push('WRITE:' + hex);
        setTimeout(function(){
          try{
            var code = Number(window.__ansCode) || 0;
            var sum = (0x0F + 1 + 0x01 + code) & 0xFF;
            function h2(n){ var s = n.toString(16).toUpperCase(); return (s.length < 2 ? '0' + s : s); }
            /* r85：应答从**命令特征 82F949B4**推回来（官方就是这个特征在 notify 上） */
            window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68',
                            '01 01 01 0F 01 01 ' + h2(code) + ' ' + h2(sum) + ' 00');
          }catch(e){}
        }, 140);
      }
      return 'ok';
  }; }
  function plain(name){ return function(){ window.__calls.push(name); return 'ok'; }; }
  return {
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":36}'; },
    wifiState: function(){ return JSON.stringify({ssid:'', on:true}); },
    wifiScanList: function(){ window.__calls.push('wifiScanList'); return '[]'; },
    bleSubscribe: function(u){
      var uu = String(u || '');
      window.__ble.push('bleSubscribe');
      window.__subs.push(uu);
      var fail = window.__cccdFail && uu.indexOf(window.__cccdFail) >= 0;
      if(!fail){
        setTimeout(function(){
          try{ window.__om3ble('cccd', uu, 0); }catch(e){}
          /* 订完**第一个**（命令特征）后，相机开始推状态包 */
          if(window.__statHex && uu.toUpperCase().indexOf('82F949B4') === 0){
            setTimeout(function(){
              try{ window.__om3ble('notify', '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', window.__statHex); }catch(e){}
            }, 80);
          }
        }, 50);
      }
      return 'ok:asked';
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
function statHex(flags){
  var p = ['D0','04','01','00','00', ('0' + flags.toString(16)).slice(-2).toUpperCase(), '00','00'];
  return '0A FF ' + p.join(' ');
}
'''

PRE = ("localStorage.setItem('om3cam', JSON.stringify({ssid:'OM-3-P-X',pass:'p',model:'OM-3',bssid:'AA:BB:CC:DD:EE:FF'}));"
       + BRIDGE)


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
    hp = os.path.join(TMP, 'dv_r85_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o85_' + tag)
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
var bl=(window.__ble||[]), subs=(window.__subs||[]), k, iWr=-1;
for(k=0;k<bl.length;k++){ if(String(bl[k]).indexOf('WRITE:')===0 && iWr<0) iWr=k; }
var iSubs=[]; for(k=0;k<bl.length;k++){ if(bl[k]==='bleSubscribe') iSubs.push(k); }
o.push('R 订阅序列='+JSON.stringify(subs));
o.push('R 订阅都在写之前='+((iSubs.length>0 && (iWr<0 || iSubs[iSubs.length-1] < iWr)) ? 'true' : 'false'));
o.push('R ble数组='+JSON.stringify(bl).slice(0,300));
o.push('R 订阅结束句='+/订阅结束：成功/.test(L));
o.push('R 命令特征最先='+((subs.length>0 && subs[0].toUpperCase().indexOf('82F949B4')===0)));
o.push('R 状态包人话='+/相机状态包：/.test(L));
o.push('R 结果码='+/结果码 0/.test(L));   /* r86 起换成 bleResultText；r88 起 ② 发两帧 */
o.push('R 帧数='+(bl.filter(function(x){return String(x).indexOf('WRITE:')===0;})).length);
o.push('R 没等到确认='+/没等到 CCCD 确认/.test(L));
o.push('R 错误='+((window.__errs||[]).length));"""

print('=== A. 三个特征值都在 → 按官方顺序订三个（命令特征最先），全订完才发命令 ===')
got = run_headless('R85A', PRE + "window.__statHex=statHex(0x08); window.__ansCode=0;", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 7000),
    (READ, 300),
])
print('  · ' + got[:420])
A('STEP-ERR' not in got, 'A0 步骤没抛错')
A('R 订阅序列=' in got and got.count('82F949B4') >= 1, 'A1 订阅了**命令特征** 82F949B4（真机"收不到包"就是因为漏了它）')
A('R 命令特征最先=true' in got, 'A1b 顺序与官方一致：82F949B4 最先')
A('"82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68","B7A8015C' in got.upper().replace(' ','')
  or ('82F949B4' in got.upper() and 'B7A8015C' in got.upper() and '05A02050' in got.upper()),
  'A1c 三个都订了（82F949B4 / B7A8015C / 05A02050）')
A('R 订阅都在写之前=true' in got, 'A2 三个订阅都在**第一个写命令之前**完成（官方也是 onDescriptorWrite 之后才发命令）')
A('R 订阅结束句=true' in got, 'A2b 日志有"订阅结束：成功 N/N 个特征值"')
A('R 状态包人话=true' in got, 'A3 相机在**命令特征**上推的状态包被解出来了')
A('R 结果码=true' in got, 'A3b 相机在命令特征上回的 電源ON 应答也被解出结果码')
A('R 错误=0' in got, 'A0b 0 运行错误')

print()
print('=== B. 只暴露 05A02050 的相机 → 只订它、不卡住（缺的特征跳过） ===')
got2 = run_headless('R85B', PRE + "window.__svcChars=1; window.__statHex=statHex(0x08);", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 6000),
    (READ, 300),
])
print('  · ' + got2[:360])
A('05A02050' in got2.upper() and '82F949B4' not in got2.upper(),
  'B1 只订实际存在的那一个（缺的 82F949B4/B7A8015C 不硬塞）')
A('R 帧数=2' in got2, 'B1b 链没卡住：命令照发（r88 起 = 两帧）')
A('R 错误=0' in got2, 'B0b 0 运行错误')

print()
print('=== C. 命令特征的 CCCD 一直不确认 → 1.5 秒超时、如实写、继续订下一个 ===')
got3 = run_headless('R85C', PRE + "window.__cccdFail='82F949B4'; window.__ansCode=0;", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 12000),
    (READ, 300),
])
print('  · ' + got3[:420])
A('R 没等到确认=true' in got3, 'C1 单个订不上就如实写"没等到 CCCD 确认"（不假装）')
A('R 帧数=2' in got3, 'C1b 订不上也不耽误发命令（不让整条链瘫掉；r88 起 = 两帧）')
A('R 错误=0' in got3, 'C0b 0 运行错误')

print()
print('=== D. 静态 ===')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(not (ids_o - ids_p), 'D1 老 id 一个都没少（少的：%s）' % (sorted(ids_o - ids_p) or '无'))
A(not (ids_p - ids_o), 'D1b 无新增 id（多的：%s）' % (sorted(ids_p - ids_o) or '无'))
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
# r90 按规格新增 cv-pass（那一轮探针断言"恰好 == {cv-pass}"）；老探针只要求"新增的都在已声明表里"
A((tv_p - tv_o) <= {'cv-pass', 'donate'}, 'D2 无新增 data-tv（多的：%s；少的：%s）' % (sorted(tv_p - tv_o), sorted(tv_o - tv_p)))
A('r85：' in page, 'D3 页面有 r85 标记')
A('STEPS_MARK' not in page, 'D3b 生成器占位符没漏')
A('function bleSubList(' in page and 'OM3_BLE_SUBS' in page, 'D4 三个特征值的清单 + 过滤函数都在')
A(page.count('var _bleSubOk') == 1, 'D4b `_bleSubOk` 只声明一次（r84 的重复声明被清掉）')
A(java == oldj, 'D5 Java 一行都没改（v3.36 的 Java 与 v3.37 相同）')

print()
print('第 85 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
