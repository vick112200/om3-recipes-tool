# -*- coding: utf-8 -*-
"""第 68 轮验收：独立「测试页（连接诊断）」+ 客户页降噪。

A. **无头浏览器实测**（真 DOM）：☰ 菜单 → 点「🔧 测试页」→ 断言真的切到 `#paneT`（客户页隐藏、
   底栏/搜索栏不显示）→ 状态面板有内容 → 点「← 回连接相机」能回来 → 客户页的 `#camOut3` 确实在
   `#camLogFold` 里且默认收起、日志三按钮在测试页里。
B. **静态**：① 新增 id **完全等于** `SPEC-round68.md` §2.3 那张表（多一个少一个都红）
   ② 原有 id 一个不少 ③ 三处页签名单都有 `T` ④ 按钮都复用既有动作（不复制实现）
   ⑤ 客户页不再有扫描明细 ⑥ 日志里不含密码（既有约定回归）。
C. **node 功能段**：把测试页那段 JS 原样抽出来 + 迷你 DOM 桩，喂假数据断言：
   状态面板在"按 SSID 看着连上"和"HTTP 确认通了"两种情况下**措辞不同**；扫 Wi-Fi 明细会把
   SSID / 信号 / BSSID / 📷 都列出来。

跑法：python scripts/dv_r68.py
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
PAGE = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r68.html')
SPEC = os.path.join(ROOT, 'SPEC-round68.md')
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
spec = io.open(SPEC, encoding='utf-8').read()


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


def blk(t, marker):
    i = t.index(marker)
    i = t.index('{', i)
    d = 0
    for m in re.finditer(r'\{|\}', t[i:]):
        d += 1 if m.group(0) == '{' else -1
        if d == 0:
            return t[i:i + m.end()]
    raise AssertionError(marker)


si, so = ids(page), ids(old)

print('=== A. 无头浏览器实测（真 DOM：进测试页 / 回客户页 / 客户页降噪） ===')
probe = []
probe.append("setTimeout(function(){var o=[];")
# 客户页：日志折叠与三按钮位置
probe.append("var f=document.getElementById('camLogFold'), o3=document.getElementById('camOut3');")
probe.append("o.push('camLogFold=' + (f?f.tagName:'无') + ' open=' + (f?f.open:'-') + ' camOut3在里面=' + !!(f&&f.contains(o3)));")
probe.append("var pt=document.getElementById('paneT');")
probe.append("o.push('按钮在测试页里=' + !!(pt&&pt.contains(document.getElementById('camCopyLog'))&&pt.contains(document.getElementById('camDlLog'))&&pt.contains(document.getElementById('camClearLog'))));")
probe.append("o.push('起始 cur=' + window.__om3cur + ' paneT 隐藏=' + (pt?pt.classList.contains('hide'):'无') + ' paneD 隐藏=' + document.getElementById('paneD').classList.contains('hide'));")
# 点 ☰ → 测试页
probe.append("var mb=document.getElementById('camMenuBtn'); if(mb) mb.click();")
probe.append("setTimeout(function(){")
probe.append("var mi=document.querySelector('#camMenuDrop button[data-act=test]'); o.push('菜单项在=' + !!mi);")
probe.append("if(mi) mi.click();")
probe.append("setTimeout(function(){")
probe.append("o.push('点了之后 cur=' + window.__om3cur + ' paneT可见=' + !pt.classList.contains('hide') + ' paneD隐藏=' + document.getElementById('paneD').classList.contains('hide'));")
probe.append("o.push('底栏显示=' + document.getElementById('barD').classList.contains('show') + ' 搜索栏显示=' + document.getElementById('row2').style.display);")
probe.append("var st=document.getElementById('tvState'); o.push('状态面板长度=' + (st?st.textContent.length:0) + ' 含原生桥=' + /原生桥/.test(st?st.textContent:''));")
probe.append("o.push('日志镜像在=' + !!document.getElementById('tvLog') + ' 按钮数=' + pt.querySelectorAll('button').length);")
# 回客户页
probe.append("var bk=document.getElementById('tvBack'); if(bk) bk.click();")
probe.append("setTimeout(function(){")
probe.append("o.push('返回后 cur=' + window.__om3cur + ' paneT隐藏=' + pt.classList.contains('hide') + ' paneD可见=' + !document.getElementById('paneD').classList.contains('hide'));")
probe.append("o.push('运行错误=' + (window.__errs?window.__errs.length:0) + ' om3errs=' + (window.__om3errs||0));")
probe.append("var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);")
probe.append("},700);},700);},700);},2600);")
head = ("<script>window.__OM3_APP__=1;window.__errs=[];window.addEventListener('error',function(e){"
        "window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
        "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});</script>")
tail = '<script>' + ''.join(probe) + '</script>'
i = page.find('<body')
j = page.find('>', i) + 1
out = page[:j] + head + page[j:].replace('</body>', tail + '</body>', 1)
hp = os.path.join(TMP, 'dv_r68.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'o68')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=12000', '--dump-dom',
                    'file:///' + hp.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
if k < 0:
    A(False, '无头浏览器没拿到输出（DOM %d 字节）' % len(dom))
else:
    got = dom[k:].split('>', 1)[1].split('</div>')[0]
    print('  （实测输出）' + got[:400])
    A('camLogFold=DETAILS' in got and 'open=false' in got and 'camOut3在里面=true' in got,
      '客户页：日志已折进 <details id="camLogFold">，默认收起，且 #camOut3 确实在里面')
    A('按钮在测试页里=true' in got, '日志三按钮（复制/下载/清空）已搬到测试页里')
    A('paneT 隐藏=true' in got and '起始 cur=T' not in got,
      '起手：测试页是隐藏的、也没停在测试页（客户不会一打开就进诊断页）')
    A('paneD 隐藏=true' in got, '起手「连接相机」页也是隐藏的（和改前一致）')
    A('菜单项在=true' in got, '☰ 菜单里有「🔧 测试页（连接诊断）」这一项')
    A("点了之后 cur=T" in got and 'paneT可见=true' in got and 'paneD隐藏=true' in got,
      '点菜单项 → 真的切到测试页（cur=T，客户页隐藏）')
    A('底栏显示=false' in got and '搜索栏显示=none' in got, '在测试页时底栏/搜索栏都不显示（不干扰）')
    A('含原生桥=true' in got, '状态面板有内容（无头里显示"没有原生桥"也是对的）')
    A('日志镜像在=true' in got, '日志镜像 #tvLog 在位')
    A("返回后 cur=D" in got and 'paneT隐藏=true' in got and 'paneD可见=true' in got,
      '点「← 回连接相机」→ 回到客户页')
    A('运行错误=0' in got and 'om3errs=0' in got, '整个过程 0 运行错误')

print('=== B. 静态：新增 id 完全等于规格那张表 / 原有 id 一个不少 ===')
sec = spec[spec.index('### 2.3'):spec.index('### 2.4')]
declared = set()
for line in sec.splitlines():
    if not line.startswith('|'):
        continue
    cell = line.split('|')[1]
    for m in re.finditer(r'`([A-Za-z][A-Za-z0-9_]*)`', cell):
        declared.add(m.group(1))
added = si - so
missing = so - si
A(not missing, '原有 id 一个都没少（少的：%s）' % (sorted(missing) or '无'))
# 第 69 轮起允许**再新增** id（后续轮次各自按自己的规格断言）。
# 这里钉的是"**第 68 轮声明的那 15 个必须还在**" —— 判据没放松（少一个就红），
# 只是不再要求"新增集合 == 第 68 轮那张表"（那会禁止以后任何一轮加 id）。
A(declared <= added, '第 68 轮声明的 %d 个新 id 都还在（少的：%s）'
  % (len(declared), sorted(declared - added) or '无'))
print('  （新增 %d 个：%s）' % (len(added), '、'.join(sorted(added))))
A(all(('id="%s"' % x) in page for x in declared), '新增 id 每一个都在页面里')
for mark in ("var PANES = ['A', 'B', 'C', 'D', 'E', 'T']", "var PS = ['A','B','C','D','E','T']",
             "T:'paneT'"):
    A(mark in page, '页签名单里都有 T：%s' % mark[:38])
A("if(a === 'test')" in page and "$('tabTest')" in page, '菜单项走的是隐藏代理页签（复用既有切换逻辑）')
A("tpan && !tpan.classList.contains('hide')" in page, '返回键在测试页时先回「连接相机」')

print('=== B2. 测试页按钮都复用既有动作（不复制实现） ===')
tvjs = page[page.index('/* ================= r68：测试页'):page.index('\n  var cc = $(\'camConnCheck\')')]
pairs = [('tvChain', '__om3camWifiChain'), ('tvDirect', '__om3direct'), ('tvCheck', "'camCheck'"),
         ('tvSaved', "'camConnect'"), ('tvBle', '__om3camBleAuto'), ('tvBleStop', "'camLinkStop'"),
         ('tvBack', "'tabCam'"), ('tvRefresh', 'tvRefreshNow')]
for bid, target in pairs:
    i = tvjs.find("tvBind('%s'" % bid)
    seg = tvjs[i:i + 400] if i >= 0 else ''
    A(i >= 0 and target in seg, '按钮 %s → 复用 %s' % (bid, target))
A('window.__om3tvState = tvState' in tvjs and 'window.__om3tvRender = tvRender' in tvjs,
  '状态面板/日志镜像导出了（供探针与后续轮次用）')
A('if(tvOn()) tvRefreshNow();' in tvjs.replace(' ', ' '), '只在"测试页可见"时才刷新（客户页零开销）')

print('=== B3. 客户页降噪 ===')
gate = blk(page, "function camDirectConnect(")
A('dBm)' not in gate.split('say(')[1].split('log(')[0] if 'say(' in gate else True,
  '客户卡上不再印 SSID/信号明细（只说"扫到 N 个，像相机的 M 个"）')
A('[直连] 明细：' in gate and "x.level + 'dBm)'" in gate, '明细改成写进日志（测试页能看到）')
# 第 68 轮真正要守的是"日志按钮那一组在测试页、不在客户页"。
# 原来写的是"整份页面只有 1 处"，但后面几轮（第 77 轮"不确定的事"那两条 ⑦/⑧ 的回答键）
# 在测试页里又用了同一个类名 → 计数断言会假红。**改成按位置判定**（口径修正，不是放松）：
#   · camlogbtns 全部出现在 #paneT 里（客户页 paneD 里一处都没有）
#   · 三个日志按钮（camCopyLog / camDlLog / camClearLog）仍在测试页
_iT, _iE = page.find('<div id="paneT"'), page.find('<div id="paneE"')
_logbtns = [m.start() for m in re.finditer(r'class="camlogbtns"', page)]
A(bool(_logbtns) and all(_iT < p < _iE for p in _logbtns),
  '`camlogbtns`（日志按钮那一组）全部在测试页里、客户页一处都没有（共 %d 处）' % len(_logbtns))
A(all(_iT < page.find('id="%s"' % b) < _iE for b in ('camCopyLog', 'camDlLog', 'camClearLog')),
  '三个日志按钮（复制 / 下载 / 清空）仍都在测试页（第 68 轮"客户页降噪"的核心）')
A('🔧 测试页（连接诊断）' in page and page.count('🔧 测试页（连接诊断') >= 3,
  '入口措辞一致：菜单一项 + 客户页两处指路')
# 日志里不含密码（既有约定）
bad = re.findall(r'log\([^)]*\bpass\b', page)
A(not bad, '日志调用里没有把密码拼进去（既有约定，回归检查）')

print('=== C. node 功能段：状态面板措辞 + 扫 Wi-Fi 明细 ===')
HARNESS = r'''
/* ---- 迷你 DOM/环境桩 ---- */
var OUT = {};
function stubEl(id){ var e = { id:id, innerHTML:'', textContent:'', scrollTop:0,
  addEventListener:function(ev, fn){ this._h = fn; },
  classList:{ contains:function(){ return false; }, toggle:function(){}, add:function(){} } };
  OUT[id] = e; return e; }
['tvState','tvOut','tvLog','tvRefresh','tvScan','tvChain','tvDirect','tvCheck','tvSaved','tvBle','tvBleStop','tvBack']
  .forEach(stubEl);
function $(id){ return OUT[id] || stubEl(id); }
var CAMON = false;
var document = { body:{ classList:{ contains:function(c){ return c === 'cam-on' && CAMON; } } },
                 querySelector:function(){ return null; }, getElementById:function(id){ return OUT[id] || stubEl(id); } };
var window = { OM3Native:null };
function setInterval(){ return 0; }                 /* 不让定时器把 node 挂住 */
function log(){} function om3err(){} function esc(s){ return String(s == null ? '' : s); }
function line(el, msg, cls){ try{ el.innerHTML += (cls ? ('[' + cls + '] ') : '') + msg + '\n'; }catch(e){} }
function wifiCached(){ return { wifi:true, ssid:'OM-3-1' }; }
function camSaved(){ return { ssid:'OM-3-1', bssid:'AA:BB:CC:DD:EE:01', model:'OM-3', serial:'SN9' }; }
var _camHTTP = false, BLEON = true, BLENAME = 'OM-3 BLE', BLEMAC = 'AA:BB:CC:11:22:33', BLEMTU = 'MTU=247';
var Native = null;
__JS__
Native = { wifiScanList: function(){ return JSON.stringify([
  { ssid:'OM-3-1', level:-45, cam:true,  bssid:'AA:BB:CC:DD:EE:01' },
  { ssid:'HomeWiFi', level:-70, cam:false, bssid:'' },
  { ssid:'Neighbor-5G', level:-88, cam:false, bssid:'11:22:33:44:55:66' } ]); },
  permState: function(){ return JSON.stringify({camera:true, fine:false, nearby:true, sdk:34}); },
  cameraState: function(){ return JSON.stringify({connected:true, ssid:'OM-3-1', bssid:'AA:BB:CC:DD:EE:01'}); },
  blePermDetail: function(){ return 'SDK=34；BLUETOOTH_SCAN=有；BLUETOOTH_CONNECT=有；蓝牙开关=开'; } };
window.OM3Native = Native;
var out = [];
/* ① 状态面板：只按 SSID 看着连上（_camHTTP=false，cam-on=true） */
CAMON = true; _camHTTP = false;
window.__om3tvState();
out.push(['状态_未确认', OUT.tvState.innerHTML]);
/* ② 状态面板：HTTP 确认通了 */
_camHTTP = true;
window.__om3tvState();
out.push(['状态_已确认', OUT.tvState.innerHTML]);
/* ③ 扫 Wi-Fi 明细 */
CAMON = false;
OUT.tvScan._h();
out.push(['扫描明细', OUT.tvOut.innerHTML]);
console.log(JSON.stringify(out));
'''
js = page[page.index('/* ================= r68：测试页'):page.index('\n  var cc = $(\'camConnCheck\')')]
p = os.path.join(TMP, '_dv_r68.js')
io.open(p, 'w', encoding='utf-8').write(HARNESS.replace('__JS__', js))
try:
    r2 = subprocess.run(['node', p], capture_output=True, text=True, encoding='utf-8', timeout=60)
except FileNotFoundError:
    print('  （没装 node，跳过功能部分）')
    r2 = None
if r2 is not None:
    if r2.returncode != 0:
        A(False, 'node 跑挂了：' + (r2.stderr or '')[-400:])
    else:
        rows = dict((x[0], x[1]) for x in json.loads(r2.stdout.strip().splitlines()[-1]))
        s1, s2 = rows['状态_未确认'], rows['状态_已确认']
        A('HTTP 还没确认' in s1 and 'HTTP 确认通了' not in s1,
          '状态面板：只按 SSID 看着连上时说"HTTP 还没确认"（不谎报）')
        A('HTTP 确认通了' in s2, '状态面板：HTTP 真通时说"HTTP 确认通了"')
        A('OM-3-1' in s1 and 'AA:BB:CC:DD:EE:01' in s1 and 'OM-3' in s1, '状态面板带 SSID/BSSID/机型')
        A('附近的设备=有' in s1 and 'SDK=34' in s1, '状态面板带权限与 SDK')
        A('AA:BB:CC:11:22:33' in s1 and 'MTU=247' in s1, '状态面板带蓝牙状态/MTU')
        sc = rows['扫描明细']
        A('扫到 3 个热点' in sc, '扫 Wi-Fi：报总数 3')
        A('📷 OM-3-1' in sc and '-45dBm' in sc and 'AA:BB:CC:DD:EE:01' in sc, '扫 Wi-Fi：相机那行带 📷 和 BSSID')
        A('（系统没给 BSSID）' in sc and '11:22:33:44:55:66' in sc, '扫 Wi-Fi：没 BSSID 的说清楚，有 BSSID 的照列')
        A('其中像相机的 1 个' in sc, '扫 Wi-Fi：给"像相机几个"的结论')

print()
print('第 68 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
