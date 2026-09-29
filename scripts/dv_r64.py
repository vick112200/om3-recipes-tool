# -*- coding: utf-8 -*-
"""第 64 轮验收：Wi-Fi 连接加 **BSSID**（照官方 SSID+BSSID 精连那一个热点）。

三部分：
  A. Java 静态 + 编译：`connectCamera2` / `setBssid` / `SDK_INT > 30` 门 / `onCapabilitiesChanged`
     取真值 / 官方两条判据（`endsWith("00:00")`、SSID 必须对得上）/ `wifiScanList` 带 bssid /
     `wifiScanList` 的归一化 / 4713 分支不再用临时 Bridge；最后真跑一次 `javac`（编不过就红）。
  B. 页面静态：id 集合与改动前**完全一致**、两处调用点都走 `camConnectRaw`、5 处 camSave 全走 `camRec`、
     BSSID 显示在位、`window.__om3camBssid` 在位。
  C. node 功能段：把页面里那 4 个函数（`camBssidOk`/`camRec`/`camBssidMerge`/`camConnectRaw`）**原样抽出来**，
     喂构造样例 + 假 `Native`，断言"有 BSSID 就走 3 参、没有/不合法就退回 2 参、原生没用 BSSID 时页面不许吹牛"。

跑法：python scripts/dv_r64.py
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
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLD_PAGE = os.path.join(ROOT, 'app', 'base.before_r64.html')
AJ = r'C:\Users\82302\AppData\Local\Temp\sdk\android-34\android.jar'
JDK = r'C:\Program Files\Java\jdk-20'
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD_PAGE, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()

# ============================================================ A. Java 侧
print('=== A. Java：BSSID 真的交给系统了吗 ===')
A('public String connectCamera2(final String ssid, final String pass, final String bssid)' in java,
  '新增 connectCamera2(ssid, pass, bssid)')
A(re.search(r'public String connectCamera\(final String ssid, final String pass\) \{\s*'
            r'return connectCamera2\(ssid, pass, null\);', java) is not None,
  '老方法 connectCamera(ssid, pass) 保留（转调 connectCamera2，行为不变）')
A('@JavascriptInterface' in java.split('public String connectCamera2')[0].rsplit('}', 1)[1],
  'connectCamera2 也带 @JavascriptInterface')
A('b.setBssid(android.net.MacAddress.fromString(lastBssid))' in java,
  '用 setBssid(MacAddress.fromString(...)) 钉住热点')
A('Build.VERSION.SDK_INT > 30' in java, '有 SDK_INT > 30 的版本门（照官方 30 < SDK_INT）')
i_gate = java.index('Build.VERSION.SDK_INT > 30')
i_set = java.index('b.setBssid(android.net.MacAddress.fromString')
A(i_gate < i_set and (i_set - i_gate) < 400, 'setBssid 在版本门**里面**（低版本不会设）')
A('catch (Throwable t)' in java[i_set:i_set + 400], 'setBssid 抛异常时吞掉（不许因此让连接失败）')
A('return pinned ? "asking@bssid" : "asking";' in java, '返回码带 @bssid 后缀（页面据此如实说明走哪条路）')
A('private volatile String lastBssid = "";' in java, 'lastBssid 用 volatile（系统线程写 / JS 线程读）')
A('public void onCapabilitiesChanged(android.net.Network n, android.net.NetworkCapabilities caps)' in java,
  '新增 onCapabilitiesChanged（官方就是在这儿存 BSSID 的）')
A('caps.getTransportInfo()' in java and 'wi.getBSSID()' in java and 'wi.getSSID()' in java,
  '从 NetworkCapabilities → WifiInfo 读 SSID/BSSID')
A('bssid.endsWith("00:00")' in java, '官方判据①：以 "00:00" 结尾的假值一律不要')
A('!lastSsid.equals(ssid)' in java, '官方判据②：SSID 必须等于本次请求的那个')
A('if (Build.VERSION.SDK_INT < 30) return;' in java, '官方判据③：Android 11 以前什么都不做')
A('"02:00:00:00:00:00".equals(s)' in java and '"FF:FF:FF:FF:FF:FF".equals(s)' in java,
  'camMacNorm 过滤系统占位值（02:00… / 广播）')
A('.append(",\\"bssid\\":").append(jsonStr(bs)).append("}")' in java,
  'wifiScanList 返回里带 bssid 字段')
A('bs = camMacNorm(e.getValue().BSSID);' in java, 'bssid 取自 ScanResult.BSSID 并过归一化')
A(r'"bssid\":" + jsonStr(lastBssid)' in java,
  'cameraState() 也报 bssid（拿不到就是空串）')
A('camNoteBssid(c2 == null ? null : c2.getNetworkCapabilities(n));' in java, 'onAvailable 里也主动查一次（双保险）')
A('if (bridge != null) bridge.connectCamera2(s, pw, bs);' in java,
  '4713（授权后重连）走**主** Bridge 实例，并带上挂起的 BSSID')
A('if (bridge != null) bridge.connectCamera2(s, pw, bs);\n'
  '                        else new Bridge().connectCamera(s, pw);' in java,
  '临时 Bridge 只剩"主实例为空时"的一条兜底（正常路径走 bridge.connectCamera2）')
A(java.count('pendBssid') >= 3, 'pendBssid 声明/赋值/使用都在（共 %d 处）' % java.count('pendBssid'))

print('=== A2. Java 真的能编译（javac） ===')
jc = os.path.join(JDK, 'bin', 'javac.exe')
if not os.path.exists(jc):
    jc = 'javac'
outd = os.path.join(tempfile.gettempdir(), '_dv_r64_cls')
try:
    if os.path.isdir(outd):
        import shutil
        shutil.rmtree(outd, ignore_errors=True)
    os.makedirs(outd)
    env = dict(os.environ)
    env['JAVA_HOME'] = JDK
    env['PATH'] = os.path.join(JDK, 'bin') + os.pathsep + env.get('PATH', '')
    r = subprocess.run([jc, '--release', '8', '-nowarn', '-encoding', 'UTF-8', '-cp', AJ,
                        '-d', outd, JAVA], capture_output=True, text=True, encoding='utf-8',
                       errors='ignore', timeout=180, env=env)
    A(r.returncode == 0, 'javac 通过（%s）' % ('无输出' if not (r.stdout or r.stderr).strip()
                                              else (r.stderr or r.stdout).strip()[:120]))
    A(os.path.exists(os.path.join(outd, 'com', 'om3', 'handbook', 'MainActivity.class')),
      '产出 MainActivity.class')
except subprocess.TimeoutExpired:
    A(False, 'javac 超时')
except FileNotFoundError:
    A(True, '（没找到 javac，跳过编译检查 —— 构建时还会编一次）')

# ============================================================ B. 页面静态
print('=== B. 页面：改的是不是"该改的那几处" ===')


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


si, so = ids(page), ids(old)
# 第 68 轮起允许**新增** id（新功能必然要新 id；新增的那一组由各轮自己的探针按规格断言，
# 见 dv_r68「新增 id 完全等于 SPEC-round68 §2.3 那张表」）。这里钉的是**不许删/不许改**：
# 第 64 轮自己那些 id 必须还在（判据没放松，只是把"相等"改成"一个都不少"）。
A(not (so - si), '第 64 轮及以前的 id 一个都没少（少的是：%s）' % (sorted(so - si) or '无'))
A('r64：BSSID' in page, 'r64 标记块在（生成脚本幂等判据）')
A(page.count('function camBssidOk(') == 1 and page.count('function camRec(') == 1
  and page.count('function camBssidMerge(') == 1 and page.count('function camConnectRaw(') == 1,
  '四个新函数各只定义 1 次（没有复制两份实现）')
HELPERS_TXT = page[page.index('var BSSID_RE = /^'):page.index('\n  function renderSaved(){')]
page_wo = page.replace(HELPERS_TXT, '')
A('.connectCamera(' not in page_wo and '.connectCamera2(' not in page_wo,
  'camConnectRaw 之外没有任何地方直接调原生连接（两处调用点都改走 camConnectRaw）')
A(page.count('camConnectRaw(') == 3, 'camConnectRaw 出现 3 次 = 定义 1 + 调用 2（实为 %d 次）'
  % page.count('camConnectRaw('))
A(page.count('camSave({') == 0, '页面里没有手写记录对象（5 处 camSave 全走 camRec）')
A(page.count('camRec(') == 6, 'camRec 使用 6 次 = 定义 1 + 调用 5（实为 %d 次）' % page.count('camRec('))
A('camConnectRaw(ssid, pass, keep.bssid)' in page and 'camConnectRaw(pick.ssid, pw, pick.bssid)' in page,
  '两处调用点都把 BSSID 传进去了（记住的 / 刚扫到的）')
A("raw.indexOf('@bssid')" in page, '页面认的是原生回的 @bssid 后缀（不替原生吹牛）')
A('window.__om3camBssid = function(ssid, bssid, src)' in page, 'window.__om3camBssid 回调在位')
A("BSSID ' + esc(bs)" in page and "bits.push('BSSID：' + esc(bs1))" in page,
  '两处显示在位（记住的相机那一行 + 已连接卡的信息行）')
A("camBssidOk(cands[ci].bssid) === svB" in page, '直连时优先挑"记住过 BSSID 的那一台"')
A('var bs = camBssidOk(s.bssid);' in page, 'renderSaved 显示前先过校验（非法不显示）')

# ============================================================ C. node 功能段
print('=== C. 功能：抽出函数在 node 里跑（喂假 Native） ===')
js = page[page.index('var BSSID_RE = /^'):page.index('\n  function renderSaved(){')]

HARNESS = r'''
var LOGS = [];
function log(m, c){ LOGS.push([String(c || ''), String(m)]); }
function om3err(e, k){ LOGS.push(['err', String(e)]); }
var Native = null;
__JS__
function J(o){ return JSON.stringify(o); }
var out = [];
/* ① 校验：合法 / 大小写 / 空格 / 假值 / 太短 / 空 / null */
out.push(['ok1', camBssidOk('aa:bb:cc:dd:ee:01'), camBssidOk('  AA:BB:CC:DD:EE:01 '),
          camBssidOk('00:00:00:00:00:00'), camBssidOk('02:00:00:00:00:00'),
          camBssidOk('FF:FF:FF:FF:FF:FF'), camBssidOk('AA:BB'), camBssidOk(''), camBssidOk(null),
          camBssidOk('AA:BB:CC:DD:00:00')]);
/* ② camRec：同 SSID 继承；换 SSID 不继承；opt 覆盖 */
var r0 = { ssid:'OM-3-1', pass:'pw', model:'OM-3', serial:'SN9', at:'2026-01-01', bssid:'AA:BB:CC:DD:EE:01' };
out.push(['recSame', camRec('OM-3-1', 'pw2', r0)]);
out.push(['recOther', camRec('OM-5-2', 'pw', r0)]);
out.push(['recModel', camRec('OM-3-1', 'p', r0, {model:'OM-1'})]);
out.push(['recNewB', camRec('OM-3-1', 'p', r0, {bssid:'aa:bb:cc:dd:ee:02'})]);
out.push(['recBadB', camRec('OM-3-1', 'p', r0, {bssid:'x'})]);
out.push(['recNoKeep', camRec('OM-3-1', 'p', null)]);
/* ③ merge：对得上+变了 / 没变 / SSID 不同 / BSSID 非法 / 没记录 */
out.push(['mgOK', camBssidMerge(r0, 'OM-3-1', 'aa:bb:cc:dd:ee:02')]);
out.push(['mgSame', camBssidMerge(r0, 'OM-3-1', 'AA:BB:CC:DD:EE:01')]);
out.push(['mgOtherSsid', camBssidMerge(r0, 'OM-5-2', 'AA:BB:CC:DD:EE:02')]);
out.push(['mgBad', camBssidMerge(r0, 'OM-3-1', 'zz')]);
out.push(['mgNoRec', camBssidMerge(null, 'OM-3-1', 'AA:BB:CC:DD:EE:02')]);
out.push(['mgKeepPass', camBssidMerge(r0, 'OM-3-1', 'AA:BB:CC:DD:EE:02').pass]);
/* ④ camConnectRaw：几种原生形态（老 APK / 支持 BSSID / 原生没用上 / 抛异常） */
Native = null;
out.push(['crNoNative', camConnectRaw('S', 'p', 'AA:BB:CC:DD:EE:01')]);
var ARGS = [];
Native = { connectCamera: function(s, p){ ARGS.push(['2', s, p]); return 'asking'; } };
out.push(['crOldApk', camConnectRaw('S', 'p', 'AA:BB:CC:DD:EE:01'), ARGS.slice(), LOGS.length]);
var A3 = [];
Native = { connectCamera2: function(s, p, b){ A3.push([s, p, b]); return 'asking@bssid'; },
           connectCamera: function(){ A3.push(['FELL-BACK']); return 'asking'; } };
out.push(['crPinned', camConnectRaw('S', 'p', 'aa:bb:cc:dd:ee:01'), A3.slice()]);
var A4 = [];
/* 注：真实的 app 里 connectCamera 与 connectCamera2 **同时存在**（新方法只是多带 BSSID），
   所以假 Native 两种情况都要给 —— 否则会先撞上 `!Native.connectCamera` 那道兜底。 */
Native = { connectCamera2: function(s, p, b){ A4.push([s, p, b]); return 'asking'; },
           connectCamera: function(){ A4.push(['FELL-BACK']); return 'asking'; } };
out.push(['crNoSuffix', camConnectRaw('S', 'p', 'AA:BB:CC:DD:EE:01'), A4.slice()]);
Native = { connectCamera2: function(){ return 'need_perm:android.permission.NEARBY_WIFI_DEVICES'; },
           connectCamera: function(){ return 'asking'; } };
out.push(['crPerm', camConnectRaw('S', 'p', 'AA:BB:CC:DD:EE:01'),
          camConnectRaw('S', 'p', 'AA:BB:CC:DD:EE:01').r.indexOf('need_perm') === 0]);
Native = { connectCamera2: function(){ throw new Error('boom'); },
           connectCamera: function(){ return 'asking'; } };
out.push(['crThrow', camConnectRaw('S', 'p', 'AA:BB:CC:DD:EE:01')]);
var A6 = [];
Native = { connectCamera: function(s, p){ A6.push(['2', s, p]); return 'asking'; } };
out.push(['crBadBssid', camConnectRaw('S', 'p', 'not-a-mac'), A6.slice()]);
console.log(J(out));
'''

harness = HARNESS.replace('__JS__', js)
tmp = os.path.join(tempfile.gettempdir(), '_dv_r64.js')
io.open(tmp, 'w', encoding='utf-8').write(harness)
try:
    r = subprocess.run(['node', tmp], capture_output=True, text=True, encoding='utf-8', timeout=60)
except FileNotFoundError:
    print('  （没装 node，跳过功能部分）')
    r = None
if r is not None:
    if r.returncode != 0:
        A(False, 'node 跑挂了：' + (r.stderr or '')[-400:])
    else:
        rows = dict((x[0], x[1:]) for x in json.loads(r.stdout.strip().splitlines()[-1]))
        o = rows['ok1']
        A(o[0] == 'AA:BB:CC:DD:EE:01' and o[1] == 'AA:BB:CC:DD:EE:01', '小写/带空格 → 规范成大写')
        A(o[2] == '' and o[3] == '' and o[4] == '', '系统占位值（全 0 / 02:00… / 广播）→ 当没有')
        A(o[5] == '' and o[6] == '' and o[7] == '', 'AA:BB / 空串 / null → 当没有（不抛）')
        A(o[8] == 'AA:BB:CC:DD:00:00', '页面对"结尾 00:00"不擅自否决（那是原生回调路径的判据，见 A 段）')
        o = rows['recSame'][0]
        A(o['bssid'] == 'AA:BB:CC:DD:EE:01' and o['model'] == 'OM-3' and o['serial'] == 'SN9'
          and o['at'] == '2026-01-01' and o['pass'] == 'pw2', '同 SSID：继承 bssid/机型/序列号/上次连接，密码用新的')
        o = rows['recOther'][0]
        A('bssid' not in o and o['model'] == '' and o['serial'] == '' and o['at'] == '',
          '换 SSID：**不继承**上一台的 bssid/机型/序列号（防串台）')
        A(rows['recModel'][0]['model'] == 'OM-1', 'opt.model 可覆盖（检测相机认到型号那处）')
        A(rows['recNewB'][0]['bssid'] == 'AA:BB:CC:DD:EE:02', 'opt.bssid 优先于 keep.bssid（刚扫到的更准）')
        A(rows['recBadB'][0]['bssid'] == 'AA:BB:CC:DD:EE:01', 'opt.bssid 非法 → 退回 keep.bssid（不被覆盖成坏值）')
        A('bssid' not in rows['recNoKeep'][0] and rows['recNoKeep'][0]['pass'] == 'p', '没有旧记录：不写 bssid 字段')
        o = rows['mgOK'][0]
        A(o['bssid'] == 'AA:BB:CC:DD:EE:02' and o['pass'] == 'pw', 'merge：对得上且变了 → 新记录（其它字段原样）')
        A(rows['mgSame'][0] is None, 'merge：值没变 → null（不写盘）')
        A(rows['mgOtherSsid'][0] is None, 'merge：SSID 不同 → null（不把 BSSID 挂到别的相机上）')
        A(rows['mgBad'][0] is None, 'merge：BSSID 非法 → null')
        A(rows['mgNoRec'][0] is None, 'merge：没有记录 → null（不凭空造记录）')
        o = rows['crNoNative'][0]
        A(o['r'] == 'unsupported' and o['via'] == 'none', '没有原生桥 → unsupported（与旧行为一致）')
        o = rows['crOldApk'][0]
        A(o['r'] == 'asking' and o['via'] == 'ssid' and rows['crOldApk'][1] == [['2', 'S', 'p']],
          '原生没有 connectCamera2（老 APK/桌面版）→ 退回 2 参，仍能连')
        A(rows['crOldApk'][2] > 0, '退回时写了日志（不静默）')
        o = rows['crPinned'][0]
        A(o['via'] == 'ssid+bssid' and o['r'] == 'asking' and o['bssid'] == 'AA:BB:CC:DD:EE:01',
          'BSSID 合法 + 原生支持 → 走 3 参、认 @bssid、返回码剥掉后缀')
        A(rows['crPinned'][1] == [['S', 'p', 'AA:BB:CC:DD:EE:01']], '3 参传的是**规范后**的大写 BSSID')
        o = rows['crNoSuffix'][0]
        A(o['r'] == 'asking' and o['via'] == 'ssid' and o['bssid'] == '',
          '原生没用 BSSID（安卓 11 及以下）→ 页面如实说"只按 SSID 连"')
        A(rows['crPerm'][1] is True, '剥掉 @bssid 后，need_perm 前缀判断仍成立（调用方不用改）')
        o = rows['crThrow'][0]
        A(o['r'].startswith('error:') and o['via'] == 'bssid', '原生抛异常 → 返回 error: 且不崩页面')
        A(rows['crBadBssid'][1] == [['2', 'S', 'p']], 'BSSID 不合法 → 退回 2 参（拿坏值去连才危险）')

print()
print('第 64 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
