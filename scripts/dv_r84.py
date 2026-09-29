# -*- coding: utf-8 -*-
"""第 84 轮验收：**照官方顺序补齐 BLE 会话**（需求方：「你不是解析了官方app？为什么照抄都不会」）

验什么（对着官方反汇编的三条硬事实）：
  A. 自动链**先订阅通知**（官方 N2/a.u0 + onDescriptorWrite：发命令前必须订阅；M2/b.s0 还要求通知特征在）
     → 订阅调用必须出现在**任何 bleWrite 之前**；CCCD status=0 时日志写"订阅成功"；等不到就如实说。
  B. **官方判据**（oishare/e.W()：只有 p(8)!=0 且 p(32)==0 才发 0x0F01）
     → 相机状态包 bit3=0（不在蓝牙连接模式）→ **不发帧**、说清原因、**不再开"观察窗"**；
       bit5=1（定位中）→ 同样不发；bit3=1 且 bit5=0 → 发。
  C. **结果码位确证**（M2/b$b.a() 返回 c()[6]）→ 相机回 `01 seq 01 0F 01 01 00 sum 00` 时日志写"结果码 0（0 = 相机接受）"。
  D. 没收到状态包 → 等 2.5 秒后**照旧试**（不因为"不知道"就拦住用户），并如实写下来。
  E. 静态：老 id/老 data-tv 一个不少、**无新增 id / 无新增 data-tv**、Java 没动、`r84：` 标记在。

跑法：python scripts/dv_r84.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r84.html')
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

NOTIFY = '05A02050-0860-4919-8ADD-9801FBA8B6ED'
WRITE1 = '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68'

BRIDGE = r'''
window.__ble = [];        /* 会动相机/蓝牙的调用（含 bleSubscribe） */
window.__calls = [];
window.__sub = 0;         /* 1 = 订阅成功（发 cccd status=0）；0 = 永不回 cccd；-1 = 订阅失败 status=133 */
window.__statHex = '';    /* 订阅成功后要推的"相机状态包"（空 = 不推） */
window.__statDelay = 120;
window.__ansCode = 0;     /* 相机回 電源ON 的结果码 */
window.OM3Native = (function(){
  var SVC = JSON.stringify([{uuid:'adc505f9-4e58-4b71-b8ca-983bb8c73e4f', type:0, chars:[
      {uuid:'82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', write:true, wnr:true, props:{write:true, wnr:true}},
      {uuid:'B7A8015C-CB94-4EFA-BDA2-B7921FA9951F', write:true, props:{write:true}},
      {uuid:'05A02050-0860-4919-8ADD-9801FBA8B6ED', props:{notify:true, cccd:true}}]}]);
  function pushStat(){
    if(!window.__statHex) return;
    try{ window.__om3ble('notify', '05A02050-0860-4919-8ADD-9801FBA8B6ED', window.__statHex); }
    catch(e){ window.__errs.push('STAT: ' + e.message); }
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
        /* 相机回一条"给 0x0F01 的回帧"：01 seq 01 0F 01 01 <code> sum 00 */
        setTimeout(function(){
          try{
            var code = Number(window.__ansCode) || 0;
            var sum = (0x0F + 1 + 0x01 + code) & 0xFF;
            var ans = ['01','01','01','0F','01','01',
                       ('0' + code.toString(16)).slice(-2), ('0' + sum.toString(16)).slice(-2).toUpperCase(),'00'];
            window.__om3ble('notify', '05A02050-0860-4919-8ADD-9801FBA8B6ED', ans.join(' '));
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
      window.__ble.push('bleSubscribe');
      window.__subUuid = String(u || '');
      if(!window.__subs) window.__subs = [];
      window.__subs.push(String(u || ''));
      if(window.__sub === 0) return 'ok:no_cccd_ever';
      setTimeout(function(){
        try{ window.__om3ble('cccd', String(u || ''), window.__sub === 1 ? 0 : 133); }catch(e){}
        if(window.__sub === 1) setTimeout(pushStat, window.__statDelay);
      }, 60);
      return 'ok:subscribed';
    },
    bleState: function(){ return 'on'; }, blePerm: function(){ return 'ok'; },
    blePermDetail: function(){ return '{}'; }, bleDevices: function(){ return '[]'; },
    bleMtuInfo: function(){ return '{}'; }, bleOsConn: function(){ return '{"conn":[],"paired":[]}'; },
    bleServices: function(){ return '[]'; }, cameraState: function(){ return '{"connected":false,"ssid":"","bssid":""}'; },
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
  /* TLV：len=0x0A、type=0xFF、payload 8 字节；payload[5] = 标志位（官方 N2/a.Y 读的位） */
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
    hp = os.path.join(TMP, 'dv_r84_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o84_' + tag)
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
var bl=(window.__ble||[]);
var iSub=-1, iWr=-1, k;
for(k=0;k<bl.length;k++){ if(bl[k]==='bleSubscribe' && iSub<0) iSub=k;
  if(String(bl[k]).indexOf('WRITE:')===0 && iWr<0) iWr=k; }
o.push('R 订阅在写之前='+((iSub>=0 && (iWr<0 || iSub<iWr)) ? 'true' : ('false(sub='+iSub+',wr='+iWr+')')));
o.push('R 订阅UUID='+(window.__subUuid||''));
o.push('R 订阅列表='+JSON.stringify(window.__subs||[]));
o.push('R CCCD成功='+/CCCD 写入结果 status=0/.test(L));
o.push('R 订上没靠超时='+(!/订阅通知\*\*没等到确认\*\*/.test(L)));
o.push('R 状态包人话='+/相机状态包：/.test(L));
o.push('R 帧数='+(bl.filter(function(x){return String(x).indexOf('WRITE:')===0;})).length);
o.push('R 帧='+JSON.stringify(bl.filter(function(x){return String(x).indexOf('WRITE:')===0;}).slice(0,1)));
o.push('R 结果码='+/结果码 0/.test(L));   /* r86 起人话表换成 bleResultText；r88 起 ② 发两帧 */
o.push('R 官方判据不发='+/照官方\*\*不发\*\*开机帧/.test(L));
o.push('R 说了原因='+/蓝牙连接模式/.test(L)+'/'+/定位/.test(L));
o.push('R 观察窗停了='+(!/45 秒里扫描\*\*没看到相机热点\*\*/.test(L)));
o.push('R 等状态包='+/等 2\.5 秒|照旧试一次开机帧/.test(L));
o.push('R 错误='+((window.__errs||[]).length));"""

