# -*- coding: utf-8 -*-
"""第 82 轮：修真机日志（2026-09-28 23:59，v3.33）暴露的两个真问题

真机日志的关键几行（`logs/` 里那份）：
  ✅ `[连接] 进入连接页：**不做任何自动蓝牙动作**…`            → 第 80/81 轮的不变式成立
  ✅ 点① → `发现：📷 BJSA21721 34:90:EA:BE:07:F9` → `已连接(status=0)` → `服务发现完成：3 个服务`
        → `（①只连模式）蓝牙连好了，**没有**发唤醒帧`          → ① 行为与设计一致
  ✅ 点② → `发【唤醒：電源ON】01 01 04 0F 01 01 02 13 00 → ok:sent` → `已发 9 字节 …给 82f949b4-…`
        → **帧真的发出去了**（"能控制相机开 Wi-Fi"的硬证据）
  ❌ 20 秒观察窗里 `没看到相机热点` → 报"没看到相机热点"     → **假失败**（见下）
  ❌ 23:59:10 `没能把相机唤醒。…把**相机蓝牙口令**填上…` 与观察窗**同时**存在 → 需求方又点了一次②被挡

两个真因（都在我这边）：
  ① 原生 `wifiScanList()` = `wm.startScan()` 后**立刻** `getScanResults()` → 拿到的是**上一次**的缓存，
     "刚被唤醒开出来的热点"必然看不到一次；再叠加安卓前台限额（4 次/2 分钟）→ 20 秒窗口基本没机会 → 假失败。
     → 新增**等新结果**的异步扫描 `wifiScanWaitAsync(ms)`（等系统广播 SCAN_RESULTS_AVAILABLE_ACTION），
       拿不到新结果就返回 `fresh:false`，页面**不许**把"未知"当"没开"。
  ② `bleAutoWake()` 等 5 秒应答失败后自下结论（"没能把相机唤醒"+让用户填口令）——而真机结论是
     **相机不回 ACK 但确实会开**。→ ②流程里它不许抢答，结论只由观察窗下。

另外：观察窗 20 秒 → 45 秒；计时从**真正发帧**那刻起；②进行中再点② = **重发一次**（不再只提示）；
③ 有记住的相机时**先按 SSID+BSSID 直连**（不依赖扫描）；断开码写人话（8=超时 / 19=相机主动断开）。

用法：python scripts/gen_r82.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
MARK = 'r82：'      # 幂等判据：这个词只在本轮新加的注释里出现（两个文件都要有）
JSTEPS, PSTEPS = [], []


def jstep(label):
    def deco(fn):
        JSTEPS.append((label, fn))
        return fn
    return deco


def pstep(label):
    def deco(fn):
        PSTEPS.append((label, fn))
        return fn
    return deco


# ============================================================ Java

# wifiScanList() 里"读结果 → 排序 → 拼 JSON"这一段的头尾（要抽成共用的 scanListJson）
J_HEAD = "                java.util.List<android.net.wifi.ScanResult> rs = null;"
J_TAIL = "                return sb.toString();"

J_NEW_METHODS = '''
        /* r82：**等新结果**的异步扫描（页面不被阻塞）。
           ⚠ 上面 wifiScanList() 是"startScan 之后立刻 getScanResults()" —— 拿到的是**上一次**的缓存，
           所以"刚被唤醒开出来的相机热点"它看不到（真机 2026-09-28 23:59 实测：帧发出去了、相机也确实开了，
           界面上却是"没看到相机热点"）。这里 startScan 后**等系统广播** SCAN_RESULTS_AVAILABLE_ACTION
           （最多 timeoutMs）再读结果；拿不到广播（安卓限流 / 系统不给扫）也照常返回，但 fresh=false ——
           页面据此说"这不代表相机没开"，不许拿它当"没开"。
           返回：立刻给请求号（形如 w12）；结果推给页面 window.__om3wifiScan(id, json)：
             {"fresh":true|false,"ms":6000,"list":[{"ssid":…,"level":…,"cam":…,"bssid":…}, …]} */
        @JavascriptInterface
        public String wifiScanWaitAsync(final int timeoutMs) {
            final String id = "w" + (++sReqId);
            POOL.execute(new Runnable() {
                @Override public void run() {
                    String json;
                    try { json = wifiScanWaitJson(timeoutMs); }
                    catch (Throwable t) {
                        json = "{\\"fresh\\":false,\\"ms\\":" + timeoutMs + ",\\"list\\":[],\\"err\\":"
                             + jsonStr(String.valueOf(t.getMessage())) + "}";
                    }
                    jsCall("window.__om3wifiScan&&window.__om3wifiScan(" + jsonStr(id) + "," + json + ")");
                }
            });
            return id;
        }

        private String wifiScanWaitJson(int timeoutMs) {
            WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wm == null) return "{\\"fresh\\":false,\\"ms\\":0,\\"list\\":[]}";
            if (!wm.isWifiEnabled()) return "err:wifi_off";
            final java.util.concurrent.CountDownLatch latch = new java.util.concurrent.CountDownLatch(1);
            final android.content.BroadcastReceiver rx = new android.content.BroadcastReceiver() {
                @Override public void onReceive(android.content.Context c, android.content.Intent i) { latch.countDown(); }
            };
            boolean reg = false;
            try {
                getApplicationContext().registerReceiver(rx,
                        new android.content.IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION));
                reg = true;
            } catch (Throwable t) { reg = false; }
            boolean started = false;
            try { started = wm.startScan(); } catch (Throwable t) { started = false; }
            boolean got = false;
            if (started && reg) {
                try { got = latch.await(timeoutMs, java.util.concurrent.TimeUnit.MILLISECONDS); }
                catch (Throwable t) { got = false; }
            }
            if (reg) { try { getApplicationContext().unregisterReceiver(rx); } catch (Throwable t) { } }
            String list = scanListJson(wm);
            return "{\\"fresh\\":" + got + ",\\"ms\\":" + timeoutMs + ",\\"list\\":"
                 + ((list.length() > 0 && list.charAt(0) == '[') ? list : "[]") + "}";
        }

'''


@jstep('J1 wifiScanList()：把"读结果 → 拼 JSON"抽成共用的 scanListJson(wm)（逻辑一字不改）')
def j1_extract(java):
    i = java.index(J_HEAD)
    # ⚠ 必须从 i **之后**找结尾 —— 这个文件里 `return sb.toString();` 前面还出现在别的方法里
    #   （第 323 行那份），`index(J_TAIL)` 会拿到它 → j<i → 切片反过来把中间一大段复制一遍。
    j = java.index(J_TAIL, i) + len(J_TAIL)
    body = java[i:j]
    # 原样搬进新方法（缩进统一减 4 空格，只是好看；Java 不依赖缩进）
    ded = '\n'.join([(ln[4:] if ln.startswith('    ') else ln) for ln in body.split('\n')])
    java = java[:i] + "                return scanListJson(wm);" + java[j:]
    new_m = ('        /* r82：扫描结果 → JSON（wifiScanList() 与 wifiScanWaitAsync() 共用这一份，不写第二份） */\n'
             '        private String scanListJson(WifiManager wm) {\n' + ded + '\n        }\n\n')
    anchor = '        @JavascriptInterface\n        public String wifiState() {'
    assert java.count(anchor) == 1, 'wifiState 锚点没找到'
    return java.replace(anchor, new_m + anchor, 1)


@jstep('J2 新增 wifiScanWaitAsync() + wifiScanWaitJson()（不动老接口）')
def j2_add(java):
    anchor = '        @JavascriptInterface\n        public String wifiState() {'
    assert java.count(anchor) == 1, 'wifiState 锚点没找到'
    return java.replace(anchor, J_NEW_METHODS.lstrip('\n') + anchor, 1)


# ============================================================ 页面

P_CONST_OLD = """  var CAM_CV_WAKE_MS = 20000;   /* 「②」之后等相机热点出现的上限（真机：相机不回 ACK，只能按热点判成功） */"""
P_CONST_NEW = """  /* STEPS_MARK（真机日志 2026-09-28 23:59 的教训）：
     · 原生 wifiScanList() 是"startScan 后立刻读缓存"→ **永远慢一拍**，看不到刚被开出来的相机热点；
       所以观察窗要用**等新结果**的 wifiScanWaitAsync（拿不到新结果只能说"未知"，不许当"没开"）；
     · 20 秒太短（一次扫描要几秒 + 安卓前台限额 4 次/2 分钟）→ 45 秒；
     · 结论**只有一个出口**（观察窗）；bleAutoWake 不许抢答（它那句"没能把相机唤醒"曾把人带偏）。 */
  var CAM_CV_WAKE_MS = 45000;      /* 观察窗上限 */
  var CV_PROBE_AT = [6000, 28000]; /* 在这两个时间点各做一次"等新结果"的扫描 */
  var CV_PROBE_MS = 6000;          /* 每次最多等 6 秒 */
  var _cvProbeCb = null, _cvProbeBusy = false, _cvFreshNone = 0, _cvFrameSaid = false;"""

P_PROBE_NEW = """  /* STEPS_MARK：**等新结果**的扫描（原生异步，页面不被阻塞）。
     · 这个版本没有该接口（老 APK）→ 回调 null，调用方退回老路；
     · `fresh:false` = 系统没给新结果（安卓限流）→ **未知**，不是"没有"。 */
  window.__om3wifiScan = function(id, raw){
    var cb = _cvProbeCb;
    _cvProbeCb = null; _cvProbeBusy = false;
    if(!cb) return;
    var info = { fresh: false, list: [], ms: 0, id: String(id || '') };
    try{
      var o = JSON.parse(String(raw || '{}') || '{}');
      info.fresh = !!o.fresh; info.ms = Number(o.ms) || 0; info.list = o.list || [];
    }catch(e){ om3err(e, "wifiScanWait"); }
    try{ cb(info); }catch(e2){ om3err(e2, "cv-probe"); }
  };
  function camProbeFresh(ms, cb){
    var N = window.OM3Native;
    if(!N || !N.wifiScanWaitAsync){ cb(null); return false; }   /* 老 APK：让调用方走老路 */
    if(_cvProbeBusy) return false;
    _cvProbeBusy = true; _cvProbeCb = cb;
    try{ N.wifiScanWaitAsync(ms || CV_PROBE_MS); }
    catch(e){ _cvProbeBusy = false; _cvProbeCb = null; cb(null); }
    return true;
  }
  /* 一份扫描结果里"像相机的那个"（原生 cam 标记 / 名字正则 / 记住的那台，三选一） */
  function camListHasCam(list){
    var L = list || [];
    for(var i = 0; i < L.length; i++){
      var o = L[i] || {}, s = String(o.ssid || '');
      if(o.cam || camLookLikeCamera(s) || camIsCameraSsid(s)) return s;
    }
    return '';
  }
  /* ②发帧后由 bleAutoWake 回调 —— 观察窗**从真正发帧那刻**起计时（没连蓝牙时先连要几秒；一次窗口只重置一次） */
  window.__om3cvOnFrame = function(){
    if(!_cvWaking || _cvFrameSaid) return;
    _cvFrameSaid = true;
    _cvWakeAt = Date.now();
    camCvSay('（唤醒帧已发出 → 观察窗从现在开始计时，最多 ' + (CAM_CV_WAKE_MS / 1000) + ' 秒）');
  };
