# -*- coding: utf-8 -*-
"""第 81 轮验收：**手动控制台**（状态可见 + 四个按钮；② 是唯一发「電源ON」帧的地方）

需求方 2026-09-28：「你可不能自动唤醒相机wifi啊…我们也要做成**显示蓝牙已连接**、并且
**点击按钮才能控制相机开启wifi**…因为相机开启wifi和手机连相机wifi并不应该是个随随便便的行为。」

A. **无头行为**（假原生桥，把"会动相机/蓝牙"的调用全记在 `window.__ble`）
   A0 状态框在**第一屏内完整可见**；②按钮在首屏
   A1 进「连接相机」页 → **一次蓝牙动作都没有**（第 80 轮建立的不变式，继续守）
   A2 点①「连接相机蓝牙」→ 有 bleScanStart/bleConnect、**没有 bleWrite**（不发帧），日志说"只连模式/没有发唤醒帧"，状态框出现"已连接"
   A3 点②「让相机开 Wi-Fi」→ **出现 bleWrite** 且帧是 `0F 01 01 02`（電源ON）；热点出现后状态框"相机 Wi-Fi…已开启"
   A4 点③「连接相机 Wi-Fi」→ 走既有 Wi-Fi 链；**蓝牙调用 []**（这一步不碰相机）
   A5 点④「断开全部」→ bleDisconnect + disconnectCamera；状态复位；A6 0 运行错误
B. **静态**：老 id 一个不少；本轮不新增 id；**新增 data-tv 完全等于** SPEC §4 那张表；
   `__om3camPaneShown` / `camWifiChain` 里没有 camBleAuto(/bleAutoWake(/bleWakeCamera(；
   camBleAuto 有 connectOnly 且 `__om3bleAutoWake = !_cvConnectOnly`；
   C. **纯函数**（node）：`camCvWakeVerdict()` 三态 + 热点优先

跑法：python scripts/dv_r81.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r81.html')
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


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


# 假原生桥：只有列在 __BLEDO 里的才算"会动相机/蓝牙"的动作
BRIDGE = r'''
window.__ble = [];      /* 会动相机/蓝牙的调用 */
window.__calls = [];    /* 其它原生调用（Wi-Fi 连接/断开…） */
window.__fakeEmit = 0;  /* =1 时：scan 启动后立刻模拟"扫到相机 → 连上 → 服务发现完" */
window.OM3Native = (function(){
  var SVC = JSON.stringify([{uuid:'adc505f9-4e58-4b71-b8ca-983bb8c73e4f', type:0,
    /* 页面里 bleWriteTarget() 读的是特征值对象上的 c.write / c.wnr（不是 c.props）→ 两个都给上 */
    chars:[{uuid:'82f949b4-f5dc-4cf3-ab3c-fd9fd4017b68', write:true, wnr:true, props:{write:true, wnr:true}},
           {uuid:'05a02050-1234-4b71-b8ca-983bb8c73e4f', notify:true, cccd:true, props:{notify:true, cccd:true}}]}]);
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
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
    wifiState: function(){ window.__calls.push('wifiState'); return JSON.stringify({ssid:'我家WiFi', on:true}); },
    wifiScanList: function(){ window.__calls.push('wifiScanList');
      return JSON.stringify([{ssid:'OM-3-P-X', bssid:'AA:BB:CC:DD:EE:FF', level:-42, cam:true},
                             {ssid:'我家WiFi', bssid:'11:22:33:44:55:66', level:-60, cam:false}]); },
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
    connectCamera2: function(a, b, c){ window.__calls.push('connectCamera2'); return 'asking@bssid'; },
    /* ↓↓ 会动相机/蓝牙的 */
    bleScan: ble('bleScan'), bleScanStart: ble('bleScanStart'), bleScanStart2: ble('bleScanStart2'),
    bleConnect: ble('bleConnect'), bleCmd: ble('bleCmd'), bleWrite: ble('bleWrite'),
    bleEnable: ble('bleEnable'), bleAskPerm: ble('bleAskPerm'),
    /* 只是"收尾/只读"的，不算动相机 */
    bleScanStop: plain('bleScanStop'), bleDisconnect: plain('bleDisconnect'),
    disconnectCamera: plain('disconnectCamera'), dropCamera: plain('dropCamera'),
    forgetWifi: plain('forgetWifi'), openWifiSettings: plain('openWifiSettings'),
    openAppSettings: plain('openAppSettings'), shareText: plain('shareText'),
    startWatch: plain('startWatch')
  };
})();
'''


def run_headless(tag, pre, steps, budget=60000):
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
    hp = os.path.join(TMP, 'dv_r81_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o81_' + tag)
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


PRE = ("localStorage.setItem('om3cam', JSON.stringify({ssid:'OM-3-P-X',pass:'p',model:'OM-3'}));"
       + BRIDGE)

STEPS = [
    ("g('tabCam').click();", 1600),
    (r"""var b=cv('cvstate'), r=b?b.getBoundingClientRect():{top:0,height:0};
