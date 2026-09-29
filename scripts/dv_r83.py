# -*- coding: utf-8 -*-
"""第 83 轮验收：真机日志（**v3.34**，2026-09-29 00:19）暴露的问题

真机证明（第 82 轮的修复生效了）：观察窗 45 秒 + "从发帧那刻计时" 都在；
`相机没回应答（5 秒）…继续等热点` —— **不再抢结论**；`蓝牙断开 …（8 = 连接超时）` 有人话了。

本轮要修/要验的：
  1. `期间在第 28、NaN 秒`（CV_PROBE_AT 被 shift 吃掉）
  2. `"等新结果"的扫描没等到系统给新结果` —— 真机 2 秒内就返回 fresh=false（`startScan` 直接 false），
     要把**原因**（why）说清；发起扫描失败时**再试一次**
  3. 00:18:54 重发被"唤醒已经在跑了"挡掉 → 帧没发出去、窗口却白开 45 秒；之后每次点②都误报"正在连蓝牙（还没发帧）"
  4. "相机到底开没开"我方判不了 → 收尾明确"**连一次（③）才是判据**" + 两个回答键（相机屏幕亮了/没反应）进日志

跑法：python scripts/dv_r83.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r83.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLDJ = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.before_r83.java')
AJ = r'C:\Users\82302\AppData\Local\Temp\sdk\android-34\android.jar'
JDK = r'C:\Program Files\Java\jdk-20'
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
OK = []
FAIL = []


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()

BRIDGE = r'''
window.__ble = [];       /* 会动相机/蓝牙的调用 */
window.__calls = [];     /* 其它原生调用（Wi-Fi 连接/扫描/断开…） */
window.__fakeEmit = 0;   /* =1：扫描启动后立刻模拟"扫到相机 → 连上 → 服务发现完" */
window.__scanFresh = 1;  /* wifiScanWaitAsync 回 fresh 还是"没拿到新结果" */
window.__scanHasCam = 1; /* "等新结果"的扫描里有没有相机热点 */
window.__scanListCam = 0;/* 缓存扫描里有没有相机热点（真机就是"缓存里没有"） */
window.__scanWhy = 'startScan_false'; /* r83：没拿到新结果的原因（真机 v3.34 就是这种） */
window.OM3Native = (function(){
  var SVC = JSON.stringify([{uuid:'adc505f9-4e58-4b71-b8ca-983bb8c73e4f', type:0,
    chars:[{uuid:'82f949b4-f5dc-4cf3-ab3c-fd9fd4017b68', write:true, wnr:true, props:{write:true, wnr:true}}]}]);
  var HOST = JSON.stringify([{ssid:'lanhome', level:-40, cam:false, bssid:'44:DF:65:F6:5D:92'}]);
  var CAM  = JSON.stringify([{ssid:'OM-3-P-X', level:-44, cam:true, bssid:'AA:BB:CC:DD:EE:FF'}]);
  function ble(name){ return function(){
      window.__ble.push(name);
      if((name === 'bleScanStart2' || name === 'bleScanStart') && window.__fakeEmit){
        setTimeout(function(){
          try{
            window.__om3ble('found', 'BJSA21721', '34:90:EA:BE:07:F9', -70, 1);
            window.__om3ble('connected', '34:90:EA:BE:07:F9', '0');
            window.__om3ble('svc', SVC, '0');
          }catch(e){ window.__errs.push('FAKE-EMIT: ' + e.message); }
        }, 60);
      }
      if(name === 'bleWrite'){
        try{ window.__om3ble('wrote', '82f949b4-f5dc-4cf3-ab3c-fd9fd4017b68', 9, arguments[1]); }catch(e){}
      }
      return 'ok';
  }; }
  function plain(name){ return function(){ window.__calls.push(name); return 'ok'; }; }
  return {
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":36}'; },
    wifiState: function(){ return JSON.stringify({ssid:'', on:true}); },
    wifiScanList: function(){ window.__calls.push('wifiScanList'); return window.__scanListCam ? CAM : HOST; },
    wifiScanWaitAsync: function(ms){
      window.__calls.push('wifiScanWaitAsync');
      setTimeout(function(){
        try{
          window.__om3wifiScan('w1', JSON.stringify({
            fresh: !!window.__scanFresh, why: String(window.__scanWhy || ''),
            ms: ms, list: window.__scanHasCam ? JSON.parse(CAM) : JSON.parse(HOST) }));
        }catch(e){ window.__errs.push('FAKE-SCAN: ' + e.message); }
      }, 40);
      return 'w1';
    },
    /* r84 起的口径修正：自动链会**先订阅通知**再发命令，并且发帧前要等相机状态包；
       老探针的假桥原来没有 bleSubscribe → 会白等 2.5 秒（把时序全推后）。
       这里补一个"订阅成功 + 推一条 bit3(蓝牙连接模式)=1 的状态包"，让时序回到原来的样子。 */
    bleSubscribe: function(u){
      window.__calls.push('bleSubscribe');
      setTimeout(function(){
        try{
          window.__om3ble('cccd', String(u || ''), 0);
          window.__om3ble('notify', '05A02050-0860-4919-8ADD-9801FBA8B6ED',
                          '0A FF D0 04 01 00 00 08 00 00');
        }catch(e){ window.__errs.push('SUB: ' + e.message); }
      }, 40);
      return 'ok:subscribed';
    },
    cameraState: function(){ return '{"connected":false,"ssid":"","bssid":""}'; },
    bleState: function(){ return 'on'; },
    blePerm: function(){ return 'ok'; }, blePermDetail: function(){ return '{}'; },
    bleDevices: function(){ return '[]'; }, bleServices: function(){ return '[]'; },
    bleMtuInfo: function(){ return '{}'; }, bleOsConn: function(){ return '{"conn":[],"paired":[]}'; },
    camGet: function(){ return '{"status":0,"text":""}'; }, camGetAsync: function(){ return 'id1'; },
    camPost: function(){ return '{}'; }, camPostAsync: function(){ return 'id2'; },
    connectCamera: function(){ window.__calls.push('connectCamera'); return 'asking'; },
    connectCamera2: function(){ window.__calls.push('connectCamera2'); return 'asking@bssid'; },
    bleScan: ble('bleScan'), bleScanStart: ble('bleScanStart'), bleScanStart2: ble('bleScanStart2'),
    bleConnect: ble('bleConnect'), bleCmd: ble('bleCmd'), bleWrite: ble('bleWrite'),
    bleEnable: ble('bleEnable'), bleAskPerm: ble('bleAskPerm'),
    bleScanStop: plain('bleScanStop'), bleDisconnect: plain('bleDisconnect'),
    disconnectCamera: plain('disconnectCamera'), dropCamera: plain('dropCamera'),
    forgetWifi: plain('forgetWifi'), openWifiSettings: plain('openWifiSettings'),
    openAppSettings: plain('openAppSettings'), shareText: plain('shareText'),
    startWatch: plain('startWatch')
  };
})();
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
    hp = os.path.join(TMP, 'dv_r83_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o83_' + tag)
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


print('=== A. 真机那种"系统不让扫"（why=startScan_false）→ 必须说清原因、不许说"没开" ===')
got = run_headless('R83A', PRE + "window.__scanFresh=0; window.__scanHasCam=0; window.__scanWhy='startScan_false';", [
    ("g('tabCam').click();", 1500),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 52000),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('A1 说原因='+/系统不让 App 触发扫描/.test(L));
o.push('A2 说了没看到='+/没看到相机热点/.test(L));
o.push('A2b 不抢结论='+(!/没能把相机唤醒/.test(L)));
o.push('A3 指路③='+/连一次才是判据/.test(L));
o.push('A4 扫描='+((window.__calls||[]).filter(function(x){return x==='wifiScanWaitAsync';})).length);
o.push('A5 帧='+((window.__ble||[]).filter(function(x){return x==='bleWrite';})).length);
o.push('A6 错误='+((window.__errs||[]).length));""", 300),
])
print('  · ' + got[:400])
A('STEP-ERR' not in got, 'A0 步骤没抛错')
A('A1 说原因=true' in got, 'A1 没拿到新结果时说清**为什么**（真机 v3.34 只说"没等到系统给新结果"，判不出是哪一种）')
A('A2 说了没看到=true' in got and 'A2b 不抢结论=true' in got,
  'A2 到点说"没看到相机热点"，且**不出现**"没能把相机唤醒"（真机教训）')
