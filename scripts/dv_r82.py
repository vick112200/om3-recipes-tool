# -*- coding: utf-8 -*-
"""第 82 轮验收：真机日志（2026-09-28 23:59）暴露的两个问题都修掉了

真机：①只连只发帧都对；但 ② 之后 20 秒"没看到相机热点"→ 假失败；
      同时 bleAutoWake 自己喊"没能把相机唤醒"+让填口令（与观察窗打架，人又点了一次②被挡）。

A. **无头行为**（假桥）
   A1 原生"等新结果"的扫描返回 fresh=true 且里面有相机 → 观察窗成功、日志写"新扫了一次 … 像相机的 1 个"
   A2 fresh=false（安卓限流）→ 日志如实写"系统没给新结果…**不代表**相机没开"，**不许**说"相机没开"
   A3 ②流程里**没有**"没能把相机唤醒"（不抢结论），有"继续等热点"
   A4 没连蓝牙时点② → 观察窗**从发帧那刻**才计时（日志有"观察窗从现在开始计时"）
   A5 观察窗进行中再点② → **重发**（`bleWrite` 多一条），不再只提示"已经在跑"
   A6 ③ 有记住的相机 → **不扫描**（不调 wifiScanList）、直接 connectCamera2（钉 BSSID）
   A7 喂蓝牙 lost(status=8) → 日志含"连接超时"
B. **静态 + Java**
   B1 Java：`wifiScanWaitAsync` / `wifiScanWaitJson` / 共用 `scanListJson` 都在；老 `wifiScanList()` 只多一行
   B2 `javac --release 8` 编得过
   B3 页面：观察窗 45 秒、两个探测点、`fresh:false` 不当"没开"、③ 先走记住的凭据
   B4 老 id 一个不少；**无新增 id / data-tv**；r82 标记在

跑法：python scripts/dv_r82.py
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
PAGE = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r82.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLDJ = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.before_r82.java')
AJ = r'C:\Users\82302\AppData\Local\Temp\sdk\android-34\android.jar'
JDK = r'C:\Program Files\Java\jdk-20'
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()
oldj = io.open(OLDJ, encoding='utf-8').read()


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


# 假桥：可以切换 wifiScanWaitAsync 的返回（fresh / 无新结果 / 扫到相机）
BRIDGE = r'''
window.__ble = [];       /* 会动相机/蓝牙的调用 */
window.__calls = [];     /* 其它原生调用（Wi-Fi 连接/扫描/断开…） */
window.__fakeEmit = 0;   /* =1：scan 启动后立刻模拟"扫到相机 → 连上 → 服务发现完" */
window.__scanFresh = 1;  /* wifiScanWaitAsync 回 fresh 还是"没等到新结果" */
window.__scanHasCam = 1;  /* "等新结果"的扫描里有没有相机热点 */
window.__scanListCam = 0; /* 缓存扫描（wifiScanList）里有没有相机热点 —— 默认和真机一样：缓存里没有 */
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
    /* r82 新增：等新结果的扫描（异步） */
    wifiScanWaitAsync: function(ms){
      window.__calls.push('wifiScanWaitAsync');
      setTimeout(function(){
        try{
          window.__om3wifiScan('w1', JSON.stringify({
            fresh: !!window.__scanFresh, ms: ms,
            list: window.__scanHasCam ? JSON.parse(CAM) : JSON.parse(HOST) }));
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
    blePerm: function(){ return 'ok'; },
    blePermDetail: function(){ return '{}'; },
    bleDevices: function(){ return '[]'; },
    bleServices: function(){ return '[]'; },
    bleMtuInfo: function(){ return '{}'; },
    bleOsConn: function(){ return '{"conn":[],"paired":[]}'; },
    camGet: function(){ return '{"status":0,"text":""}'; },
    camGetAsync: function(){ return 'id1'; },
    camPost: function(){ return '{}'; },
    camPostAsync: function(){ return 'id2'; },
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
    hp = os.path.join(TMP, 'dv_r82_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o82_' + tag)
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


PRE = ("localStorage.setItem('om3cam', JSON.stringify({ssid:'OM-3-P-X',pass:'p',model:'OM-3',bssid:'AA:BB:CC:DD:EE:FF'}));" + BRIDGE)

print('=== A. 无头行为 ===')
got = run_headless('R82A', PRE, [
    ("g('tabCam').click();", 1500),
    (r"""window.__ble=[]; window.__calls=[]; window.__fakeEmit=1; cv('cv-ble').click();""", 1500),
    (r"""window.__ble=[]; window.__calls=[]; cv('cv-wake').click();""", 12000),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('A1 新扫过='+/新扫了一次/.test(L));
o.push('A1b 观察窗成功='+/相机 Wi-Fi 起来了/.test(L));
o.push('A2 新结果里有相机='+/新扫了一次：\d+ 个热点，像相机的 1 个/.test(L));
o.push('A3 没抢结论='+(!/没能把相机唤醒/.test(L) || /相机回过帧了/.test(L)));   /* r88：回过帧就不说"没能唤醒" */
o.push('A4 计时从发帧起='+/观察窗从现在开始计时/.test(L));
o.push('A5 蓝牙调用='+JSON.stringify(window.__ble||[]));
o.push('A6 状态框='+cvt('cvstate').replace(/\n/g,' | ').slice(0,150));
o.push('A7 错误='+(window.__errs?window.__errs.length:0));""", 300),
], )
for seg in got.split(' ;; '):
    print('  · ' + seg[:260])
