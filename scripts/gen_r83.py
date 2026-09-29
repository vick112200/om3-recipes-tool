# -*- coding: utf-8 -*-
"""第 83 轮：真机日志（2026-09-29 00:19，**v3.34**）暴露的新问题

好消息（第 82 轮的修复在真机上生效了）：
  · `② 观察窗开始：最多 45 秒…` + `（唤醒帧已发出 → 观察窗从现在开始计时）` → 新窗口/新计时都在；
  · `相机没回应答（5 秒）—— 它本来就不回 ACK（真机证实，正常），**继续等热点**…`
    → **第 82 轮修的"抢结论"没了**（再也不喊"没能把相机唤醒"）；
  · `蓝牙断开：连接断开（status=8）　（8 = 连接超时：相机切到传输态 / 走远 / 关机都可能）` → 码写成人话了。

新问题（本轮修）：
  1. **`期间在第 28、NaN 秒`** —— `CV_PROBE_AT.shift()` 把常量数组吃掉了（第二次开窗时 `[1]` 是 undefined）。
  2. **`"等新结果"的扫描没等到系统给新结果`**：真机 2 秒内就返回 fresh=false —— 说明 `startScan()`
     在安卓 16/targetSdk 34 上**直接返回 false**（不是"等不到广播"）。得把**原因**记下来（why），
     并且发起扫描失败时**再试一次**（常见原因是"上一次扫描还在进行"）。
  3. 窗口白开：`00:18:54` 重发时 `唤醒已经在跑了，不重复发` → **帧没发出去，窗口却重开了 45 秒**；
     之后每次点②都回 `② 正在连蓝牙（还没发帧）—— 连上就会自动发，稍等`（其实早就连上了，是上次的等应答没跑完）。
  4. 最重要的：**"相机到底开没开 Wi-Fi"我这边判不了** —— 真机上扫描拿不到新结果，而这次日志里
     **没有点③**（连一次才是唯一不依赖扫描的判据）。所以：① 收尾文案改成"**连一次才是判据**，点③"；
     ② 加两个**回答键**（相机屏幕亮了/没反应）→ 你的观察直接进日志（第 77 轮那套做法）。

用法：python scripts/gen_r83.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
MARK = 'r83：'
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
J_OLD = '''            boolean started = false;
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
        }'''

J_NEW = '''            boolean started = tryScan(wm);
            /* r83：真机（安卓 16 / targetSdk 34）上 `startScan()` 常常**直接返回 false** ——
               最常见的原因是"上一次扫描还没结束"（系统里正在扫）。所以隔 1.2 秒再试一次，
               比"直接放弃、拿缓存冒充新结果"强。 */
            if (!started && reg) {
                try { Thread.sleep(1200); } catch (Throwable t) { }
                started = tryScan(wm);
            }
            boolean got = false;
            if (started && reg) {
                try { got = latch.await(timeoutMs, java.util.concurrent.TimeUnit.MILLISECONDS); }
                catch (Throwable t) { got = false; }
            }
            if (reg) { try { getApplicationContext().unregisterReceiver(rx); } catch (Throwable t) { } }
            /* r83：把"为什么没拿到新结果"说清楚（真机日志里这样才判得出是限流、还是系统不让扫、还是 Wi-Fi 关着）：
                 ok / register_failed / startScan_false / no_broadcast */
            String why = got ? "ok"
                    : (!reg ? "register_failed" : (!started ? "startScan_false" : "no_broadcast"));
            String list = scanListJson(wm);
            return "{\\"fresh\\":" + got + ",\\"why\\":" + jsonStr(why) + ",\\"ms\\":" + timeoutMs + ",\\"list\\":"
                 + ((list.length() > 0 && list.charAt(0) == '[') ? list : "[]") + "}";
        }

        private boolean tryScan(WifiManager wm) {
            try { return wm.startScan(); } catch (Throwable t) { return false; }
        }'''

J_ANCHOR2 = '''            if (wm == null) return "{\\"fresh\\":false,\\"ms\\":0,\\"list\\":[]}";
            if (!wm.isWifiEnabled()) return "err:wifi_off";
            final java.util.concurrent.CountDownLatch latch'''

J_ANCHOR2_NEW = '''            if (wm == null) return "{\\"fresh\\":false,\\"why\\":\\"no_wifi_manager\\",\\"ms\\":0,\\"list\\":[]}";
            if (!wm.isWifiEnabled()) return "err:wifi_off";
            final java.util.concurrent.CountDownLatch latch'''


@jstep('J1 wifiScanWaitJson：说清"为什么没拿到新结果"（why）＋ startScan 返回 false 时隔 1.2 秒再试一次')
def j1_why(java):
    assert java.count(J_OLD) == 1, 'wifiScanWaitJson 里那段没找到'
    java = java.replace(J_OLD, J_NEW, 1)
    assert java.count(J_ANCHOR2) == 1, 'no_wifi_manager 那行没找到'
    return java.replace(J_ANCHOR2, J_ANCHOR2_NEW, 1)


# ============================================================ 页面

# P1：探测点数组不许被 shift 改掉（NaN 的根因）+ 区分"上次的帧还在等应答"
P_VARS_OLD = "  var _cvProbeCb = null, _cvProbeBusy = false, _cvFreshNone = 0, _cvFrameSaid = false;"
P_VARS_NEW = ("  var _cvProbeCb = null, _cvProbeBusy = false, _cvFreshNone = 0, _cvFrameSaid = false;\n"
              "  var _cvProbeAt = [];     /* STEPS_MARK每次开窗都从 CV_PROBE_AT **复制**一份 —— "
              "直接 shift() 常量数组会让第二次开窗打印出「NaN 秒」（真机日志 00:18:52 抓到） */")

P_INTRO_OLD = """    camCvSay('② 观察窗开始：最多 ' + (CAM_CV_WAKE_MS / 1000) + ' 秒（相机会进传输态、屏幕会亮）。'
      + '期间在第 ' + (CV_PROBE_AT[0] / 1000) + '、' + (CV_PROBE_AT[1] / 1000)
      + ' 秒各做一次"等新结果"的扫描（拿不到新结果会如实说，不当"没开"）…');"""
P_INTRO_NEW = """    _cvProbeAt = CV_PROBE_AT.slice();          /* STEPS_MARK：每次开窗都复制一份（见 _cvProbeAt 声明） */
    camCvSay('② 观察窗开始：最多 ' + (CAM_CV_WAKE_MS / 1000) + ' 秒（相机会进传输态、屏幕会亮）。'
      + (_cvProbeAt.length ? ('期间在第 ' + _cvProbeAt.map(function(x){ return x / 1000; }).join('、')
                              + ' 秒各做一次"等新结果"的扫描') : '')
      + '（拿不到新结果会如实说原因，不当"没开"）…');"""

P_TICK_COND_OLD = "        if(!hs && !_cvProbeBusy && _cvFrameSaid && CV_PROBE_AT.length && waited >= CV_PROBE_AT[0]){\n          var at = CV_PROBE_AT.shift();"
P_TICK_COND_NEW = "        if(!hs && !_cvProbeBusy && _cvFrameSaid && _cvProbeAt.length && waited >= _cvProbeAt[0]){\n          var at = _cvProbeAt.shift();"

P_PROBE_MSG_OLD = """              if(!info.fresh){
                _cvFreshNone++;
                camCvSay('（"等新结果"的扫描没等到系统给新结果 —— 安卓前台限额约 4 次/2 分钟，'
                  + '这**不代表**相机没开）', 'warn');
                return;
              }"""
P_PROBE_MSG_NEW = """              if(!info.fresh){
                _cvFreshNone++;
                camCvSay('（"等新结果"的扫描没拿到新结果：' + cvScanWhyText(info.why)
                  + ' —— 这**不代表**相机没开）', 'warn');
                if(info.why === 'wifi_off') camCvSay('（**手机 Wi-Fi 开关是关的** —— 打开 Wi-Fi 再点②）', 'err');
                return;
              }"""

P_WHY_FN_ANCHOR = "  function camListHasCam(list){"
P_WHY_FN = """  /* STEPS_MARK：把原生给的"为什么没拿到新结果"翻成人话（真机日志里一眼看出是限流、还是系统不让扫、还是 Wi-Fi 关着） */
  function cvScanWhyText(w){
    if(w === 'startScan_false')  return '系统不让 App 触发扫描（安卓 13+ 的限额：startScan 直接返回 false，试了两次）';
    if(w === 'no_broadcast')     return '发起了扫描、但系统没回结果广播（被限流/系统吞了）';
    if(w === 'register_failed')  return '注册"扫描结果"广播失败（系统不给这个接收器）';
    if(w === 'wifi_off')         return '**手机的 Wi-Fi 开关是关的**';
    if(w === 'no_wifi_manager')  return '读不到 Wi-Fi 服务';
    return w ? ('系统给的说明：' + w) : '系统没给说明';
  }