A('A3 指路③=true' in got, 'A3 收尾明确"**连一次（③）才是判据**"')
A('A4 扫描=2' in got, 'A4 两个探测点各做一次"等新结果"的扫描')
A('A5 帧=2' in got, 'A5 ②真发帧（r88 起 = 官方的两条命令：電源ON + リモコンモード）')
A('A6 错误=0' in got, 'A0b 0 运行错误')

print()
print('=== A2. 手机 Wi-Fi 关着（why=wifi_off）→ 直接说人话 ===')
got2 = run_headless('R83B', PRE + "window.__scanFresh=0; window.__scanHasCam=0; window.__scanWhy='wifi_off';", [
    ("g('tabCam').click();", 1500),
    ("""window.__fakeEmit=1; cv('cv-wake').click();""", 52000),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('B1 说WiFi关='+/手机 Wi-Fi 开关是关的/.test(L));
o.push('B2 错误='+((window.__errs||[]).length));""", 300),
])
print('  · ' + got2[:260])
A('B1 说WiFi关=true' in got2, 'B1 `why=wifi_off` → 日志直说"手机的 Wi-Fi 开关是关的"')
A('B2 错误=0' in got2, 'B0b 0 运行错误')

print()
print('=== A3. 发不出帧→**不许**白开窗；第二次开窗不许 NaN；回答键进日志 ===')
got3 = run_headless('R83C', PRE + "window.__scanFresh=0; window.__scanHasCam=0; window.__scanWhy='startScan_false';", [
    ("g('tabCam').click();", 1500),
    ("window.wn = function(L){return L.split(String.fromCharCode(10)).filter(function(l){return /②备份 ② 观察窗开始/.test(l);}).length;}", 100),
    ("""window.__ble=[]; window.__fakeEmit=1; cv('cv-ble').click();""", 4000),           # ① 只连（等它连完）
    ("""cv('cv-wake').click();""", 800),                                                 # ② 发帧 → 窗 1（同步发帧）
    (r"""o.push('C2 窗1='+window.wn(window.__om3logText()));
o.push('C4 帧1='+((window.__ble||[]).filter(function(x){return x==='bleWrite';})).length);
cv('cv-wake').click();""", 800),                                                       # ② 再点（应答中）→ 不许重开
    (r"""o.push('C1 等应答='+/上一次发的那条还在等应答/.test(window.__om3logText()));
o.push('C3 窗2='+window.wn(window.__om3logText()));
o.push('C4b 帧2='+((window.__ble||[]).filter(function(x){return x==='bleWrite';})).length);""", 13000),  # 等应答跑完
    ("""cv('cv-wake').click();""", 900),                                                # 再点 ② → 才重发 + 窗 2
    (r"""var L=window.__om3logText();
o.push('C5 窗3='+window.wn(L));
o.push('C6 无NaN='+!/NaN/.test(L));
o.push('C7 有秒数='+/第 6、28 秒/.test(L));
o.push('C8 帧2='+((window.__ble||[]).filter(function(x){return x==='bleWrite';})).length);
cv('cv-seen').click(); cv('cv-notseen').click();
var L2=window.__om3logText();
o.push('C9 看到了='+/【②之后 · 人看到的】相机屏幕\*\*亮了/.test(L2));
o.push('C10 没反应='+/相机\*\*没反应\*\*/.test(L2));
o.push('C11 错误='+((window.__errs||[]).length));
o.push('C13 窗口行='+L.split(String.fromCharCode(10)).filter(function(l){return /观察窗开始/.test(l);}).map(function(l){return l.slice(0,26);}).join(' || '));
o.push('C12 日志尾='+L2.slice(-900).split(String.fromCharCode(10)).join(' / '));""", 300),
], budget=40000)
print('  · ' + got3[:520])
A('STEP-ERR' not in got3, 'C0 步骤没抛错')
A('C1 等应答=true' in got3 and 'C2 窗1=1' in got3 and 'C3 窗2=1' in got3,
  'C1 上次的帧还在等应答时再点② → 说清"等它跑完再点②"，**不重开观察窗**（真机 00:18:54 白等 45 秒）')
_m1 = re.search(r'C4 帧1=(\d+)', got3); _m2 = re.search(r'C4b 帧2=(\d+)', got3)
A(bool(_m1) and bool(_m2) and _m1.group(1) == _m2.group(1),
  'C1b 被挡的那次**一帧都没多发**（帧数 %s → %s；r88 起一次②=两条命令，但被挡时一条都不发）'
  % (_m1.group(1) if _m1 else '?', _m2.group(1) if _m2 else '?'))
_m3 = re.search(r'C8 帧2=(\d+)', got3)
A('C5 窗3=2' in got3 and bool(_m3) and bool(_m2) and int(_m3.group(1)) > int(_m2.group(1)),
  'C2 等应答跑完后再点② → 才真的再发（帧数 %s → %s）+ 重开窗'
  % (_m2.group(1) if _m2 else '?', _m3.group(1) if _m3 else '?'))
A('C6 无NaN=true' in got3 and 'C7 有秒数=true' in got3,
  'C3 第二次开窗写的是"第 6、28 秒"而**不是「NaN 秒」**（真机 00:18:52 抓到）')
A('C9 看到了=true' in got3, 'C4 回答键「屏幕亮了/进传输态」→ 日志写明"相机确实执行了开机帧"')
A('C10 没反应=true' in got3, 'C4b 回答键「相机没反应」→ 日志写明"相机没执行开机帧"')
A('C11 错误=0' in got3, 'C0b 0 运行错误')

print()
print('=== B. 静态 + 结构 ===')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(not (ids_o - ids_p), 'B1 老 id 一个都没少（少的：%s）' % (sorted(ids_o - ids_p) or '无'))
A(not (ids_p - ids_o), 'B1b 本轮**没有新增 id**（多的：%s）' % (sorted(ids_p - ids_o) or '无'))
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
DECLARED = {'cv-seen', 'cv-notseen'}   # ← 本轮规格 §4 那张表（新增 data-tv **完全等于**它）
A(not (tv_o - tv_p), 'B2 老 data-tv 一个都没少（少的：%s）' % (sorted(tv_o - tv_p) or '无'))
# r90 按规格新增 cv-pass（那一轮探针断言"恰好 == {cv-pass}"）；本轮只要求"老的一个不少、新增的都在已声明表里"
A((tv_o - tv_p) == set() and all(x in (set(DECLARED) | {'cv-pass', 'donate'}) for x in (tv_p - tv_o)),
  'B2b 新增 data-tv 都在已声明表里（多的：%s；少的：%s）'
  % (sorted((tv_p - tv_o) - set(DECLARED) - {'cv-pass', 'donate'}), sorted(tv_o - tv_p)))
for n in sorted(DECLARED):
    A(('data-tv="%s"' % n) in page, 'B2c 规格里写的 `%s` 真在页面里' % n)
A('r83：' in page, 'B3 页面有 r83 标记（生成脚本幂等判据）')
A('r83：' in java, 'B3b Java 有 r83 标记')
A('r82：：' not in page, 'B3c 顺手把上一轮遗留的「r82：：」双冒号清掉了')
A('CV_PROBE_AT.slice()' in page, 'B4 探测点数组是**复制**的（NaN 根因）')
A('cvScanWhyText' in page, 'B4b why → 人话的翻译函数在')
A('_bleWakeRunning){ camCvSay' in page, 'B4c 发帧前先看有没有在等应答')
nocmt = re.sub(r'/\*.*?\*/', '', page, flags=re.S)
A(not re.search(r'function\s+camCvWifi\s*\([^)]*\)\s*\{[^}]*camBleAuto\(', nocmt),
  'B5 ③ 仍然不碰蓝牙（自动路径不许有蓝牙调用）')

print()
print('=== C. Java ===')
A(java.count('public String wifiScanWaitAsync(final int timeoutMs)') == 1, 'C1 wifiScanWaitAsync 只有一份')
A(java.count('private boolean tryScan(WifiManager wm)') == 1, 'C1b tryScan 只有一份')
A(all(('"%s"' % w) in java for w in ('ok', 'startScan_false', 'no_broadcast', 'register_failed')),
  'C2 why 的四态都在（ok / startScan_false / no_broadcast / register_failed）')
A('Thread.sleep(1200)' in java, 'C3 startScan 返回 false 时隔 1.2 秒**再试一次**（真机原因多半是"系统里正有一次扫描"）')
A(java.count('public String wifiScanList()') == 1, 'C4 老 wifiScanList() 还在、只有一份')
jc = os.path.join(JDK, 'bin', 'javac.exe')
jc = jc if os.path.exists(jc) else 'javac'
try:
    r = subprocess.run([jc, '--release', '8', '-nowarn', '-cp', AJ,
                        '-d', os.path.join(ROOT, 'apk', 'build', 'jc83'), JAVA],
                       capture_output=True, timeout=180)
    A(r.returncode == 0, 'C5 javac --release 8 编得过（%s）'
      % ('' if r.returncode == 0 else r.stderr.decode('utf-8', 'replace')[:180]))
except Exception as e:      # noqa
    A(False, 'C5 javac 跑不起来：%s' % e)

print()
print('第 83 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
