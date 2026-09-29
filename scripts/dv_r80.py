# -*- coding: utf-8 -*-
"""第 80 轮（上）验收：**不许再自动唤醒相机 Wi-Fi**（SPEC-round80-plan.md §2）。

需求方 2026-09-28：「你可不能自动唤醒相机wifi啊…相机开启wifi和手机连相机wifi并不应该是个随随便便的行为」
改前（真机日志可证）：进「连接相机」页就自动跑蓝牙链并发唤醒帧 → 相机自己开 Wi-Fi。

A. **无头行为**（假原生桥，把蓝牙调用全记下来）
   A1 进「连接相机」页 → **一次蓝牙动作都没有**（没有 bleScanStart / bleConnect / bleCmd / bleWrite）；
      日志里有"不做任何自动蓝牙动作"那句
   A2 点「连接相机」 → **仍没有**蓝牙动作；提示里出现"App 不会替你开相机 Wi-Fi"
   A3 手动点「用蓝牙唤醒相机」（`id="camLinkWake"`）→ **这时才**出现蓝牙动作（证明按钮那条路还在）
B. **静态**：`__om3camPaneShown` 里没有 `camBleAuto`；`camWifiChain` 里没有 `camBleAuto`；
   文案不再是"App 会先试蓝牙唤醒"；老 id 一个不少；本轮不新增 id；0 运行错误

跑法：python scripts/dv_r80.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r80.html')
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


BRIDGE = r'''
window.__ble = [];      /* 只记"会动相机/蓝牙"的调用 */
window.__all = [];
window.OM3Native = (function(){
  var BLEDO = {'bleScan':1,'bleScanStart':1,'bleConnect':1,'bleCmd':1,'bleWrite':1,'bleEnable':1,'bleAskPerm':1};
  function rec(n){ return function(){ window.__all.push(n); if(BLEDO[n]) window.__ble.push(n); return '{"s":200,"t":"ok"}'; }; }
  var API = {
    permState: function(){ window.__all.push('permState'); return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
    wifiState: function(){ window.__all.push('wifiState'); return JSON.stringify({ssid:'我家WiFi', on:true}); },
    wifiScanList: function(){ window.__all.push('wifiScanList'); return JSON.stringify([{ssid:'OM-3-P-X', bssid:'AA:BB:CC:DD:EE:FF', level:-42, cam:true}]); },
    cameraState: function(){ window.__all.push('cameraState'); return '{"connected":false,"ssid":"","bssid":""}'; },
    bleState: function(){ window.__all.push('bleState'); return 'on'; },
    blePerm: function(){ window.__all.push('blePerm'); return 'ok'; },
    blePermDetail: function(){ window.__all.push('blePermDetail'); return '{}'; },
    bleDevices: function(){ window.__all.push('bleDevices'); return '[]'; },
    bleServices: function(){ window.__all.push('bleServices'); return '[]'; },
    bleMtuInfo: function(){ window.__all.push('bleMtuInfo'); return '{}'; },
    camGet: function(){ window.__all.push('camGet'); return '{"s":200,"t":"ok"}'; },
    camGetAsync: function(){ window.__all.push('camGetAsync'); return 'id1'; },
    camPost: function(){ window.__all.push('camPost'); return '{}'; },
    camPostAsync: function(){ window.__all.push('camPostAsync'); return 'id2'; },
    /* ↓↓ 这些才是"会动相机/蓝牙"的 */
    bleScan: rec('bleScan'), bleScanStart: rec('bleScanStart'), bleConnect: rec('bleConnect'), bleCmd: rec('bleCmd'),
    bleWrite: rec('bleWrite'), bleEnable: rec('bleEnable'), bleAskPerm: rec('bleAskPerm'),
    ensureCamera: rec('ensureCamera'), startWatch: rec('startWatch'),
    bleScanStop: function(){ window.__all.push('bleScanStop'); return 'ok'; },
    bleDisconnect: function(){ window.__all.push('bleDisconnect'); return 'ok'; },
    dropCamera: rec('dropCamera'), forgetWifi: rec('forgetWifi'),
    openWifiSettings: rec('openWifiSettings'), openAppSettings: rec('openAppSettings'),
    shareText: rec('shareText'), disconnectCamera: rec('disconnectCamera')
  };
  return API;
})();
'''


def run_headless(tag, pre, steps, budget=40000):
    tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in steps], ensure_ascii=False) + ',si=0;\n'
            'function g(i){return document.getElementById(i);}\n'
            'function finish(){var d=document.createElement("div");d.id=\'' + tag + '\';'
            'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
            'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
            'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
            'setTimeout(next,1500);\n</script>')
    i0 = page.find('<body')
    j0 = page.find('>', i0) + 1
    out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
           'try{' + pre + '}catch(e){}</script>' + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r80_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o80_' + tag)
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



# 第二个桥：**扫不到像相机的热点**（用来看"App 不会替你开相机 Wi-Fi"那句提示）
BRIDGE2 = BRIDGE.replace("ssid:'OM-3-P-X', bssid:'AA:BB:CC:DD:EE:FF', level:-42, cam:true",
                         "ssid:'我家WiFi2', bssid:'11:22:33:44:55:66', level:-55, cam:false")

print('=== A. 进页面/点连接：不许有任何蓝牙动作 ===')
got = run_headless('R80A', BRIDGE, [
    ("g('tabCam').click();", 2500),
    ("var L=(window.__om3logText?window.__om3logText():'');"
     "o.push('A1 进页面时的蓝牙调用=' + JSON.stringify(window.__ble || []));"
     "o.push('A1b 说了不做自动蓝牙=' + /不做任何自动蓝牙动作/.test(L));", 300),
    ("window.__ble = []; g('camGateConn').click();", 3000),
    ("var L=(window.__om3logText?window.__om3logText():'');"
     "o.push('A2 点连接后的蓝牙调用=' + JSON.stringify(window.__ble || []));"
     "o.push('A2b 说了不会替你开=' + /App 不会替你开相机 Wi-Fi/.test(L));"
     "o.push('A3 运行错误=' + (window.__errs?window.__errs.length:0));", 300),
])
for seg in got.split(' ;; '):
    print('  · ' + seg[:250])
A('STEP-ERR' not in got, 'A0 步骤没抛错')
A("A1 进页面时的蓝牙调用=[]" in got,
  'A1 进「连接相机」页**一次蓝牙动作都没有**（不扫/不连/不发帧）—— 改前会自动跑整条链')
A('A1b 说了不做自动蓝牙=true' in got, 'A1b 而且日志里明说了"不做任何自动蓝牙动作"（可追溯）')
A("A2 点连接后的蓝牙调用=[]" in got,
  'A2 点「连接相机」**也不自动跑蓝牙链**（不会替用户把相机 Wi-Fi 打开）')
# A2b 要换场景：上面的假桥里"像相机的热点"是有的（camHotspotVisible=true），
# 那条提示**本来就不该出现**；要验它就换成"扫不到相机热点"的桥。
got2b = run_headless('R80C', BRIDGE2, [
    ("g('tabCam').click();", 1500),
    ("g('camGateConn').click();", 3000),
    ("var L=(window.__om3logText?window.__om3logText():'');"
     "o.push('A2b 说了不会替你开=' + /App 不会替你开相机 Wi-Fi/.test(L));"
     "o.push('A2c 蓝牙调用=' + JSON.stringify(window.__ble || []));"
     "var go=(g('camGateOut')||{}).innerText||'';o.push('A2d 提示框原文=' + go.slice(0,160));", 200),
])
for seg in got2b.split(' ;; '):
    print('  · ' + seg[:250])
A('A2b 说了不会替你开=true' in got2b,
  'A2b 扫不到相机 Wi-Fi 时，提示里写清「App 不会替你开相机 Wi-Fi」+ 指了两条路')
A('A3 运行错误=0' in got, 'A3 全程 0 运行错误')

print('=== A3. 手动按钮那条路还在（点了才动）===')
got2 = run_headless('R80B', BRIDGE, [
    ("g('tabCam').click();", 1200),
    ("window.__ble = [];"
     "var b=g('bleScan') || g('camLinkWake') || g('bleWake');"
     "o.push('A3a 手动蓝牙按钮在=' + !!b + ' id=' + (b?b.id:'无'));"
     "if(b){ try{ b.click(); }catch(e){ o.push('A3a2 点它出错:'+e.message); } }", 2500),
    ("o.push('A3b 手动点后的蓝牙调用=' + JSON.stringify((window.__ble||[]).slice(0,4)));", 200),
])
for seg in got2.split(' ;; '):
    print('  · ' + seg[:250])
A('A3a 手动蓝牙按钮在=true' in got2, 'A3a 手动蓝牙入口还在（「扫描蓝牙设备」/「用蓝牙唤醒相机」没被一起删掉）')
A(re.search(r"A3b 手动点后的蓝牙调用=\[[^]]+\]", got2) is not None,
  'A3b **点它才会**出现蓝牙动作（用户明确点头才动相机）')

print('=== B. 静态 ===')
i_shown = page.index('window.__om3camPaneShown = function(){')
j_shown = page.index('};', i_shown)
A('camBleAuto' not in page[i_shown:j_shown], 'B1 `__om3camPaneShown` 里没有 camBleAuto 了')
i_chain = page.index('function camWifiChain()')
_win = page[i_chain:i_chain + 4000]          # 固定窗口，够覆盖这个函数体
# 精确断言"那句自动调用没了"（我自己的注释里提到 camBleAuto 不算，所以不能用"整词不在窗口里"）
A("try{ camBleAuto('点「连接相机」'); }" not in page,
  'B2 `camWifiChain()` 里那句自动调用（扫→连→发唤醒帧）已经删掉')
A('App 不会替你开相机 Wi-Fi' in _win, 'B2b 换成了明确提示（窗口内能找到那句）')
A('App 不会替你开相机 Wi-Fi' in page and 'App 会先试「蓝牙唤醒相机」把它叫醒' not in page,
  'B3 文案改成如实说明（不再宣称"App 会先试蓝牙唤醒"）')
A('r80：不自动开相机 Wi-Fi' in page and page.count('r80：不自动开相机 Wi-Fi') >= 2,
  'B4 r80 标记在（两处：页面钩子 + 连接链）')
si, so = ids(page), ids(old)
A(not (so - si), 'B5 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B6 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print()
print('第 80 轮（上）探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