A('STEP-ERR' not in got, 'A0 步骤没抛错')
A('A1 新扫过=true' in got, 'A1 观察窗真的做了"等新结果"的扫描（日志"新扫了一次…"）')
A('A1b 观察窗成功=true' in got, 'A1b 新结果里有相机 → 观察窗报成功（并点亮③）')
A('A2 新结果里有相机=true' in got,
  'A2 日志把"新扫了一次、像相机的 1 个"写出来了（**缓存里没有、新扫才有** —— 真机正是这个场景）')
A('A3 没抢结论=true' in got, 'A3 ②流程里**没有**"没能把相机唤醒"（结论只由观察窗下；r88 起回过帧就照实说）')
A('A4 计时从发帧起=true' in got, 'A4 观察窗**从真正发帧那刻**开始计时（没连蓝牙时不空跑）')
A('bleWrite' in got, 'A5 ②仍然真发帧（bleWrite）')
A('A7 错误=0' in got, 'A0b 0 运行错误')

print()
print('=== A2. fresh=false（安卓限流）→ 不许当"相机没开" + ②重发 + ③不扫描 + lost 码 ===')
got2 = run_headless('R82B', ("localStorage.setItem('om3cam', JSON.stringify({ssid:'OM-3-P-X',pass:'p',model:'OM-3',bssid:'AA:BB:CC:DD:EE:FF'}));"
                             + BRIDGE
                             # ⚠ 开关必须写在 BRIDGE **之后**（BRIDGE 自己会赋默认值，先写会被覆盖）
                             + "window.__scanFresh=0;"), [
    ("g('tabCam').click();", 1500),
    (r"""window.__ble=[]; window.__calls=[]; window.__fakeEmit=1; cv('cv-wake').click();""", 13000),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('B1 如实说限流='+/没拿到新结果|没给新结果|没等到系统给新结果/.test(L));
o.push('B2 不说没开='+/不代表\*\*相机没开|这不等于相机没开/.test(L));
o.push('B3 重发前的帧数='+(window.__ble||[]).filter(function(x){return x==='bleWrite';}).length);
cv('cv-wake').click();""", 12000),
    (r"""o.push('B4 重发后的帧数='+(window.__ble||[]).filter(function(x){return x==='bleWrite';}).length);
window.__calls=[]; window.__ble=[];
cv('cv-wifi').click();""", 12000),
    (r"""o.push('B5 ③等新结果的扫描次数='+((window.__calls||[]).filter(function(x){return x==='wifiScanWaitAsync';})).length);
o.push('B5b ③直连调用='+JSON.stringify((window.__calls||[]).filter(function(x){return /connectCamera/.test(x);})));
o.push('B6 蓝牙调用='+JSON.stringify(window.__ble||[]));
window.__om3ble('lost','连接断开（status=8）','8');
var L2=(window.__om3logText?window.__om3logText():'');
o.push('B7 lost码人话='+/8 = 连接超时/.test(L2));
o.push('B8 错误='+(window.__errs?window.__errs.length:0));
o.push('B9 日志尾='+L2.slice(-1500).replace(/\n/g,' / '));
o.push('B10 __scanFresh='+window.__scanFresh+' 有探测句='+/等新结果/.test(L2)+' 有窗口开始='+/观察窗开始/.test(L2));""", 300),
])
for seg in got2.split(' ;; '):
    print('  · ' + seg[:260])
A('STEP-ERR' not in got2, 'B0 步骤没抛错')
A('B1 如实说限流=true' in got2,
  'B1 拿不到新结果时**如实说**（r83 起措辞更准：「没拿到新结果：<为什么>」，同一件事）')
A('B2 不说没开=true' in got2, 'B2 明确写上"**不代表**相机没开"（把"未知"和"否"分开）')
m1 = re.search(r'B3 重发前的帧数=(\d+)', got2)
m2 = re.search(r'B4 重发后的帧数=(\d+)', got2)
A(bool(m1) and bool(m2) and int(m2.group(1)) > int(m1.group(1)),
  'B3 观察窗进行中再点② = **重发**（帧数 %s → %s；真机日志里用户正是想重试，却被挡住）'
  % (m1.group(1) if m1 else '?', m2.group(1) if m2 else '?'))
A('B5 ③等新结果的扫描次数=0' in got2, 'B4 ③ 记住过这台 → **一次“等新结果”的扫描都不做**（不依赖扫描，直接按记住的凭据连）')
A('connectCamera2' in got2, 'B4b ③ 直接按 SSID+BSSID 请系统连（connectCamera2）')
A('B6 蓝牙调用=[]' in got2, 'B4c ③ 不碰蓝牙')
A('B7 lost码人话=true' in got2, 'B5 蓝牙断开 status=8 在日志里有人话（"连接超时"）')
A('B8 错误=0' in got2, 'B0b 0 运行错误')

print()
print('=== A3. 一直没看到（也没新结果）→ 45 秒到点必须给出"能走的路"，且不许把"未知"说成"没开" ===')
got3 = run_headless('R82C', ("localStorage.setItem('om3cam', JSON.stringify({ssid:'OM-3-P-X',pass:'p',model:'OM-3',bssid:'AA:BB:CC:DD:EE:FF'}));"
                             + BRIDGE
                             + "window.__scanFresh=0; window.__scanHasCam=0;"), [
    ("g('tabCam').click();", 1500),
    (r"""window.__fakeEmit=1; cv('cv-wake').click();""", 8000),
    (r"""o.push('C1 发帧了='+/0F 01 01 02/.test(window.__om3logText?window.__om3logText():''));""", 40000),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('C2 到点说没看到='+/没看到相机热点/.test(L));
o.push('C3 不说没开='+/这不等于相机没开/.test(L));
o.push('C4 指路③='+/点③「连接相机 Wi-Fi」/.test(L));
o.push('C5 说了限流='+/没拿到新结果/.test(L));
o.push('C6 状态框仍未开='+/未知 \/ 还没开/.test(cvt('cvstate').replace(/\n/g,' ')));
o.push('C7 错误='+(window.__errs?window.__errs.length:0));
o.push('C9 日志尾='+L.slice(-560).replace(/\n/g,' / '));""", 300),
], budget=70000)
for seg in got3.split(' ;; '):
    print('  · ' + seg[:260])