"""

P_SCAN_CB_OLD = """    var info = { fresh: false, list: [], ms: 0, id: String(id || '') };
    try{
      var o = JSON.parse(String(raw || '{}') || '{}');
      info.fresh = !!o.fresh; info.ms = Number(o.ms) || 0; info.list = o.list || [];
    }catch(e){ om3err(e, "wifiScanWait"); }"""
P_SCAN_CB_NEW = """    var info = { fresh: false, why: '', list: [], ms: 0, id: String(id || '') };
    try{
      var o = JSON.parse(String(raw || '{}') || '{}');
      info.fresh = !!o.fresh; info.why = String(o.why || ''); info.ms = Number(o.ms) || 0; info.list = o.list || [];
    }catch(e){ om3err(e, "wifiScanWait"); }"""

# P2：发不出帧就别重开窗 / 提示说准
P_SEND_OLD = """  function camCvWake(){
    /* r82：：再点② = **重发一次**（相机可能没收到；真机日志里用户正是想重试，却被"已经在跑了"挡住，
       那是错的）—— 只把"重发"这句话说了，下面的正常发帧路径照走（不复制第二份实现）。
       还在连蓝牙（帧还没发出去）时只提示。 */
    if(_cvWaking && !_cvFrameSaid){
      camCvSay('② 正在连蓝牙（还没发帧）—— 连上就会自动发，稍等', 'warn');
      return;
    }
    if(_cvWaking) camCvSay('② 再发一次「電源ON」（相机可能没收到）—— 观察窗重新计时', 'warn');
    if(BLEON){
      var blk = '';
      try{ blk = blePowerOnBlock(); }catch(e0){ om3err(e0, "silent"); }
      if(blk){ camCvSay('先不发开机帧：' + blk, 'warn'); return; }"""
P_SEND_NEW = """  function camCvWake(){
    /* r83：：再点② = **重发一次**（相机可能没收到）—— 但**只有真能发出去**才重开观察窗。
       ⚠ 真机日志 00:18:54 的教训：上一次的帧还在等 5 秒应答时，重发被 bleAutoWake 挡掉（"唤醒已经在跑了"），
         可观察窗已经重开了 → 白等 45 秒，而且后面每次点②都误报"正在连蓝牙（还没发帧）"。 */
    if(_cvWaking && !_cvFrameSaid){
      if(BLEON) camCvSay('② 上一次发的帧还在等相机应答（最多 5 秒）—— 等它跑完再点②', 'warn');
      else      camCvSay('② 正在连蓝牙（还没发帧）—— 连上就会自动发，稍等', 'warn');
      return;
    }
    if(_cvWaking) camCvSay('② 再发一次「電源ON」（相机可能没收到）—— 观察窗重新计时', 'warn');
    if(BLEON){
      if(_bleWakeRunning){ camCvSay('② 上一次发的那条还在等应答（最多 5 秒）—— 等它跑完再点②（别急）', 'warn'); return; }
      var blk = '';
      try{ blk = blePowerOnBlock(); }catch(e0){ om3err(e0, "silent"); }
      if(blk){ camCvSay('先不发开机帧：' + blk, 'warn'); return; }"""
# P3：收尾文案 → "连一次才是判据"
P_TAIL_OLD = """          camCvSay(CAM_CV_WAKE_MS / 1000 + ' 秒里扫描**没看到相机热点**（'
            + (_cvFreshNone ? ('其中 ' + _cvFreshNone + ' 次系统压根没给新结果，多半被安卓限流；') : '')
            + '**这不等于相机没开** —— 扫描本来就不可靠）。三步走：'
            + '① 看相机屏幕：亮了吗 / 进「传输状态」了吗？没有就确认相机开机、MENU → Wi-Fi/蓝牙 里蓝牙是「开」；'
            + '② **直接点③「连接相机 Wi-Fi」** —— 它用记住的 SSID+BSSID 连，**不依赖扫描**；'
            + '③ 还不行再点一次②（每次都会真发帧），把日志发我', 'warn');"""
P_TAIL_NEW = """          camCvSay(CAM_CV_WAKE_MS / 1000 + ' 秒里扫描**没看到相机热点**（'
            + (_cvFreshNone ? ('其中 ' + _cvFreshNone + ' 次压根没拿到新结果；') : '')
            + '**这不等于相机没开**）。两步走：'
            + '① **看一眼相机屏幕**：亮了 / 进了「传输状态」→ 就在下面按「屏幕亮了」那条（你的回答会进日志）；'
            + '没反应 → 确认相机开机、MENU → Wi-Fi/蓝牙 里蓝牙是「开」，再点一次②。'
            + '② **点③「连接相机 Wi-Fi」** —— 它用记住的 SSID+BSSID 连；'
            + '**"扫不到"不代表没开，连一次才是判据**（连上就说明相机确实开了）', 'warn');
          camCvSay('（补一句为什么：安卓 13+ 对"扫热点"有硬限额，`startScan` 经常直接被系统拒；'
            + '所以我们**只把扫描当参考**，判定靠"能不能连上"。详见日志里的"没拿到新结果："那句）', 'warn');"""
# P4：HTML —— 两个回答键（相机屏幕看到了吗）
P_HTML_OLD = """    <div class="cvnote">每一步都要你点：<b>App 不会自己连蓝牙，也不会自己开相机 Wi-Fi</b>。"""
P_HTML_NEW = """    <!-- STEPS_MARK：②之后"相机开没开"，**我这边从扫描判不了**（安卓 13+ 限额）→ 加两个回答键，
         你的观察直接进日志（第 77 轮那套做法）。"连上③"是机器判据，这两条是人看到的判据。 -->
    <div class="cvbtns" style="margin:2px 0 2px">
      <span style="font-size:11.5px;color:#9aa3b2;display:block;margin:0 0 4px">点了「② 让相机开 Wi-Fi」之后，看一眼相机屏幕：</span>
      <button type="button" class="bigsm" data-tv="cv-seen">屏幕亮了 / 进了「传输状态」</button>
      <button type="button" class="bigsm" data-tv="cv-notseen">相机没反应（屏幕没变）</button>
    </div>
    <div class="cvnote">每一步都要你点：<b>App 不会自己连蓝牙，也不会自己开相机 Wi-Fi</b>。"""

# P5：绑定回答键
P_BIND_OLD = """    cvBind('cv-off',  function(){ camCvOff(); });"""
P_BIND_NEW = """    cvBind('cv-off',  function(){ camCvOff(); });
    /* STEPS_MARK：②之后"相机屏幕看到了什么"—— 你的回答进日志（我这边判不了，扫描不可靠） */
    cvBind('cv-seen', function(){
      camCvSay('【②之后 · 人看到的】相机屏幕**亮了/进了传输状态** → 相机确实执行了开机帧；接下来点③连它', 'ok');
    });
    cvBind('cv-notseen', function(){
      camCvSay('【②之后 · 人看到的】相机**没反应**（屏幕没变）→ 相机没执行开机帧：'
        + '按"唤醒没生效"查（相机有没有开机/蓝牙是不是「开」/相机是不是拒绝了这个连接）', 'warn');
    });"""


@pstep('P1 修 NaN：探测点数组每次开窗复制一份，别 shift 常量')
def p1_nan(html):
    assert html.count(P_VARS_OLD) == 1, '_cvProbeCb 那行没找到'
    html = html.replace(P_VARS_OLD, P_VARS_NEW, 1)
    assert html.count(P_INTRO_OLD) == 1, '观察窗开头那句没找到'
    html = html.replace(P_INTRO_OLD, P_INTRO_NEW, 1)
    assert html.count(P_TICK_COND_OLD) == 1, '轮询里探测条件没找到'
    return html.replace(P_TICK_COND_OLD, P_TICK_COND_NEW, 1)


@pstep('P2 原生的 why 翻成人话 + 扫描结果回调带上 why')
def p2_why(html):
    assert html.count(P_WHY_FN_ANCHOR) == 1, 'camListHasCam 锚点没找到'
    html = html.replace(P_WHY_FN_ANCHOR, P_WHY_FN + P_WHY_FN_ANCHOR, 1)
    assert html.count(P_SCAN_CB_OLD) == 1, '__om3wifiScan 解析那段没找到'
    html = html.replace(P_SCAN_CB_OLD, P_SCAN_CB_NEW, 1)
    assert html.count(P_PROBE_MSG_OLD) == 1, '探测回调里那句没找到'
    return html.replace(P_PROBE_MSG_OLD, P_PROBE_MSG_NEW, 1)


@pstep('P3 发不出帧就别重开窗；提示说准（上次的等应答 / 正在连蓝牙）')
def p3_window(html):
    assert html.count(P_SEND_OLD) == 1, 'camCvWake 那段没找到'
    return html.replace(P_SEND_OLD, P_SEND_NEW, 1)


@pstep('P4 收尾文案：扫描只是参考，"连一次（③）"才是判据')
def p4_tail(html):
    assert html.count(P_TAIL_OLD) == 1, '收尾文案没找到'
    return html.replace(P_TAIL_OLD, P_TAIL_NEW, 1)


@pstep('P5 连接卡加两个回答键（相机屏幕亮了/没反应）')
def p5_html(html):
    assert html.count(P_HTML_OLD) == 1, 'cvnote 锚点没找到'
    assert 'data-tv="cv-seen"' not in html, '已经加过了'
    return html.replace(P_HTML_OLD, P_HTML_NEW, 1)


@pstep('P6 绑定两个回答键')
def p6_bind(html):
    assert html.count(P_BIND_OLD) == 1, 'cvBind(cv-off) 锚点没找到'
    return html.replace(P_BIND_OLD, P_BIND_NEW, 1)


@pstep('P7 顺手把上一轮 marker 替换留下的「r82：：」双冒号改成单冒号')
def p7_colon(html):
    n = html.count('r82：：')
    assert n >= 1, '没找到 r82：：'
    return html.replace('r82：：', 'r82：')


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
    for once in ('public String wifiScanWaitAsync(final int timeoutMs)', 'private boolean tryScan(WifiManager wm)',
                 'public String wifiScanList()'):
        assert java.count(once) == 1, 'Java 结构自检：`%s` 出现 %d 次' % (once, java.count(once))
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
        print('[r83] 已经是目标状态 —— 不重复改。')
        return 0
    try:
        newj, cj = run_java(java)
        newh, ch = run_page(html)
    except AssertionError as e:
        print('[r83] ✗ %s —— **不写盘**' % e)
        return 1
    dj = len(newj.encode('utf-8')) - len(java.encode('utf-8'))
    dh = len(newh.encode('utf-8')) - len(html.encode('utf-8'))
    if not (0 < dj < 8000) or not (0 < dh < 20000):
        print('[r83] ✗ 体积不对（Java %+d / 页面 %+d）—— **不写盘**' % (dj, dh))
        return 1
    if '--check' in sys.argv:
        print('[r83] --check：Java %d 步 / 页面 %d 步都能跑通（未写盘）' % (len(cj), len(ch)))
        for c in cj + ch:
            print('   · ' + c)
        return 0
    io.open(JAVA, 'w', encoding='utf-8', newline='').write(newj)
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(newh)
    print('[r83] ✓ Java %d 步 + 页面 %d 步：修 NaN / 说清扫描为什么拿不到 / 发不出帧不白开窗 / "连一次才是判据" + 两个回答键'
          % (len(cj), len(ch)))
    print('[r83] Java 净增 %d 字节；页面净增 %d 字节' % (dj, dh))
    return 0


if __name__ == '__main__':
    sys.exit(main())