var w=cv('cv-wake'), rw=w?w.getBoundingClientRect():{top:9999};
o.push('A0 状态框 y='+Math.round(r.top)+' h='+Math.round(r.height)+' 视口='+window.innerHeight
       + ' 完整可见='+(r.top>=0 && (r.top+r.height)<=window.innerHeight));
o.push('A0b ②按钮 y='+Math.round(rw.top)+' 视口='+window.innerHeight+' 在首屏='+(rw.top<window.innerHeight));
var L=(window.__om3logText?window.__om3logText():'');
o.push('A1 进页面蓝牙调用='+JSON.stringify(window.__ble||[]));
o.push('A1b 说了不做自动蓝牙='+/不做任何自动蓝牙动作/.test(L));""", 250),
    (r"""window.__ble=[]; window.__calls=[]; window.__fakeEmit=1;
cv('cv-ble').click();""", 1800),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('A2 ①点完蓝牙调用='+JSON.stringify(window.__ble||[]));
o.push('A2b ①没发帧='+((window.__ble||[]).indexOf('bleWrite')<0));
o.push('A2c 日志只连模式='+/只连模式/.test(L)+' 没有发唤醒帧='+/没有(\*\*)?发唤醒帧/.test(L));
o.push('A2d 状态框蓝牙已连接='+/已连接/.test(cvt('cvstate')));
o.push('A2e 状态框='+cvt('cvstate').replace(/\n/g,' | ').slice(0,150));
o.push('A2f 日志尾='+L.slice(-320).replace(/\n/g,' / '));""", 250),
    (r"""window.__ble=[]; cv('cv-wake').click();""", 3400),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('A3 ②点完蓝牙调用='+JSON.stringify(window.__ble||[]));
o.push('A3b ②发了電源ON帧='+/0F 01 01 02/.test(L));
o.push('A3c 说了按热点判成功='+/观察窗开始|等相机把 Wi-Fi 开起来|热点起来/.test(L));
o.push('A3d 状态框相机WiFi已开启='+/相机 Wi-Fi.*已开启/.test(cvt('cvstate').replace(/\n/g,' ')));
o.push('A3e 没把家里WiFi当相机='+(cvt('cvstate').indexOf('已开启（我家WiFi）')<0));
o.push('A3f 状态框='+cvt('cvstate').replace(/\n/g,' | ').slice(0,180));""", 250),
    (r"""window.__ble=[]; cv('cv-wifi').click();""", 3400),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('A4 ③点完蓝牙调用='+JSON.stringify(window.__ble||[]));
o.push('A4b ③走了Wi-Fi链='+/第 (1|2|3)\/3 步/.test(L));""", 250),
    (r"""window.__ble=[]; window.__calls=[]; cv('cv-off').click();""", 1000),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('A5 ④点完蓝牙调用='+JSON.stringify(window.__ble||[]));