A('STEP-ERR' not in got3, 'C0 步骤没抛错')
A('C1 发帧了=true' in got3, 'C0b 先真发了帧（前置）')
A('C2 到点说没看到=true' in got3 and 'C3 不说没开=true' in got3,
  'C1 到点说"没看到相机热点"**并且**写明"这不等于相机没开"（把"未知"和"否"分开 —— 真机教训）')
A('C4 指路③=true' in got3, 'C1b 给出能走的路：**点③（用记住的 SSID+BSSID，不依赖扫描）**')
A('C5 说了限流=true' in got3, 'C1c 如实说"没拿到新结果"（并说清为什么 —— r83 加了 why），不装作看到')
A('C6 状态框仍未开=true' in got3, 'C1d 状态框如实保持"未知 / 还没开"（不谎报成功）')
A('C7 错误=0' in got3, 'C0c 0 运行错误')

print()
print('=== C. 静态 + Java ===')
A(java.count('public String wifiScanWaitAsync(final int timeoutMs)') == 1
  and java.count('private String wifiScanWaitJson(int timeoutMs)') == 1
  and java.count('private String scanListJson(WifiManager wm)') == 1,
  'C1 Java 新增/共用的三个方法各 1 处（不复制实现）')
A(java.count('public String wifiScanList()') == 1 and 'return scanListJson(wm);' in java,
  'C1b 老 wifiScanList() 只把"拼 JSON"换成调用共用方法（签名/行为不变）')