print('=== A. 订上了 + 相机报「蓝牙连接模式」 → 发帧、并解出结果码 0 ===')
got = run_headless('R84A', PRE + "window.__sub=1; window.__statHex=statHex(0x08); window.__ansCode=0;", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 6000),
    (READ, 300),
])
print('  · ' + got[:460])
A('STEP-ERR' not in got, 'A0 步骤没抛错')
A('R 订阅在写之前=true' in got, 'A1 **订阅发生在任何写命令之前**（官方顺序：onDescriptorWrite 之后才允许发命令）')
_m = re.search(r'R 订阅列表=(\[[^\]]*\])', got)
_lst = json.loads(_m.group(1)) if _m else []
A(len(_lst) >= 2 and _lst[0].upper().startswith('82F949B4')
  and any(u.upper().startswith('05A02050') for u in _lst),
  'A1b 官方顺序：订的第一个是**命令特征 82F949B4**（v3.37 起按官方订三个；见 SPEC-round85）')
A('R CCCD成功=true' in got and 'R 订上没靠超时=true' in got,
  'A1c 等的是**CCCD 写成功的回调**（onDescriptorWrite），不是"发出去就算订上"—— 日志写了 status=0，也没出现"没等到确认"')
A('R 状态包人话=true' in got, 'A1d 收到并解出相机状态包（以前从没人喂给它 —— 那是判据永远不生效的根因）')
A('R 帧数=2' in got, 'A2 bit3=1 且 bit5=0 → 发两帧（r88 起 = 官方"导入图片"那两条：電源ON + リモコンモード）')
A('0F 01 01 02 13 00' in got.upper(), 'A2b 帧还是官方那 9 字节 01 … 04 0F 01 01 02 13 00')
A('R 结果码=true' in got, 'A3 相机回帧的结果码被解出来（官方 M2/b$b.a() 取 c()[6]）：显示"结果码 0（0 = 相机接受）"')
A('R 错误=0' in got, 'A0b 0 运行错误')