o.push('A5b ④其它原生调用='+JSON.stringify(window.__calls||[]));
o.push('A5c ④日志说了断开全部='+/断开全部/.test(L));
o.push('A5d 状态复位='+/蓝牙.*未连接/.test(cvt('cvstate').replace(/\n/g,' ')));
o.push('A6 运行错误='+(window.__errs?window.__errs.length:0));""", 300),
]

print('=== A. 无头行为（假桥：状态 / 四个按钮各走各的）===')
got = run_headless('R81A', PRE, STEPS)
for seg in got.split(' ;; '):
    print('  · ' + seg[:260])

A('STEP-ERR' not in got, 'A0 步骤没抛错')
m = re.search(r'A0 状态框 y=(-?\d+) h=(\d+) 视口=(\d+) 完整可见=(\w+)', got)
A(bool(m) and m.group(4) == 'true',
  'A0 状态框在**第一屏内完整可见**（y=%s h=%s 视口=%s）—— "显示蓝牙已连接"必须一眼能看到'
  % (m.groups()[:3] if m else ('?',) * 3))
A('A0b ②按钮' in got and '在首屏=true' in got, 'A0b 「② 让相机开 Wi-Fi」按钮也在首屏（主控制就在手边）')
A('A1 进页面蓝牙调用=[]' in got, 'A1 进「连接相机」页**一次蓝牙动作都没有**（第 80 轮的不变式继续守住）')
A('A1b 说了不做自动蓝牙=true' in got, 'A1b 日志明说"不做任何自动蓝牙动作"（可追溯）')
m2 = re.search(r'A2 ①点完蓝牙调用=(\[[^\]]*\])', got)
A(bool(m2) and 'bleScanStart2' in m2.group(1) and 'bleConnect' in m2.group(1),
  'A2 点①**真的去连蓝牙了**（扫 + 连；实测 %s）' % (m2.group(1) if m2 else '?'))
A('A2b ①没发帧=true' in got, 'A2b ①**只连蓝牙、不发「電源ON」帧**（相机 Wi-Fi 不会因此打开）')
A('A2c 日志只连模式=true 没有发唤醒帧=true' in got,
  'A2c 日志说清了"只连模式 / 没有发唤醒帧"（用户能看出这一步没动相机）')
A('A2d 状态框蓝牙已连接=true' in got, 'A2d 状态框出现「蓝牙…已连接」（需求方点名要的显示）')
A('A3 ②点完蓝牙调用=' in got and 'bleWrite' in got.split('A3 ②点完蓝牙调用=')[1].split(' ;; ')[0],
  'A3 点②**才**发帧（出现 bleWrite）')
A('A3b ②发了電源ON帧=true' in got, 'A3b 发的正是「電源ON」帧（`0F 01 01 02`）—— 能控制相机开 Wi-Fi')
A('A3c 说了按热点判成功=true' in got,
  'A3c 说清了"怎么算成功"（第 82 轮起文案改成「观察窗开始 / 拿不到新结果不当"没开"」，同一件事）')
A('A3d 状态框相机WiFi已开启=true' in got, 'A3d 热点出现后状态框变「相机 Wi-Fi…已开启」')
A('A3e 没把家里WiFi当相机=true' in got,
  'A3e 状态框**没有**把"家里 Wi-Fi 的 SSID"当成相机热点名（此刻手机还挂在家里 Wi-Fi 上）')
A('A4 ③点完蓝牙调用=[]' in got, 'A4 点③**不碰蓝牙**（只连手机↔相机 Wi-Fi）')
A('A4b ③走了Wi-Fi链=true' in got, 'A4b ③接的是既有 Wi-Fi 链（没有复制第二份实现）')
A('A5 ④点完蓝牙调用=' in got and 'bleDisconnect' in got.split('A5b ④其它原生调用=')[1].split(' ;; ')[0],
  'A5 点④断了蓝牙（bleDisconnect）—— 断开类不算"动相机"，所以记在 __calls 里')
A('disconnectCamera' in got, 'A5b 点④也断了相机 Wi-Fi（复用 #camDisconnect 的处理器）')
A('A5d 状态复位=true' in got, 'A5c 断开后状态复位成「未连接」')
A('A6 运行错误=0' in got, 'A6 四个按钮点下来 0 运行错误')

print()
print('=== A2. 热点一直不出现 → 观察窗到点必须**明确给出下一步**（不是静默挂着）===')
# 口径修正（第 82 轮）：观察窗 20 秒 → 45 秒（真机证明"扫描永远慢一拍"+安卓限流，20 秒会假失败），
# 等的时间跟着加长；收尾文案第 82 轮也改成"没看到 ≠ 没开 + 直接点③"（同一件事，措辞更准）。
BRIDGE_NOCAM = BRIDGE.replace("ssid:'OM-3-P-X', bssid:'AA:BB:CC:DD:EE:FF', level:-42, cam:true",
                             "ssid:'邻居WiFi', bssid:'99:88:77:66:55:44', level:-70, cam:false")
gotB = run_headless('R81B', ("localStorage.setItem('om3cam', JSON.stringify({ssid:'OM-3-P-X',pass:'p',model:'OM-3'}));"
                             + BRIDGE_NOCAM), [
    ("g('tabCam').click();", 1500),
    (r"""window.__fakeEmit=1; cv('cv-wake').click();""", 50000),
    (r"""var L=(window.__om3logText?window.__om3logText():'');