"""

P_WATCH_OLD_HEAD = """  /* 「②」发完帧后的**热点观察窗**：最多等 CAM_CV_WAKE_MS，看到热点=成功、到点=明确失败。
     扫描要省着用：1 秒轮询但只在第 8 秒**强制真扫一次**（r74 的 __om3hotspotForce 就是给"刚唤醒"留的），
     其余轮询只读缓存/当前 SSID —— 不许回到"10 秒扫 20 次"。 */
  function camCvWakeWatch(){
    if(_cvWakeT){ clearInterval(_cvWakeT); _cvWakeT = null; }
    _cvWaking = true; _cvWakeAt = Date.now(); _cvWakeHot = ''; window.__om3cvForced = 0;
    camCvRender();
    camCvSay('② 唤醒帧已发 —— 相机不回 ACK（真机证实），所以按**热点出现**判成功：最多等 '
      + (CAM_CV_WAKE_MS / 1000) + ' 秒…');"""

P_WATCH_NEW_HEAD = """  /* STEPS_MARK：「②」之后的**热点观察窗**（结论的唯一出口）
     · 45 秒；在 CV_PROBE_AT 两个点各做一次"等新结果"的扫描，其余轮询只读当前 SSID（省扫描额度）；
     · 到点**不说"相机没开"**：扫描不可靠 → 说清"这不等于没开" + 指路③（不依赖扫描）。
     扫描要省着用，不许回到"10 秒扫 20 次"。 */
  function camCvWakeWatch(){
    if(_cvWakeT){ clearInterval(_cvWakeT); _cvWakeT = null; }
    /* _cvWakeAt 先按"点按钮"算一个上界；帧真发出去时 __om3cvOnFrame 会把它重置成那一刻
       （没连蓝牙时先连要几秒，不能白算进观察窗）。 */
    _cvWaking = true; _cvWakeHot = ''; _cvWakeAt = Date.now(); _cvFrameSaid = false;
    _cvProbeCb = null; _cvProbeBusy = false; _cvFreshNone = 0;
    camCvRender();
    camCvSay('② 观察窗开始：最多 ' + (CAM_CV_WAKE_MS / 1000) + ' 秒（相机会进传输态、屏幕会亮）。'
      + '期间在第 ' + (CV_PROBE_AT[0] / 1000) + '、' + (CV_PROBE_AT[1] / 1000)
      + ' 秒各做一次"等新结果"的扫描（拿不到新结果会如实说，不当"没开"）…');"""

P_TICK_OLD = """    _cvWakeT = setInterval(function(){
      try{
        var waited = Date.now() - _cvWakeAt;
        if(waited >= 8000 && !window.__om3cvForced){
          window.__om3cvForced = 1;
          try{ if(window.__om3hotspotForce) window.__om3hotspotForce(); }catch(e1){ om3err(e1, "silent"); }
        }
        var hs = false;
        try{ hs = camHotspotVisible(); }catch(e2){ om3err(e2, "silent"); }
        var v = camCvWakeVerdict(hs, waited, CAM_CV_WAKE_MS);"""

P_TICK_NEW = """    _cvWakeT = setInterval(function(){
      try{
        var waited = _cvWakeAt ? (Date.now() - _cvWakeAt) : 0;
        var hs = false;
        try{ hs = camHotspotVisible(); }catch(e2){ om3err(e2, "silent"); }
        /* STEPS_MARK：到点就做一次"等新结果"的扫描（异步；同时在飞的只允许一个）。
           ⚠ 只在**帧真的发出去之后**才开始探测（_cvFrameSaid）—— 没连蓝牙时要先连几秒。 */
        if(!hs && !_cvProbeBusy && _cvFrameSaid && CV_PROBE_AT.length && waited >= CV_PROBE_AT[0]){
          var at = CV_PROBE_AT.shift();
          var started = camProbeFresh(CV_PROBE_MS, function(info){
            try{
              if(!info) return;
              if(!info.fresh){
                _cvFreshNone++;
                camCvSay('（"等新结果"的扫描没等到系统给新结果 —— 安卓前台限额约 4 次/2 分钟，'
                  + '这**不代表**相机没开）', 'warn');
                return;
              }
              var s = camListHasCam(info.list);
              camCvSay('（新扫了一次：' + (info.list || []).length + ' 个热点，像相机的 '
                + (s ? ('1 个 → ' + s) : '0 个') + '）');
              if(s) _cvWakeHot = s;
            }catch(e3){ om3err(e3, "cv-probe-cb"); }
          });
          if(started) camCvSay('（第 ' + (at / 1000) + ' 秒：做一次"等新结果"的扫描，最多 '
            + (CV_PROBE_MS / 1000) + ' 秒…）');
        }
        var v = camCvWakeVerdict(hs || !!_cvWakeHot, waited, CAM_CV_WAKE_MS);"""

P_TIME_OLD = """        }else{
          camCvSay('等了 ' + (CAM_CV_WAKE_MS / 1000) + ' 秒没看到相机热点 —— 相机可能没收到唤醒帧。'
            + '看一眼相机屏幕：亮了吗？没亮就 ① 确认相机开机、MENU → Wi-Fi/蓝牙 里蓝牙是「开」'
            + ' ② 再点一次「② 让相机开 Wi-Fi」③ 还不行把日志发我', 'warn');
        }"""

P_TIME_NEW = """        }else{
          /* STEPS_MARK：**不许把"没看到"当成"没开"**（扫描不可靠）—— 给三条能走的路，并把③点亮 */
          camCvSay(CAM_CV_WAKE_MS / 1000 + ' 秒里扫描**没看到相机热点**（'
            + (_cvFreshNone ? ('其中 ' + _cvFreshNone + ' 次系统压根没给新结果，多半被安卓限流；') : '')
            + '**这不等于相机没开** —— 扫描本来就不可靠）。三步走：'
            + '① 看相机屏幕：亮了吗 / 进「传输状态」了吗？没有就确认相机开机、MENU → Wi-Fi/蓝牙 里蓝牙是「开」；'
            + '② **直接点③「连接相机 Wi-Fi」** —— 它用记住的 SSID+BSSID 连，**不依赖扫描**；'
            + '③ 还不行再点一次②（每次都会真发帧），把日志发我', 'warn');
          try{
            var b3b = camCvBtn('cv-wifi');
            if(b3b){ b3b.style.boxShadow = '0 0 0 3px #d8b45a55';
              setTimeout(function(){ try{ b3b.style.boxShadow = ''; }catch(e6){} }, 6000); }
          }catch(e7){ om3err(e7, "silent"); }
        }"""


@pstep('P1 观察窗常量：45 秒 + 两个"等新结果"的扫描点')
def p1_const(html):
    assert html.count(P_CONST_OLD) == 1, '观察窗常量没找到'
    return html.replace(P_CONST_OLD, P_CONST_NEW, 1)


@pstep('P2 新增：__om3wifiScan 回调 + camProbeFresh + camListHasCam + __om3cvOnFrame')
def p2_probe(html):
    assert html.count(P_CONST_NEW) == 1, '先跑 P1'
    return html.replace(P_CONST_NEW, P_CONST_NEW + '\n' + P_PROBE_NEW, 1)


@pstep('P3 观察窗重写：等新结果 + 计时从发帧起 + 到点不误判')
def p3_watch(html):
    assert html.count(P_WATCH_OLD_HEAD) == 1, '观察窗函数头没找到'
    html = html.replace(P_WATCH_OLD_HEAD, P_WATCH_NEW_HEAD, 1)
    assert html.count(P_TICK_OLD) == 1, '观察窗轮询体没找到'
    html = html.replace(P_TICK_OLD, P_TICK_NEW, 1)
    assert html.count(P_TIME_OLD) == 1, '观察窗超时文案没找到'
    return html.replace(P_TIME_OLD, P_TIME_NEW, 1)


@pstep('P4 bleAutoWake：②流程里不抢结论 + 发帧后回调观察窗')
def p4_nowake_claim(html):
    old = """        _bleAutoRun = false;
        var tip = _bleLastAck"""
    assert html.count(old) == 1, 'bleAutoWake 收尾没找到'
    new = """        _bleAutoRun = false;
        /* STEPS_MARK：②流程里**不许抢结论**（真机日志：这句"没能把相机唤醒"让人以为失败、又点了一次②，
           而观察窗其实还在等）。真机结论是**相机不回 ACK 但确实会开** → 这里只说"没应答"。 */
        if(_cvWaking){
          bleAutoSay('相机没回应答（' + (BLE_AUTO_ACK_MS / 1000) + ' 秒）—— 它本来就不回 ACK（真机证实，正常），'
            + '**继续等热点**…', 'warn');
          return;
        }
        var tip = _bleLastAck"""
    html = html.replace(old, new, 1)
    old2 = "      var hex = bleSendPreset(st.ch, st.sub, '唤醒：' + st.name, st.payload);\n"
    assert html.count(old2) == 1, '发帧那行没找到'
    new2 = (old2 +
            "      try{ if(window.__om3cvOnFrame) window.__om3cvOnFrame(); }catch(e8){ om3err(e8, \"silent\"); }\n")
    return html.replace(old2, new2, 1)


@pstep('P5 ② 进行中再点② = 重发一次（不再只提示"已经在跑"）')
def p5_retry(html):
    old = """  function camCvWake(){
    if(_cvWaking){ camCvSay('② 已经在让相机开 Wi-Fi 了（等热点）—— 要重来先点④「断开全部」', 'warn'); return; }"""
    assert html.count(old) == 1, '②的入口没找到'
    new = """  function camCvWake(){
    /* STEPS_MARK：再点② = **重发一次**（相机可能没收到；真机日志里用户正是想重试，却被"已经在跑了"挡住，
       那是错的）—— 只把"重发"这句话说了，下面的正常发帧路径照走（不复制第二份实现）。
       还在连蓝牙（帧还没发出去）时只提示。 */
    if(_cvWaking && !_cvFrameSaid){
      camCvSay('② 正在连蓝牙（还没发帧）—— 连上就会自动发，稍等', 'warn');
      return;
    }
    if(_cvWaking) camCvSay('② 再发一次「電源ON」（相机可能没收到）—— 观察窗重新计时', 'warn');"""
    return html.replace(old, new, 1)


@pstep('P5b 蓝牙已连这条路：**先开观察窗再发帧**（帧发出时回调把计时重置到那一刻）')
def p5b_order(html):
    old = """      camCvSay('② 蓝牙已连 → 发「電源ON」帧让相机开 Wi-Fi（相机会进传输态、屏幕会亮）…');
      try{ bleAutoWake(); }catch(e1){ camCvSay('发唤醒帧出错：' + e1.message, 'err'); return; }
      camCvWakeWatch(); return;"""
    assert html.count(old) == 1, '②的蓝牙已连分支没找到'
    new = """      camCvSay('② 蓝牙已连 → 发「電源ON」帧让相机开 Wi-Fi（相机会进传输态、屏幕会亮）…');
      camCvWakeWatch();   /* STEPS_MARK：先开窗；帧发出时 __om3cvOnFrame 会把计时重置到那一刻 */
      try{ bleAutoWake(); }catch(e1){ camCvSay('发唤醒帧出错：' + e1.message, 'err'); return; }
      return;"""
    return html.replace(old, new, 1)


@pstep('P6 ③：记住过这台 → 先按 SSID+BSSID 直连（不依赖扫描），扫描只当兜底')
def p6_saved_first(html):
    old = """    function wifi(){
      step('第 2/3 步：扫附近 Wi-Fi，找相机热点…');"""
    assert html.count(old) == 1, 'wifi() 头没找到'
    new = """    function wifi(){
      /* STEPS_MARK：**记住过这台就先用记住的 SSID+BSSID 连** —— 这条不依赖扫描
         （真机：扫描会被安卓限流、误报"没找到像相机的热点"，而按记住的凭据连是稳的）。没记住才去扫。 */
      var sv0 = camSaved() || {};
      if(sv0.ssid){
        step('第 2/3 步：这台相机记过（' + sv0.ssid + (sv0.bssid ? ' + BSSID ' + sv0.bssid : '')
           + '）→ 直接请系统连它（**不依赖扫描**）…', 'ok');
        try{ connectNow(); }catch(e0){ om3err(e0, "silent"); }
        step('已经交给系统了 —— 连上后这里会自动「检测相机」；'
           + '若一直连不上，点下面「扫码连接（忘了密码时用）」最稳（相机屏幕上那个码）');
        watchHttp();
        return;
      }
      step('第 2/3 步：扫附近 Wi-Fi，找相机热点…');"""
    html = html.replace(old, new, 1)

    old2 = """      step('已经交给系统了 —— 连上后这里会自动「检测相机」；'
         + '若一直连不上，点下面「扫码连接（忘了密码时用）」最稳（相机屏幕上那个码）');
      var w = 0;
      var wd = setInterval(function(){"""
    assert html.count(old2) == 1, '看门狗头没找到'
    new2 = """      step('已经交给系统了 —— 连上后这里会自动「检测相机」；'
         + '若一直连不上，点下面「扫码连接（忘了密码时用）」最稳（相机屏幕上那个码）');
      watchHttp();
    }
    /* r67：看门狗 —— 只有 HTTP 真通才报成功（上面两条路都调它） */
    function watchHttp(){
      var w = 0;
      var wd = setInterval(function(){"""
    return html.replace(old2, new2, 1)


@pstep('P7 蓝牙断开码写人话（8=超时 / 19=相机主动断开）')
def p7_lost_hint(html):
    old = "  function bleLostHint("
    assert old not in html, '已经插过了'
    anchor = "      else if(ev === 'lost'){ BLEON = false; window.__om3bleConnOnly = false; bleRec('蓝牙断开：' + a, 'warn'); bleRenderSvc(); }"
    assert html.count(anchor) == 1, 'lost 分支没找到'
    new = "      else if(ev === 'lost'){ BLEON = false; window.__om3bleConnOnly = false; bleRec('蓝牙断开：' + a + bleLostHint(a), 'warn'); bleRenderSvc(); }"
    html = html.replace(anchor, new, 1)
    helper = """  /* STEPS_MARK：GATT 断开码写人话（真机日志里只看得到 status=8/19，看日志的人会误判） */
  function bleLostHint(why){
    var m = /status=(\\d+)/.exec(String(why || ''));
    if(!m) return '';
    if(m[1] === '8') return '　（8 = 连接超时：相机切到传输态 / 走远 / 关机都可能）';
    if(m[1] === '19') return '　（19 = 相机主动断开）';
    if(m[1] === '22') return '　（22 = 手机这边主动断开）';
    if(m[1] === '133') return '　（133 = 安卓这边连接超时/异常）';
    return '';
  }
"""
    a2 = "  function bleSendPreset(ch, sub, label, payload){"
    assert html.count(a2) == 1, 'bleSendPreset 锚点没找到'
    return html.replace(a2, helper + a2, 1)


def run_java(java):
    changed = []
    for label, fn in JSTEPS:
        before = java
        try:
            java = fn(java)
        except (AssertionError, ValueError) as e:
            raise AssertionError('Java 第「%s」步失败：%s' % (label, e or '锚点没找到'))
        if java == before:
            raise AssertionError('Java 这一步什么都没改：' + label)
        changed.append(label)
    # ⚠ 结构自检（这次真踩到过：切片取反 → 文件里多出一整份 wifiScanList/bleState…）
    for once in ('public String wifiScanList()', 'private String scanListJson(WifiManager wm)',
                 'public String wifiScanWaitAsync(final int timeoutMs)',
                 'private String wifiScanWaitJson(int timeoutMs)', 'public String bleState()'):
        assert java.count(once) == 1, 'Java 结构自检：`%s` 出现 %d 次（应为 1）' % (once, java.count(once))
    return java, changed


def run_page(html):
    changed = []
    for label, fn in PSTEPS:
        before = html
        try:
            html = fn(html)
        except (AssertionError, ValueError) as e:
            raise AssertionError('页面第「%s」步失败：%s' % (label, e or '锚点没找到'))
        if html == before:
            raise AssertionError('页面这一步什么都没改：' + label)
        changed.append(label)
    html = html.replace('STEPS_MARK', MARK)
    assert MARK in html
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    java = io.open(JAVA, encoding='utf-8').read()
    if MARK in html and MARK in java:
        print('[r82] 已经是目标状态 —— 不重复改。')
        return 0
    try:
        newj, cj = run_java(java)
        newh, ch = run_page(html)
    except AssertionError as e:
        print('[r82] ✗ %s —— **不写盘**' % e)
        return 1
    # ⚠ 体积兜底：本轮改动应该只有几 KB（这次踩到过"多出一整份代码"→ +36 KB）
    dj = len(newj.encode('utf-8')) - len(java.encode('utf-8'))
    dh = len(newh.encode('utf-8')) - len(html.encode('utf-8'))
    if not (0 < dj < 12000) or not (0 < dh < 20000):
        print('[r82] ✗ 体积不对（Java %+d 字节 / 页面 %+d 字节）—— 多半是切片取反把代码复制了一份，**不写盘**' % (dj, dh))
        return 1
    if '--check' in sys.argv:
        print('[r82] --check：Java %d 步 / 页面 %d 步都能跑通（未写盘）：' % (len(cj), len(ch)))
        for c in cj + ch:
            print('   · ' + c)
        return 0
    io.open(JAVA, 'w', encoding='utf-8', newline='').write(newj)
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(newh)
    print('[r82] ✓ Java %d 步 + 页面 %d 步：等新结果的扫描 / 观察窗 45 秒不误判 / ③优先按记住的凭据连' % (len(cj), len(ch)))
    for old_p, nm in ((os.path.join(ROOT, 'app', 'base.before_r82.html'), '页面'),
                      (os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.before_r82.java'), 'Java')):
        if os.path.exists(old_p):
            b = io.open(old_p, encoding='utf-8').read()
            a = newh if nm == '页面' else newj
            print('[r82] %s 净增 %d 字节' % (nm, len(a.encode('utf-8')) - len(b.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