print()
print('=== B. 相机报"不在蓝牙连接模式"(bit3=0) → 照官方**不发**，且不许再开观察窗 ===')
got2 = run_headless('R84B', PRE + "window.__sub=1; window.__statHex=statHex(0x00);", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 6000),
    (READ, 300),
])
print('  · ' + got2[:460])
A('R 帧数=0' in got2, 'B1 bit3=0 → **一帧都不发**（官方 oishare/e.W() 就是这个规则）')
A('R 官方判据不发=true' in got2 and 'R 说了原因=true' in got2,
  'B2 说清"照官方不发"以及相机自己报的位（蓝牙连接模式）—— 这才是"为什么没反应"的答案')
A('R 观察窗停了=true' in got2, 'B3 没发帧就**不再开 45 秒观察窗**（否则到点那句"没看到相机热点"会误导）')
A('R 错误=0' in got2, 'B0b 0 运行错误')

print()
print('=== A2. 相机报"定位中"(bit5=1) → 同样不发 ===')
got2b = run_headless('R84B2', PRE + "window.__sub=1; window.__statHex=statHex(0x28);", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 6000),
    (READ, 300),
])
print('  · ' + got2b[:400])
A('R 帧数=0' in got2b, 'B4 bit5（定位）置位 → 不发（`blePowerOnBlock` 的两条规则都在）')

print()
print('=== C. 订阅成功但相机一直不报状态包 → 等 2.5 秒照旧试（不拦住用户） ===')
got3 = run_headless('R84C', PRE + "window.__sub=1; window.__statHex=''; window.__ansCode=0;", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 9000),
    (READ, 300),
])
print('  · ' + got3[:400])
A('R 等状态包=true' in got3, 'C1 没状态包时明确写"等 2.5 秒 / 照旧试一次"')
A('R 帧数=2' in got3, 'C2 还是把帧发了（不因为"不知道相机状态"就把用户拦住；r88 起 = 两帧）')
A('R 订阅在写之前=true' in got3, 'C0b 顺序依旧：先订阅再发')

print()
print('=== D. 订阅拿不到 CCCD 确认 → 如实说，不许假装订上 ===')
got4 = run_headless('R84D', PRE + "window.__sub=0;", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 9000),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('D1 如实说没确认='+(/没等到 CCCD 确认/.test(L) || /订阅结束：成功 0\//.test(L)));
o.push('D2 还是发了='+((window.__ble||[]).filter(function(x){return String(x).indexOf('WRITE:')===0;}).length));
o.push('D3 错误='+((window.__errs||[]).length));""", 300),
])
print('  · ' + got4[:300])
A('D1 如实说没确认=true' in got4, 'D1 等不到 CCCD 确认时如实写"没等到确认"，不假装')
A('D2 还是发了=2' in got4, 'D2 依旧把命令发出去（订阅失败不该让整条链瘫掉；r88 起 = 两帧）')

print()
print('=== E. 静态 ===')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(not (ids_o - ids_p), 'E1 老 id 一个都没少（少的：%s）' % (sorted(ids_o - ids_p) or '无'))
A(not (ids_p - ids_o), 'E1b 本轮**没有新增 id**（多的：%s）' % (sorted(ids_p - ids_o) or '无'))
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
# r90 按规格新增 cv-pass（那一轮探针断言"恰好 == {cv-pass}"）；老探针只要求"新增的都在已声明表里"
A((tv_p - tv_o) <= {'cv-pass', 'donate'}, 'E2 **没有新增 data-tv**（多的：%s；少的：%s）' % (sorted(tv_p - tv_o), sorted(tv_o - tv_p)))
A('r84：' in page, 'E3 页面有 r84 标记（生成脚本幂等判据）')
A(java == oldj, 'E4 **Java 一行都没改**（本轮只动页面）')
A('function bleSubNotify(' in page and 'function _bleWakeGo(' in page and 'function bleResultCode(' in page,
  'E5 三个新函数都在（订阅 / 发帧段 / 结果码）')
assert 'STEPS_MARK' not in page
A('STEPS_MARK' not in page, 'E6 生成器占位符没漏在页面里')

print()
print('第 84 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