o.push('B1 发了帧='+/0F 01 01 02/.test(L));
o.push('B2 明确说没看到='+/没看到相机热点/.test(L));
o.push('B3 说了下一步='+/确认相机开机/.test(L)+' 指路③='+/点③「连接相机 Wi-Fi」/.test(L));
o.push('B4 状态框仍未开='+/未知 \/ 还没开/.test(cvt('cvstate').replace(/\n/g,' ')));
o.push('B5 错误='+(window.__errs?window.__errs.length:0));""", 300),
], budget=90000)
for seg in gotB.split(' ;; '):
    print('  · ' + seg[:260])
A('STEP-ERR' not in gotB, 'B0 步骤没抛错')
A('B1 发了帧=true' in gotB, 'B0b 先发了唤醒帧（前置）')
A('B2 明确说没看到=true' in gotB, 'B0c 热点一直没看到 → 观察窗到点时**明确说出来**（不静默挂着）')
A('B3 说了下一步=true 指路③=true' in gotB, 'B0d 给下一步（看相机屏幕 / **直接点③（不依赖扫描）** / 再点一次② / 发日志）')
A('B4 状态框仍未开=true' in gotB, 'B0e 状态框如实保持"未知 / 还没开"（不谎报成功）')
A('B5 错误=0' in gotB, 'B0f 0 运行错误')

print()
print('=== C. 纯函数：camCvWakeVerdict（热点优先 / 到点算超时）===')
js = page[page.index('function camCvWakeVerdict('):page.index('function camCvRender(')]
harness = ('var out=[];\n' + js + '''
out.push(['hotspot', camCvWakeVerdict(true, 0, 20000)]);
out.push(['timeout', camCvWakeVerdict(false, 20000, 20000)]);
out.push(['waiting', camCvWakeVerdict(false, 19999, 20000)]);
out.push(['waiting0', camCvWakeVerdict(false, 0, 20000)]);
out.push(['priority', camCvWakeVerdict(true, 99999, 20000)]);
console.log(JSON.stringify(out));
''')
tmpjs = os.path.join(TMP, 'dv_r81_fn.js')
io.open(tmpjs, 'w', encoding='utf-8', newline='').write(harness)
try:
    rr = subprocess.run(['node', tmpjs], capture_output=True, text=True, encoding='utf-8', timeout=60)
except FileNotFoundError:
    rr = None
    print('  （没装 node，跳过功能部分）')
if rr is not None:
    if rr.returncode != 0:
        A(False, 'node 跑挂了：' + (rr.stderr or '')[-300:])
    else:
        rows = dict((x[0], x[1]) for x in json.loads(rr.stdout.strip().splitlines()[-1]))
        print('  ' + json.dumps(rows, ensure_ascii=False))
        A(rows.get('hotspot') == 'up', '看到热点 → 立刻算成功（up）')
        A(rows.get('timeout') == 'timeout', '等满上限 → 算超时（timeout，会明确说失败）')
        A(rows.get('waiting') == '', '还没到点、也没热点 → 继续等（空串）')
        A(rows.get('waiting0') == '', '刚开始等 → 继续等')
        A(rows.get('priority') == 'up', '热点优先于超时（热点来了就报成功）')

print()
print('=== B. 静态 ===')
A(page.count('r81：手动控制台') >= 3, 'B1 r81 标记在（生成脚本幂等判据；%d 处）' % page.count('r81：手动控制台'))
i_shown = page.index('window.__om3camPaneShown = function(){')
j_shown = page.index('};', i_shown)
blk_shown = page[i_shown:j_shown]
i_chain = page.index('function camWifiChain(')
j_chain = page.index('\n  window.__om3camWifiChain = camWifiChain;', i_chain)
blk_chain = page[i_chain:j_chain]


def nocmt(t):
    """去掉注释再查"有没有这句调用" —— 第 80 轮留的注释里会**提到** camBleAuto（说明为什么要删它），
    那不是调用；用整串查会假红（dv_r80 当年也踩过同一个坑，它改用精确串）。"""
    t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)
    return '\n'.join([ln for ln in t.split('\n') if not ln.strip().startswith('//')])


for nm, blk in (('进页面钩子', blk_shown), ('camWifiChain', blk_chain)):
    code = nocmt(blk)
    A('camBleAuto(' not in code, 'B2 %s 的**代码**里没有 camBleAuto(（不许自动连蓝牙）' % nm)
    A('bleAutoWake(' not in code, 'B2b %s 的代码里没有 bleAutoWake(（不许自动发唤醒帧）' % nm)
    A('bleWakeCamera(' not in code, 'B2c %s 的代码里没有 bleWakeCamera(' % nm)
A('function camBleAuto(why, isResume, opts){' in page, 'B3 camBleAuto 有第三个参数 opts（只连模式）')
A('var _cvConnectOnly = !!opts.connectOnly;' in page
  and 'window.__om3bleAutoWake = window.__om3cvWantWake ? true : !_cvConnectOnly;' in page,
  'B3b 只连模式真的把"发唤醒帧"关掉了（r89 起：`__om3bleAutoWake = __om3cvWantWake ? true : !_cvConnectOnly`'
  + ' —— 用户点过②时以②为准）')
A('（①只连模式）蓝牙连好了，**没有**发唤醒帧' in page, 'B3c 只连模式收口时会明说"没有发唤醒帧"')
A('if(!_bleWakeRunning && !_bleAutoRun){' in blk_chain, 'B4 ③ 不再白等：只有唤醒真的在跑才等热点')
# 口径修正（第 82 轮）：观察窗 20 秒 → 45 秒、探测方式从"第 8 秒强制一次缓存扫描"改成
# "两个时间点做等新结果的扫描"（真机证明强制读缓存永远慢一拍）。守的目的不变：**观察窗 + 纯函数判成败 + 不许高频扫描**。
A(re.search(r'var CAM_CV_WAKE_MS = \d+;', page) is not None
  and int(re.search(r'var CAM_CV_WAKE_MS = (\d+);', page).group(1)) >= 20000
  and 'camCvWakeVerdict(hs || !!_cvWakeHot, waited, CAM_CV_WAKE_MS)' in page,
  'B5 观察窗（≥20 秒）+ 用纯函数判成败')
A('CV_PROBE_AT' in page and 'camProbeFresh(' in page and 'wifiScanWaitAsync' in page
  and 'waited >= 8000' not in page,
  'B5b 观察窗改成"等新结果"的扫描（两个时间点、异步、每次 ≤6 秒）—— 不再用"读缓存"当判据')
A('_bleAutoStop = true' not in page[page.index('function camCvStopBle()'):page.index('function camCvBle()')],
  'B6 ④的收尾**没有**设 _bleAutoStop（否则之后①再也跑不起来）')
si, so = ids(page), ids(old)
A(not (so - si), 'B7 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B8 本轮**没有新增 id**（多的：%s）—— 新控件用 data-tv 选择器' % (sorted(si - so) or '无'))
# 只数**HTML 标签里**的 data-tv（JS 里 `'[data-tv="' + n + '"]'` 那种拼接不算）
page_tv = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
old_tv = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
declared = set(['cvstate', 'cv-ble', 'cv-wake', 'cv-wifi', 'cv-off'])
added = page_tv - old_tv
# 口径修正（r83）：第 83 轮又加了两个回答键（cv-seen / cv-notseen，见 SPEC-round83 §4），
# 所以这里从"完全等于 r81 那张表"改成"**r81 那几个一个都不少**"；新增集合由当轮探针钉死。
A(declared <= added, 'B9 r81 那批 data-tv 一个都没少（缺：%s；本轮之后新增的：%s）'
  % (sorted(added - declared) or '无', sorted(declared - added) or '无'))
A(all(('data-tv="%s"' % x) in page for x in ('cvstate', 'cv-ble', 'cv-wake', 'cv-wifi', 'cv-off')),
  'B9b 五个 data-tv 全都真的在页面里（不是只写在规格里）')

print()
print('第 81 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
