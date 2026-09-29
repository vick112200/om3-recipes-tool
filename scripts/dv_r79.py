# -*- coding: utf-8 -*-
"""第 79 轮验收：入口按钮**点了必须真的有效果**（SPEC-round79.md）。

需求方 2026-09-28：「点了没啥反应」← 根因是 `#camGateScan` 第 74 轮"放回来"时**没接上功能**
（它的 click 只有 `showStep(1)`），而当年的探针只断言了"可见/排后/样式次要"。
本探针把这类漏洞堵上：**对入口按钮断言"点了真的会发生它该做的事"**。

A. **无头行为**（假原生桥，点真按钮、看真效果）
   A1 点「扫码连接」→ 真的去启动扫码（日志出现「扫码：正在打开摄像头」/「扫码：等待相机权限」
      /「扫码组件没加载成功」/「这个环境不给用摄像头」其一；或 `#scanMask` 浮层打开）
      —— **修前：只有 `showStep(1)`，什么都没有** ❗
   A2 点「连接相机」→ 日志出现「第 1/3 步」这类连接链的话（证明接到链上了）
   A3 点「手动填 SSID / 密码」→ 手动填卡 `#camManualCard` 变成可见
B. **静态**：三条路分支文案在（情况 A/B/C）+「不用先去改相机的 Wi-Fi 开关」这句在；
   老 id 一个不少；本轮不新增 id；`r79` 标记在；运行错误 0

跑法：python scripts/dv_r79.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r79.html')
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
window.__calls = [];
window.OM3Native = (function(){
  function rec(n){ return function(){ window.__calls.push(n); return '{"s":200,"t":"ok"}'; }; }
  return {
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
    wifiState: function(){ return JSON.stringify({ssid:'我家WiFi', on:true}); },
    wifiScanList: function(){ return JSON.stringify([{ssid:'OM-3-P-X', bssid:'AA:BB:CC:DD:EE:FF', level:-42, cam:true}]); },
    cameraState: function(){ return '{"connected":false,"ssid":"","bssid":""}'; },
    blePermDetail: function(){ return '{}'; }, startWatch: rec('startWatch'), ensureCamera: rec('ensureCamera'),
    camGet: rec('camGet'), camGetAsync: function(p){ window.__calls.push('camGetAsync'); return 'id1'; },
    camPost: rec('camPost'), camPostAsync: function(p,b){ window.__calls.push('camPostAsync'); return 'id2'; },
    bleScanStop: rec('bleScanStop'), bleDisconnect: rec('bleDisconnect'), dropCamera: rec('dropCamera'),
    forgetWifi: rec('forgetWifi'), openWifiSettings: rec('openWifiSettings'), openAppSettings: rec('openAppSettings'),
    shareText: rec('shareText'), disconnectCamera: rec('disconnectCamera'), bleScanStart: rec('bleScanStart'),
    bleConnect: rec('bleConnect'), bleCmd: rec('bleCmd'), bleWrite: rec('bleWrite'), bleAskPerm: rec('bleAskPerm')
  };
})();
/* 把 getUserMedia 记下来（无头里没有摄像头；记到就算"启动了扫码"） */
if(navigator.mediaDevices){
  var _gum = navigator.mediaDevices.getUserMedia;
  navigator.mediaDevices.getUserMedia = function(c){
    window.__gum = (window.__gum || 0) + 1;
    return Promise.reject(new Error('无头环境没有摄像头'));
  };
}
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
    hp = os.path.join(TMP, 'dv_r79_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o79_' + tag)
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


def log_tail(ms):
    return ("var L=(window.__om3logText?window.__om3logText():'');"
            "o.push('LOG=' + L.slice(-%d).replace(/\\n/g,' ⏎ '));" % ms)


print('=== A. 入口按钮点下去到底有没有干活（假桥）===')
got = run_headless('R79A', BRIDGE, [
    ("g('tabCam').click();", 800),
    ("o.push('A0 进到连接页=' + (getComputedStyle(g('paneD')).display !== 'none'));", 200),
    # ── 点「扫码连接」：修前这里**什么都不会发生**
    ("window.__gum = 0; g('camGateScan').click();", 1500),
    ("var L=(window.__om3logText?window.__om3logText():'');"
     "var scanSaid = /扫码：正在打开摄像头|扫码：等待相机权限|扫码组件没加载成功|这个环境不给用摄像头|扫码起不来/.test(L);"
     "var maskOn = false; try{ maskOn = !g('scanMask').classList.contains('hide'); }catch(e){}"
     "o.push('A1 扫码启动过=' + scanSaid + ' getUserMedia调了=' + (window.__gum||0) + ' 浮层开=' + maskOn);"
     "o.push('A1b 日志尾部=' + L.slice(-300).replace(/\\n/g,' ⏎ '));", 300),
])
for seg in got.split(' ;; '):
    print('  · ' + seg[:260])
A('A0 进到连接页=true' in got, 'A0 能进连接相机页（前置）')
m = re.search(r'A1 扫码启动过=(\w+) getUserMedia调了=(\d+) 浮层开=(\w+)', got)
A(bool(m) and (m.group(1) == 'true'), 'A1 点「扫码连接」**真的去启动了扫码**（日志里有扫码那套话）'
  + ('；实测：启动过=%s gum=%s 浮层=%s' % (m.groups() if m else ('?',) * 3)))

got2 = run_headless('R79B', BRIDGE, [
    ("g('tabCam').click();", 800),
    ("g('camGateConn').click();", 2500),
    ("var L=(window.__om3logText?window.__om3logText():'');"
     "o.push('A2 连接链跑过=' + /第 1\\/3 步|第 2\\/3 步/.test(L));", 200),
    ("g('tabCam').click();", 400),
    ("var c=g('camManualCard'); c.style.display='none';"
     "g('camGateManual').click();", 600),
    ("var c=g('camManualCard');"
     "o.push('A3 手动填卡可见=' + !!(c && (c.style.display !== 'none') && c.getBoundingClientRect().height > 0));"
     "o.push('A4 运行错误=' + (window.__errs?window.__errs.length:0));", 200),
])
for seg in got2.split(' ;; '):
    print('  · ' + seg[:260])
A('A2 连接链跑过=true' in got2, 'A2 点「连接相机」真的跑连接链（日志里有「第 1/3 步」）')
A('A3 手动填卡可见=true' in got2, 'A3 点「手动填 SSID / 密码」真的把手动填卡打开（可见）')
A('A4 运行错误=0' in got2, 'A4 三个入口点下来 0 运行错误')

print('=== B. 静态 ===')
A('先看相机屏幕上是什么，对号入座' in page, 'B1 第一步改成了"先看相机屏幕上是什么"')
A('情况 A：相机屏幕上有「二维码」' in page and '情况 B：相机屏幕上只有 SSID 和密码' in page
  and '情况 C：你已经自己在相机/手机设置里把相机 Wi-Fi 打开了' in page,
  'B2 三条路按相机屏幕分支写清了（A 有二维码 / B 只有 SSID 密码 / C 已自己开好）')
A('不用先去改相机的 Wi-Fi 开关' in page, 'B3 明确回答了"要不要自己开相机 Wi-Fi"（不用先改；App 也会自己唤醒）')
A("window.__om3startScan()" in page and 'window.__om3startScan = startScanNow' in page,
  'B4 「扫码连接」复用的是既有 __om3startScan（没复制第二份实现）')
A('r79：入口真的能点' in page, 'B5 r79 标记在（生成脚本幂等判据）')
si, so = ids(page), ids(old)
A(not (so - si), 'B6 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B7 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print()
print('第 79 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
