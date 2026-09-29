# -*- coding: utf-8 -*-
"""第 74 轮验收：扫码"放回来但往后放" + 不白等 10 秒 + 热点探测节流 + 日志带头（SPEC-round74.md）。

A. **无头实测**
   A1 三个扫码入口都**可见**（第 49 轮被 .hid49 藏了 → display:none）
   A2 扫码**排在「连接相机」之后**（"往后放"），且是次要样式（.gho）
   A3 蓝牙这条路跑不起来时**不再白等 10 秒**：假原生桥里**故意不给 ble\*** 接口，
      用"页面提示文字的时间线"量「第 1/3 步」→「第 2/3 步」的间隔（修前 ~10000ms，修后应 < 2500ms）
   A4 相机热点一直没起来、蓝牙可用时：**真扫 Wi-Fi 被节流**（10 秒里 ≤6 次，修前 ~20 次），
      并且日志里出现"节流 5 秒"那条提示
   A5 日志头齐全 + **日志里绝不出现相机密码**（故意存一份带密码的记录再取日志）
B. **静态**：.hid49 的 CSS 还在（当开关）但**没有任何按钮**带它；blePossible 判据在；
   节流常量 5000 在；`__om3logText` 导出；老 id 一个不少；本轮不新增 id。

⚠ 探针自己踩过的两个坑（写在这里免得下次再犯）：
   ① 前置 JS 里点 `#tabCam` **没用**：那段 JS 在 body 开头执行，那时候页签的监听还没绑上 →
      后面所有元素都是"零尺寸"，看起来像"没放回来"。必须把点击当**步骤**跑。
   ② 钩 `window.__om3log` **收不到连接链的话**：连接链用的是块内的 `log()`/`step()`，
      不走导出的 `__om3log`。改成**轮询 `#camGateOut` 的文字变化**做时间线。

跑法：python scripts/dv_r74.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r74.html')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
F = K = 0

BANHELPER = '''
function watchText(ids){
  var last = {}, tl = [];
  var t0 = Date.now();
  setInterval(function(){
    for(var i = 0; i < ids.length; i++){
      var e = document.getElementById(ids[i]); if(!e) continue;
      var t = (e.innerText || '').replace(/\\s+/g, ' ').trim();
      if(t !== last[ids[i]]){
        var add = t;
        if(t.indexOf(last[ids[i]] || '') === 0) add = t.slice((last[ids[i]] || '').length);   /* 只记新增那段 */
        last[ids[i]] = t;
        tl.push({t: Date.now() - t0, id: ids[i], s: add.trim().slice(0, 160)});
      }
    }
  }, 150);
  window.__tlFn = function(){ return tl; };
}
'''


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


def run_headless(tag, extra_pre, steps, budget=60000):
    tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in steps], ensure_ascii=False) + ',si=0;\n'
            'function g(i){return document.getElementById(i);}\n'
            "function vis(id){var e=g(id);if(!e)return '无';var c=getComputedStyle(e);"
            "if(c.display==='none'||c.visibility==='hidden')return '隐藏';var r=e.getBoundingClientRect();"
            "return (r.width>0&&r.height>0)?'显示':'零尺寸';}\n" + BANHELPER +
            'function finish(){var d=document.createElement("div");d.id=\'' + tag + '\';'
            'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
            'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
            'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
            'setTimeout(next,1500);\n</script>')
    i0 = page.find('<body')
    j0 = page.find('>', i0) + 1
    out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
           'try{' + extra_pre + '}catch(e){}</script>' + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r74_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o74_' + tag)
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


print('=== A. 无头实测 ===')
# ── A1/A2：扫码入口可见 + 位置/样式（点击当步骤跑！）
got = run_headless('R74A', '', [
    ("g('tabCam').click();", 700),
    ("vis('paneD') === '显示' ? o.push('A0 进到连接相机页') : o.push('A0 没进到 paneD（paneD=' + vis('paneD') + '）');", 200),
    ("o.push('A1 camGateScan=' + vis('camGateScan') + ' camScan=' + vis('camScan')"
     " + ' camScanHelp=' + vis('camScanHelp') + ' camGateConn=' + vis('camGateConn'));", 200),
    ("var s=g('camGateScan'), c=g('camGateConn');"
     "o.push('A2 主按钮在扫码前面=' + !!(c.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING)"
     " + ' 扫码class=[' + s.className + '] 主按钮class=[' + c.className + ']');"
     "o.push('A9 运行错误=' + (window.__errs ? window.__errs.length : 0));", 200),
])
for seg in got.split(' ;; '):
    print('  · ' + seg)
A('A0 进到连接相机页' in got, 'A0 能进连接相机页（前置检查）')
# 口径修正（第 97 轮，需求方 2026-09-29「扫码还是扫不出来，实在不行就把扫码连接去掉吧」）：
# 这一条原来断的是"第 74 轮放回来的三个扫码入口都可见"。第 97 轮按规格**又收起来了**
# （只加 style="display:none"，class/节点/逻辑都没动），所以判据改成：
#   ① 三个入口**都隐藏**（第 97 轮的新目标态）② 「连接相机」照旧可见 ③ 节点/class 还在（第 97 轮另验"一键能开"）
A('A1 camGateScan=隐藏 camScan=隐藏 camScanHelp=隐藏 camGateConn=显示' in got,
  'A1 三个扫码入口**都收起来了**（第 97 轮决定；「连接相机」照旧在）—— 原来的口径是第 74 轮"都放回来"')
A('A2 主按钮在扫码前面=true' in got and 'gho' in got.split('A2')[1].split(';;')[0],
  'A2 扫码**排在「连接相机」之后**、且样式降一级（.gho）—— 是"往后放"而不是第一入口')
A('A9 运行错误=0' in got, 'A9 全程 0 运行错误')

# ── A3：蓝牙跑不起来 → 不许白等 10 秒（假桥里故意不给 ble* 接口）
BRIDGE_NOBLE = '''
window.OM3Native = (function(){
  var OTHER = [{ssid:'我家WiFi', bssid:'11:22:33:44:55:66', level:-55, cam:false}];
  return {
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
    wifiState: function(){ return JSON.stringify({ssid:'我家WiFi', on:true}); },
    wifiScanList: function(){ window.__scans = (window.__scans || 0) + 1; return JSON.stringify(OTHER); },
    cameraState: function(){ return '{"connected":false,"ssid":"","bssid":""}'; },
    startWatch: function(){ return 'ok'; }, camGet: function(){ return '{"status":0,"text":""}'; },
    disconnectCamera: function(){ return 'ok'; }, forgetWifi: function(){ return 'ok'; }, dropCamera: function(){ return 'ok'; },
    openWifiSettings: function(){ return 'ok'; }, openAppSettings: function(){ return 'ok'; }, shareText: function(){ return 'ok'; }
  };
})();
watchText(['camGateOut', 'camOut3']);
'''
got = run_headless('R74B', BRIDGE_NOBLE, [
    ("g('tabCam').click();", 1200),
    # ⚠ 不能用"文字变化时间线"量这件事：这条链可能是**同步**跑完的（click 里就把 1/3→2/3 都写了），
    #   那 watcher 第一次采样时文字已是最终态、什么都量不到（本轮踩过）。改成
    #   "100ms 轮询 + 记录每个标记**第一次**出现的时刻"。
    # ⚠ 量 #camOut3（日志框，只追加）：#camGateOut 那个提示框会被 camDirectConnect 里的
    #    host.innerHTML='' 清空 → 拿它当时间线会漏掉前两步（本轮踩过）
    ("window.__t0=Date.now(); window.__mark={}; window.__scans=0;"
     "window.__watch=setInterval(function(){var t=(g('camOut3')||{}).innerText||'';"
     "var n=Date.now()-window.__t0;"
     "if(!window.__mark.a && /第 1\\/3 步/.test(t)) window.__mark.a=n;"
     "if(!window.__mark.b && /第 2\\/3 步/.test(t)) window.__mark.b=n;},100);"
     "g('camGateConn').click();", 12000),
    ("var mk=window.__mark||{}; clearInterval(window.__watch);"
     "o.push('A3 标记=' + JSON.stringify(mk) + ' 间隔=' + ((mk.a!=null&&mk.b!=null)?(mk.b-mk.a):'量不到') + 'ms');"
     "var t3=((g('camOut3')||{}).innerText||'').replace(/\\n/g,' / ');"
     "o.push('A3 日志尾部=' + t3.slice(-320));"
     "o.push('A3 扫 Wi-Fi 次数=' + (window.__scans||0));", 200),
])
for seg in got.split(' ;; '):
    print('  · ' + seg)
m = re.search(r'A3 标记=\{[^}]*\} 间隔=(\d+)ms', got)
A(bool(m) and int(m.group(1)) < 2500,
  'A3 蓝牙这条路跑不起来时**不再白等 10 秒**（实测间隔 %s ms；修前 ~10000ms）' % (m.group(1) if m else '?'))
# 口径修正（第 80 轮）：需求方要求"**不许自动唤醒相机 Wi-Fi**"，所以那段"等蓝牙链/不等它了"
# 的分支整个没了 —— 现在点「连接相机」根本不碰蓝牙。要守的还是同一件事：
# **不会白等蓝牙**，而且**有话说清楚**（现在这句是"App 不会替你开相机 Wi-Fi …"）。
A('不等它了，直接进 Wi-Fi' in got or 'App 不会替你开相机 Wi-Fi' in got or '没有蓝牙接口）→ 直接试 Wi-Fi' in got,
  'A3 而且说清了（"不等它了，直接进 Wi-Fi" / "App 不会替你开相机 Wi-Fi" / "没有蓝牙接口）→ 直接试 Wi-Fi" —— 第 80 轮起不再自动跑蓝牙，所以措辞变了，语义还是"不等它，并说清为什么"）')

# ── A4：蓝牙可用但相机热点一直没起来 → 扫描必须被节流
BRIDGE_BLE = '''
window.OM3Native = (function(){
  var OTHER = [{ssid:'我家WiFi', bssid:'11:22:33:44:55:66', level:-55, cam:false}];
  return {
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
    wifiState: function(){ return JSON.stringify({ssid:'我家WiFi', on:true}); },
    wifiScanList: function(){ window.__scans = (window.__scans || 0) + 1; return JSON.stringify(OTHER); },
    cameraState: function(){ return '{"connected":false,"ssid":"","bssid":""}'; },
    startWatch: function(){ return 'ok'; }, camGet: function(){ return '{"status":0,"text":""}'; },
    /* 蓝牙接口齐全（所以它会真的等蓝牙链）—— 但不给任何扫描结果/连接结果 */
    bleScan: function(){ return 'ok'; }, bleScanCam: function(){ return 'ok'; }, bleConnect: function(){ return 'ok'; },
    bleCmd: function(){ return 'ok'; }, bleWrite: function(){ return 'ok'; }, bleScanStop: function(){ return 'ok'; },
    bleDisconnect: function(){ return 'ok'; }, blePermDetail: function(){ return '{}'; }, bleAskPerm: function(){ return 'ok'; },
    disconnectCamera: function(){ return 'ok'; }, forgetWifi: function(){ return 'ok'; }, dropCamera: function(){ return 'ok'; },
    openWifiSettings: function(){ return 'ok'; }, openAppSettings: function(){ return 'ok'; }, shareText: function(){ return 'ok'; }
  };
})();
watchText(['camGateOut', 'camOut3']);
'''
got = run_headless('R74C', BRIDGE_BLE, [
    ("g('tabCam').click();", 1200),
    ("window.__scans = 0; watchText(['camGateOut','camOut3']); g('camGateConn').click();", 14000),
    ("var tl=window.__tlFn ? window.__tlFn() : [];"
     "o.push('A4 扫 Wi-Fi 次数=' + (window.__scans||0) + '（窗口约 14 秒）');"
     "o.push('A4 节流提示=' + (tl.some(function(x){return /没重复扫 Wi-Fi（节流 \\d+ 秒）/.test(x.s);}) ? '有' : '没有'));"
     "o.push('A4 提示文案=' + (g('camGateOut') ? g('camGateOut').innerText.replace(/\\n/g,' / ').slice(0,200) : '无'));", 300),
])
for seg in got.split(' ;; '):
    print('  · ' + seg)
m2 = re.search(r'A4 扫 Wi-Fi 次数=(\d+)', got)
A(bool(m2) and int(m2.group(1)) <= 6,
  'A4 等热点期间真扫 Wi-Fi 次数 ≤ 6（实测 %s 次/14 秒；修前 10 秒里就 ~20 次）' % (m2.group(1) if m2 else '?'))
# 口径修正（第 78 轮）：真机日志证明安卓前台扫描限额约 4 次/2 分钟，
# 所以节流从 5 秒放宽到 30 秒。这里**只断言"有这句说明"**，不把秒数写死（写死会在调整时假红）。
# 第 78 轮口径修正：节流从 5 秒放宽到 30 秒后，十几秒的窗口里**不会**再出现第二次真扫，
# 所以"节流那句日志"在这个窗口里本来就不该出现（它要等 ≥30 秒才可能打）。
# 运行期改成断言**正确的表现**：窗口内真扫 ≤2 次；那句话是否存在放到静态断言里查。
A('A4 扫 Wi-Fi 次数=2（窗口约 14 秒）' in got or 'A4 扫 Wi-Fi 次数=1（窗口约 14 秒）' in got,
  'A4 十几秒窗口内真扫 ≤2 次（30 秒节流的正确表现；修前是每 500ms 一次 ≈20 次）')
A('没重复扫 Wi-Fi（节流' in page, 'A4 静态：节流那句日志确实在页面里（N 不写死，第 78 轮按真机改成 30 秒）')
A('A4 提示文案=' in got and '手动填 SSID / 密码最稳' in got.split('A4 提示文案=')[-1],
  'A2b 提示文案改成了**看得见的那条路**（第 97 轮扫码入口收起后，提示语里改指「手动填 SSID / 密码」；'
  '第 74 轮这里指的是「扫码连接（忘了密码时用）」）')

# ── A5：日志头 + 不含密码
SAVED = {"ssid": "OM-3", "pass": "SIM-PASS-1234", "model": "OM-3", "serial": "BJ8A0001", "at": 1759000000000}
PRE5 = ("localStorage.setItem('om3cam', %s);" % json.dumps(json.dumps(SAVED))) + BRIDGE_BLE
got = run_headless('R74D', PRE5, [
    ("window.__om3log('第一行测试'); window.__om3log('第二行测试','warn');", 300),
    ("var t = (window.__om3logText ? window.__om3logText() : '(没有 __om3logText)');"
     "o.push('A5 日志长度=' + t.length);"
     "['App：','设备/系统：','屏幕：','权限：','记住的相机：','当前连接：','蓝牙口令：','页面：']"
     ".forEach(function(k){ o.push('A5 头 ' + k + '=' + (t.indexOf(k) >= 0)); });"
     "o.push('A5 含密码=' + (t.indexOf('SIM-PASS-1234') >= 0));"
     "o.push('A5 记住行=' + (t.split('\\n').filter(function(l){return l.indexOf('记住的相机：')===0;})[0] || '无'));", 200),
])
for seg in got.split(' ;; '):
    print('  · ' + seg)
A(re.search(r'A5 日志长度=[1-9]\d{2,}', got) is not None, 'A5 能取到导出的日志文本（__om3logText）')
for k in ['App：', '设备/系统：', '屏幕：', '权限：', '记住的相机：', '当前连接：', '蓝牙口令：']:
    A('A5 头 %s=true' % k in got, 'A5 日志头有「%s」' % k)
A('A5 含密码=false' in got, 'A5 **日志里不含相机密码**（故意存了一份带密码的记录来试）')
A('SSID=OM-3' in got and '密码不写进日志' in got, 'A5 记住的相机那行写了 SSID/型号，并注明密码不写进日志')

print('=== B. 静态 ===')
A('.hid49{display:none !important}' in page, 'B1 .hid49 的 CSS 还在（留着当"再藏回去"的开关）')
A(re.search(r'<button[^>]*class="[^"]*hid49', page) is None,
  'B1 没有任何**按钮**带 .hid49（第 97 轮的隐藏用的是 style="display:none"，.hid49 只作为历史开关留着）')
A("id=\"camGateScan\" style=\"display:none\"" in page
  and "id=\"camScan\" class=\"camprimary\" style=\"display:none\"" in page
  and "id=\"camScanHelp\" style=\"display:none\"" in page,
  'B1b 第 97 轮：三个扫码入口是**一行 style 开关**（想开就删这 3 处 style）')
A("var blePossible = (function(){" in page and 'if(!blePossible){' in page,
  'B2 蓝牙可用性判据在（跑不起来就不等那 10 秒）')
_thr = re.search(r'\(now - _hsAt\) >= (\d+)\)', page)
A(_thr is not None and int(_thr.group(1)) >= 5000,
  'B3 热点探测有节流（当前 %s 秒，要求 ≥5 秒）+ 需要时可强制重扫'
  % (_thr.group(1) if _thr else '（没找到）'))
A('_hsSkipped++' in page and 'window.__om3hotspotForce' in page,
  'B3b 有"跳过了几次"的计数与强制重扫入口')
A('window.__om3logText = logText;' in page, 'B4 日志文本导出（探针/测试页可用）')
A('r74：扫码放回 + 日志头' in page, 'B5 r74 标记在（生成脚本幂等判据）')
A('class="big gho" id="camGateScan"' in page, 'B6 扫码按钮是次要样式（.gho）')
A('扫二维码（第一次）' not in page, 'B7 旧按钮名的残留文案都清掉了（文案与按钮一致）')
si, so = ids(page), ids(old)
A(not (so - si), 'B8 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B9 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print()
print('第 74 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