A('ScanResultsAvailable_Action'.lower() not in java.lower() and 'SCAN_RESULTS_AVAILABLE_ACTION' in java,
  'C1c 用系统广播 SCAN_RESULTS_AVAILABLE_ACTION 等新结果')
jc = os.path.join(JDK, 'bin', 'javac.exe')
if not os.path.exists(jc):
    jc = 'javac'
outd = os.path.join(tempfile.gettempdir(), '_dv_r82_cls')
try:
    shutil.rmtree(outd, ignore_errors=True)
    os.makedirs(outd)
    env = dict(os.environ)
    env['JAVA_HOME'] = JDK
    env['PATH'] = os.path.join(JDK, 'bin') + os.pathsep + env.get('PATH', '')
    r = subprocess.run([jc, '--release', '8', '-nowarn', '-encoding', 'UTF-8', '-cp', AJ,
                        '-d', outd, JAVA], capture_output=True, text=True, encoding='utf-8',
                       errors='ignore', timeout=240, env=env)
    A(r.returncode == 0, 'C2 javac --release 8 编得过（%s）'
      % ('无输出' if not (r.stdout or r.stderr).strip() else (r.stderr or r.stdout).strip()[:100]))
except subprocess.TimeoutExpired:
    A(False, 'C2 javac 超时')
except FileNotFoundError:
    A(True, 'C2 （没找到 javac，跳过 —— 构建时还会编一次）')
mj = re.search(r'var CAM_CV_WAKE_MS = (\d+);', page)
A(bool(mj) and int(mj.group(1)) >= 45000, 'C3 观察窗 ≥45 秒（实测 %s）' % (mj.group(1) if mj else '?'))
A('CV_PROBE_AT = [6000, 28000]' in page and 'camProbeFresh(CV_PROBE_MS' in page,
  'C3b 两个探测点各做一次"等新结果"的扫描（异步，≤6 秒）')
A('window.__om3wifiScan = function' in page and '_cvProbeBusy' in page,
  'C3c 结果由 __om3wifiScan 推回；在飞的只允许一个')
A('if(sv0.ssid){' in page and '不依赖扫描' in page, 'C4 ③ 有记住的相机 → 先按 SSID+BSSID 直连（写明不依赖扫描）')
A('bleLostHint' in page and '8 = 连接超时' in page and '19 = 相机主动断开' in page, 'C5 断开码映射在')
A('r82：' in page and 'r82：' in java, 'C6 r82 标记在（生成脚本幂等判据）')
si, so = ids(page), ids(old)
A(not (so - si), 'C7 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'C8 本轮**没有新增 id**（多的：%s）' % (sorted(si - so) or '无'))
# ⚠ 只用 `<[^<>]*` —— 不能写成 `<[^>]*`：`[^>]` 会跨行跨语句（第 82 轮踩到：把 JS 里的
#   `'[data-tv="' + n + '"]'` 也当成 HTML 属性匹配了）
ptv = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
otv = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
# 口径修正（r83）：第 83 轮加了两个"人看到的"回答键（cv-seen / cv-notseen，写进 SPEC-round83 §4）。
# 所以本条从"一个都不许新增"改成"**老的一个都不许少**"；新增集合由**当轮**探针（dv_r83 D4）钉死。
A(not (otv - ptv), 'C9 **老 data-tv 一个都没少**（少的：%s；本轮之后新增的：%s）'
  % (sorted(otv - ptv) or '无', sorted(ptv - otv) or '无'))

print()
print('第 82 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
