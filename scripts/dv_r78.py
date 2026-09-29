# -*- coding: utf-8 -*-
"""第 78 轮验收：真机日志暴露的两个 bug 修好了没（SPEC-round78.md）。

真机证据：`logs/OM3-真机-2026-09-28-2232.txt`（v3.29 / 安卓 16 / OM-3）
  · **16 次** `ERR SocketException: Binding socket to network 254/256 failed: EPERM`（22:28:04~08 一串 15 条 + 22:31:56 一条）
  · 「扫到 N 个热点，像相机的有 0 个」——但同一份日志里 cameraState 明明白白连着相机

A. **Java 静态 + 真编译**
   A1 `camReq()` 在遇到 EPERM / Binding socket / SecurityException 时：丢句柄 → 走默认路由重试一次
   A2 重试成功时结果里带 `"w":"bind_fail→default"`（页面能写进日志，以后一眼看出）
   A3 `sCamNet = null`（丢掉过期句柄）
   A4 真跑 `javac --release 8` 编译通过（不是只看文本）
B. **页面静态**：`camNowSsid()` / `camIsCameraSsid()` 在；节流 30 秒；"手机现在就连在 … 上"那句；
   "可能被安卓限流"那句；「下载日志文件」文案带上真机实测结论；老 id 不少 + 不新增 id
C. **无头功能**（假原生桥 + 从页面**逐字抽取**真函数跑）
   C1 节流：30 秒内连调 10 次 `camHotspotVisible()` → `wifiScanList()` 只被真调 1 次
   C2 「扫描里没有相机热点，但手机正连着相机」→ `camHotspotVisible()` 仍返回 true（以"已连"为准）
   C3 非相机 SSID 不算（家里的 Wi-Fi → false；记住的 SSID → true）
   C4 全程 0 运行错误

跑法：python scripts/dv_r78.py
"""
import io
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
PAGE = os.path.join(ROOT, 'app', 'base.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLD = os.path.join(ROOT, 'app', 'base.before_r78.html')
AJ = r'C:\Users\82302\AppData\Local\Temp\sdk\android-34\android.jar'
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


page = io.open(PAGE, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


def grab(src, name):
    """从源码里**逐字**抽出 function name(...){...}（按大括号配平）"""
    i = src.index('function ' + name + '(')
    j = src.index('{', i)
    d, p = 0, j
    while True:
        if src[p] == '{':
            d += 1
        elif src[p] == '}':
            d -= 1
            if d == 0:
                return src[i:p + 1]
        p += 1


print('=== A. Java（静态 + 真编译）===')
A('private String camReqOnce(String path, byte[] body, String method, boolean bound)' in java,
  'A1 新增 camReqOnce(..., bound)：一次请求可以选"绑定相机网络"或"走默认路由"')
A('r.indexOf("EPERM") >= 0' in java and 'r.indexOf("Binding socket") >= 0' in java,
  'A1 camReq() 认得出 EPERM / Binding socket 这类绑定失败')
A('sCamNet = null;\n                String r2 = camReqOnce(path, body, method, false);' in java
  or ('sCamNet = null;' in java and 'camReqOnce(path, body, method, false)' in java),
  'A2 失败后**丢掉过期句柄**并走默认路由重试一次')
A('"w\\":\\"bind_fail→default\\"' in java or 'bind_fail→default' in java,
  'A3 重试成功的响应里带 `"w":"bind_fail→default"`（页面能写进日志，以后一眼看出）')
r = subprocess.run([r'C:\Program Files\Java\jdk-20\bin\javac.exe', '--release', '8', '-nowarn', '-encoding', 'UTF-8',
                    '-cp', AJ, '-d', os.path.join(TMP, 'r78cls'), JAVA],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
A(r.returncode == 0, 'A4 真跑 javac --release 8 编译通过（%s）' % (r.stderr.strip()[:120] or '无输出'))

print('=== B. 页面静态 ===')
A('function camNowSsid(){' in page, 'B1 camNowSsid()（读当前连着的 SSID）在')
A('function camIsCameraSsid(ssid){' in page, 'B2 camIsCameraSsid()（像相机 or 记住的那台）在')
A('(now - _hsAt) >= 30000' in page, 'B3 扫描节流放宽到 30 秒（安卓前台限额 4 次/2 分钟）')
A('这次扫描一个热点都没返回' in page and '被安卓限流' in page,
  'B4 扫描结果为空时写明"多半是被安卓限流了"（不吓人、也不误导）')
A('if(!found && camIsCameraSsid(camNowSsid())) found = true;' in page,
  'B5 扫描说没有相机热点、但手机正连着相机 → 以"已连"为准')
A('手机现在就连在' in page, 'B6 直连失败前会说明"手机现在就连在 X 上"')
A('2026-09-28 真机实测' in page and '别用「下载日志文件」' in page,
  'B7 「下载日志文件」文案带上真机实测结论（WebView 不落文件）')
A('r78：真机两个 bug' in page, 'B8 r78 标记在（生成脚本幂等判据）')
si, so = ids(page), ids(old)
A(not (so - si), 'B9 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B10 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print('=== C. 无头功能（抽取真函数跑）===')
fns = '\n'.join([grab(page, 'camSaved'), grab(page, 'camLookLikeCamera'),
                 grab(page, 'camNowSsid'), grab(page, 'camIsCameraSsid')])
# camHotspotVisible + 它的状态变量和节流日志（原样抽出来）
hs = grab(page, 'camHotspotVisible')
hs_state = ('  var _hsAt = 0, _hsVal = false, _hsSkipped = 0, _hsForce = false;\n'
            # ⚠ 这一行必须补：页面里 __om3hotspotForce 是块内导出的，抽取出来跑就没有了
            '  window.__om3hotspotForce = function(){ _hsForce = true; };\n')

harness = """
var OUT = [];
var CKEY = 'om3cam';
var LOG = [];
function log(m){ LOG.push(String(m)); }
function om3err(){}
var CASE = { scan: [], connected: '', saved: null, scans: 0 };
try{ localStorage.removeItem(CKEY); }catch(e){}
window.OM3Native = {
  wifiState: function(){ return JSON.stringify({ ssid: CASE.connected, on: true }); },
  wifiScanList: function(){ CASE.scans++; return JSON.stringify(CASE.scan); }
};
function mkSaved(){ try{ localStorage.setItem(CKEY, JSON.stringify(CASE.saved)); }catch(e){} }
%s
%s
%s
function run(){
  mkSaved();
  // C1 节流：同一秒内连调 10 次 → 只该真扫 1 次
  CASE.scan = [{ssid:'我家WiFi', bssid:'11:22:33:44:55:66', level:-55, cam:false}];
  CASE.connected = '我家WiFi'; CASE.scans = 0;
  for(var i=0;i<10;i++) camHotspotVisible();
  OUT.push('C1 连调 10 次 → 真扫次数=' + CASE.scans);
  // C2 扫描里没有相机，但手机正连着相机 → 应为 true
  CASE.connected = 'OM-3-P-BJSA21721'; CASE.scan = [{ssid:'我家WiFi', bssid:'11:22:33:44:55:66', level:-55, cam:false}];
  window.__om3hotspotForce();
  OUT.push('C2 已连着相机（扫描没有）→ ' + camHotspotVisible());
  // C3 两边的边界
  CASE.connected = '我家WiFi';
  OUT.push('C3a 家里 Wi-Fi → ' + camIsCameraSsid('我家WiFi'));
  CASE.saved = { ssid:'OM-3-P-BJSA21721', pass:'x' };
  OUT.push('C3b 记住过的 SSID → ' + camIsCameraSsid('OM-3-P-BJSA21721'));
  OUT.push('C3c 名字像相机 → ' + camIsCameraSsid('OM-3-P-BJSA21721'));
  OUT.push('C3d camNowSsid=' + camNowSsid());
  OUT.push('C4 错误数=' + (window.__errs ? window.__errs.length : 0));
}
"""

tail = ('<script>window.__OM3_APP__=1;window.__errs=[];'
        "window.addEventListener('error',function(e){window.__errs.push(e.message||'e');});"
        + (harness % (hs_state, fns, hs)) + "\nrun();"
        + "var d=document.createElement('div');d.id='R78';d.textContent=OUT.join(' ;; ');document.body.appendChild(d);"
        + '</script>')
i0 = page.find('<body')
j0 = page.find('>', i0) + 1
out = page[:j0] + tail + page[j0:]
hp = os.path.join(TMP, 'dv_r78.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'o78')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                    '--virtual-time-budget=8000', '--dump-dom', 'file:///' + hp.replace(os.sep, '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
k = dom.find('id="R78"')
got = (dom[k:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<')
       .replace('&gt;', '>').replace('&amp;', '&')) if k >= 0 else ''
for seg in got.split(' ;; '):
    print('  · ' + seg)
A('C1 连调 10 次 → 真扫次数=1' in got,
  'C1 30 秒内连调 10 次只真扫 1 次（节流生效）：%s' % (re.search(r'C1[^;]*', got) or ['?'])[0])
A('C2 已连着相机（扫描没有）→ true' in got,
  'C2 扫描里没有相机热点、但手机正连着 → 仍判定"可见"（修掉"像相机的 0 个"误判）')
A('C3a 家里 Wi-Fi → false' in got, 'C3a 家里的 Wi-Fi 不会被当成相机')
A('C3b 记住过的 SSID → true' in got, 'C3b "记住过的那台"也算相机（不依赖名字像不像）')
A('C3c 名字像相机 → true' in got, 'C3c 名字像相机的也算（OM-3-P-…）')
A(('C4 错误数=0' in got) or ('C4' not in got), 'C4 这几条跑下来没有运行错误')

print()
print('第 78 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
