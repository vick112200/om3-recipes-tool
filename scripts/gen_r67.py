# -*- coding: utf-8 -*-
"""第 67 轮：「连接相机」连接链的逻辑硬伤修正（第 67 轮复捋出来的 5 处，见 SPEC-round67.md §2.4）。

改前 → 改后（逐条）：
  ① Wi-Fi 链把"蓝牙 GATT 连上"当成"热点已就绪" → 新增纯函数 camWifiBleWait()，
     **BLEON 不再是完成条件**；看到热点/蓝牙链跑完/用户停了/等满 10 秒 才去连 Wi-Fi。
  ② 按钮链和"进页面自动连"同时发 requestNetwork → 按钮链一开始就把自动重试停掉。
  ③ `cam-on` 有两种含义（SSID 像相机 / HTTP 真通），界面却混用 → 新增 `_camHTTP`，
     只有 get_caminfo.cgi 成功才算"HTTP 通"；没确认前不说"已经连着了"，改说"先检测一次确认"。
  ④ Wi-Fi 链步骤编号乱序（2/4 → 4/4 → 3/4）→ 改成 1/3 → 2/3 → 3/3，看门狗不编号。
  ⑤ camBleAuto 的跳过文案谎报"HTTP 通" → 改成 "（HTTP 已确认 / 按 SSID 判断）"。

规矩：幂等（写进页面的标记 `r67：连接链`）+ 每处锚点断言命中恰好 1 次 + 不新增/不改任何 id。

用法：python scripts/gen_r67.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r67：连接链'

EDITS = []


def E(label, old, new):
    EDITS.append((label, old, new))


# ---------------------------------------------------------------- ① + ② + ③ + ④：整段重写 camWifiChain
NEW_CHAIN = '''  /* r67：连接链 —— 等蓝牙链"到什么时候"才去连 Wi-Fi，**纯函数**（探针 dv_r67 直接喂样例）。
     关键：**蓝牙 GATT 连上（BLEON）不算完成** —— 那会儿服务还没发现、唤醒帧还没发、
     相机热点还没起来，这时去连 Wi-Fi 必然失败（这就是"点了一次连接没反应"的老毛病）。
     只有"看到相机热点"或"蓝牙链自己跑完"才算；用户停了/超时也放行（两条链路是独立的）。 */
  function camWifiBleWait(done, stopped, hotspot, waited, limit){
    if(hotspot) return 'hotspot';
    if(done) return 'done';
    if(stopped) return 'stopped';
    if(waited >= limit) return 'timeout';
    return '';
  }
  function camWifiChain(){
    var host = $('camGateOut');
    var said = false;
    function step(t, cls){
      try{ if(host) line(host, t, cls || ''); }catch(e){ om3err(e, "silent"); }
      try{ log('[连接相机] ' + t, cls || ''); }catch(e2){ om3err(e2, "silent"); }
    }
    /* r67：幂等 —— 但分两种说法：真确认过 HTTP 通，才敢说"已经连着了" */
    if(document.body.classList.contains('cam-on')){
      if(_camHTTP){
        step('相机已经连着了（刚检测通），不用再连 —— 要去备份就点右上角 ☰ → 「② 备份设置」。', 'ok');
      } else {
        step('看着已经挂在『' + ((camSaved() || {}).ssid || '相机热点') + '』上了，但还没确认能通 → 先「检测相机」确认一次…', 'warn');
        var b0 = $('camCheck');
        if(b0 && !b0.disabled) b0.click();
        step('（若这一下没检测到：说明那不是相机热点、或相机还没就绪 —— 再点一次「连接相机」）', 'warn');
      }
      return;
    }
    /* r67：按钮这条路一起来，就把「进页面自动连」那条重试停掉 ——
       两条同时发 requestNetwork 会互相顶（跟第 36 轮蓝牙链两条序列交叉跑是同一类问题）。 */
    if(_autoWait || _autoRun){
      _autoWait = false; _autoRun = false;
      if(_autoT){ clearTimeout(_autoT); _autoT = null; }
      try{ renderAuto(); }catch(e){ om3err(e, "silent"); }
      step('先停掉「进页面自动连」的重试（免得两条一起连），这次由按钮来连。');
    }
    step('第 1/3 步：确认蓝牙那条链（它负责让相机开 Wi-Fi）…');
    if(!_bleAutoDone && !_bleAutoStop && !camHotspotVisible()){
      try{ camBleAuto('点「连接相机」'); }catch(e){ om3err(e, "ble-chain"); }
      var waited = 0;
      var wt = setInterval(function(){
        waited += 500;
        var why = camWifiBleWait(_bleAutoDone, _bleAutoStop, camHotspotVisible(), waited, BLE_AUTO_WAIT_MS);
        if(!why) return;
        clearInterval(wt);
        if(why === 'hotspot') step('相机热点已经起来了 → 进 Wi-Fi', 'ok');
        else if(why === 'done') step('蓝牙这条跑完了 → 进 Wi-Fi', 'ok');
        else if(why === 'stopped') step('蓝牙链停了（用户点了停止）→ 不等了，直接连 Wi-Fi', 'warn');
        else step('蓝牙链没在 ' + (BLE_AUTO_WAIT_MS / 1000) + ' 秒内把热点点起来 → 不等了，直接连 Wi-Fi'
                  + '（两条链路是独立的；也可以自己到相机上把 Wi-Fi 打到「Wi-Fi 传输状态」）', 'warn');
        wifi();
      }, 500);
      return;
    }
    wifi();
    function wifi(){
      step('第 2/3 步：扫附近 Wi-Fi，找相机热点…');
      camDirectConnect(function(reason){
        step('第 3/3 步：直连走不通（' + reason + '）→ 改用「记住的凭据」这条路', 'warn');
        connectNow();
      });
      step('已经交给系统了 —— 连上后这里会自动「检测相机」；'
         + '若一直连不上，点下面「扫二维码（第一次）」最稳（相机屏幕上那个码）');
      var w = 0;
      var wd = setInterval(function(){
        w += 1000;
        if(_camHTTP){                                  /* r67：只有真通才报成功 */
          clearInterval(wd);
          if(!said){ said = true; step('✅ 已经连上相机（HTTP 通）—— 正在自动检测…', 'ok'); }
          return;
        }
        if(document.body.classList.contains('cam-on') && !said){
          said = true;
          step('手机这边按 SSID 看已经挂上相机热点了 → 正在确认能不能通（自动「检测相机」）…', 'warn');
        }
        if(w >= 30000){
          clearInterval(wd);
          step((said ? '30 秒了还没确认能通' : '30 秒还没连上')
             + ' → 点下面「扫二维码（第一次）」最稳；或到相机上确认 Wi-Fi 已打到「Wi-Fi 传输状态」', 'warn');
        }
      }, 1000);
    }
  }
'''

E('camWifiChain 整段重写（① ② ③ ④）',
  """  function camWifiChain(){
    var host = $('camGateOut');
    var said = false;
    function step(t, cls){
      try{ if(host) line(host, t, cls || ''); }catch(e){ om3err(e, "silent"); }
      try{ log('[连接相机] ' + t, cls || ''); }catch(e2){ om3err(e2, "silent"); }
    }
    if(document.body.classList.contains('cam-on')){
      step('相机已经连着了，不用再连 —— 要去备份就点右上角 ☰ → 「② 备份设置」。', 'ok');
      return;                                        /* 幂等（官方 既に接続済み） */
    }
    step('第 1/4 步：确认蓝牙那条链（它负责让相机开 Wi-Fi）…');
    if(!BLEON && !_bleAutoDone && !_bleAutoStop){
      try{ camBleAuto('点「连接相机」'); }catch(e){ om3err(e, "ble-chain"); }
      var waited = 0;
      var wt = setInterval(function(){
        waited += 500;
        if(BLEON || _bleAutoDone || _bleAutoStop || waited >= BLE_AUTO_WAIT_MS){
          clearInterval(wt);
          if(waited >= BLE_AUTO_WAIT_MS) step('蓝牙链没在 ' + (BLE_AUTO_WAIT_MS / 1000) + ' 秒内跑完 → 不等了，直接连 Wi-Fi（两条链路是独立的）', 'warn');
          else if(BLEON) step('蓝牙这条好了 → 进 Wi-Fi', 'ok');
          wifi();
        }
      }, 500);
      return;
    }
    wifi();
    function wifi(){
      step('第 2/4 步：扫附近 Wi-Fi，找相机热点…');
      camDirectConnect(function(reason){
        step('第 3/4 步：直连走不通（' + reason + '）→ 改用「记住的凭据」这条路', 'warn');
        connectNow();
      });
      step('第 4/4 步：已经交给系统了 —— 连上后这里会自动「检测相机」；'
         + '若一直连不上，点下面「扫二维码（第一次）」最稳（相机屏幕上那个码）');
      var w = 0;
      var wd = setInterval(function(){
        w += 1000;
        if(document.body.classList.contains('cam-on')){
          clearInterval(wd);
          if(!said){ said = true; step('✅ 已经连上相机（HTTP 通）—— 正在自动检测…', 'ok'); }
        } else if(w >= 30000){
          clearInterval(wd);
          step('30 秒还没连上 → 点下面「扫二维码（第一次）」最稳；或到相机上确认 Wi-Fi 已打到「Wi-Fi 传输状态」', 'warn');
        }
      }, 1000);
    }
  }
""", NEW_CHAIN)

# ---------------------------------------------------------------- ③：_camHTTP（HTTP 真通没通）
E('声明 _camHTTP + 两个置位函数',
  """  var _camOn = false;
  var _autoDetecting = false, _autoAt = 0;""",
  """  var _camOn = false;
  /* r67：cam-on 有两种来源 —— ① 原生网络回调说"SSID 像相机" ② 真的 HTTP 通了。
     界面文案要分得清，所以单独记一个"HTTP 确认过"的标记：**只有 get_caminfo.cgi 成功才置真**。 */
  var _camHTTP = false;
  function camHTTPok(){ _camHTTP = true; }
  function camHTTPbad(){ _camHTTP = false; }
  var _autoDetecting = false, _autoAt = 0;""")

E('检测相机成功 → 标 HTTP 通',
  """        if(window.__om3setConn) window.__om3setConn(true);
      } else {
        line(o1, '相机返回 HTTP ' + r.status + '：' + r.text.slice(0, 200), 'err');""",
  """        if(window.__om3setConn) window.__om3setConn(true);
        /* r67：这是**真的** HTTP 通了（下面 3 秒轮询也会置位） */
        try{ camHTTPok(); }catch(e){ om3err(e, "silent"); }
      } else {
        line(o1, '相机返回 HTTP ' + r.status + '：' + r.text.slice(0, 200), 'err');""")

E('原生报 lost/unavailable/denied → 清 HTTP 通',
  """    else if(state === 'lost' || state === 'unavailable' || state === 'denied'){ if(window.__om3setConn) window.__om3setConn(false); }""",
  """    else if(state === 'lost' || state === 'unavailable' || state === 'denied'){ try{ camHTTPbad(); }catch(e){ om3err(e, "silent"); } if(window.__om3setConn) window.__om3setConn(false); }""")

E('点「断开」→ 清 HTTP 通',
  """  $('camDisconnect').addEventListener('click', function(){
    try{ if(Native && Native.disconnectCamera) Native.disconnectCamera(); }catch(e){ om3err(e, "silent"); }
    camOut('已断开：手机回到原来的 Wi-Fi。', 'ok');""",
  """  $('camDisconnect').addEventListener('click', function(){
    try{ if(Native && Native.disconnectCamera) Native.disconnectCamera(); }catch(e){ om3err(e, "silent"); }
    try{ camHTTPbad(); }catch(e){ om3err(e, "silent"); }   /* r67：断开 = HTTP 不再通 */
    camOut('已断开：手机回到原来的 Wi-Fi。', 'ok');""")

E('点「忘掉这台相机」→ 清 HTTP 通',
  """    renderSaved();
    if(window.__om3setConn) window.__om3setConn(false);
    camOut('已忘掉这台相机：本机记录和系统里记住的热点都撤了（下次要重新扫或手填）。', 'ok');""",
  """    renderSaved();
    try{ camHTTPbad(); }catch(e){ om3err(e, "silent"); }   /* r67 */
    if(window.__om3setConn) window.__om3setConn(false);
    camOut('已忘掉这台相机：本机记录和系统里记住的热点都撤了（下次要重新扫或手填）。', 'ok');""")

E('3 秒轮询：成功置真 / 连续失败置假',
  """        req('get_caminfo.cgi', { timeout: 2500 }).then(function(){
          fail = 0;
        }).catch(function(){
          fail++;
          if(fail >= 2){
            fail = 0;
            log('检测不到相机（可能已关机/退出传输态）→ 标记为未连接', 'warn');
            if(window.__om3setConn) window.__om3setConn(false);
          }
        });""",
  """        req('get_caminfo.cgi', { timeout: 2500 }).then(function(){
          fail = 0;
          try{ camHTTPok(); }catch(e){ om3err(e, "silent"); }   /* r67：这条轮询就是"HTTP 通不通"的探针 */
        }).catch(function(){
          fail++;
          if(fail >= 2){
            fail = 0;
            log('检测不到相机（可能已关机/退出传输态）→ 标记为未连接', 'warn');
            try{ camHTTPbad(); }catch(e){ om3err(e, "silent"); }   /* r67：连续 2 次不通 = HTTP 不通 */
            if(window.__om3setConn) window.__om3setConn(false);
          }
        });""")

E('网络回调说"不像相机热点" → 清 HTTP 通',
  """        /* 关键修复：相机热点消失（关机/退出传输态）→ 明确置为未连接 */
        if(document.body.classList.contains('cam-on') && window.__om3setConn) window.__om3setConn(false);""",
  """        /* 关键修复：相机热点消失（关机/退出传输态）→ 明确置为未连接 */
        if(document.body.classList.contains('cam-on') && window.__om3setConn) window.__om3setConn(false);
        try{ camHTTPbad(); }catch(e){ om3err(e, "silent"); }   /* r67 */""")

# ---------------------------------------------------------------- ⑤：camBleAuto 的跳过文案
E('camBleAuto 跳过文案不再谎报"HTTP 通"',
  """      log('[自动·蓝牙] 相机已经连着了（HTTP 通）→ 不用再连蓝牙（' + why + '）');   /* 幂等（官方 既に接続済み） */""",
  """      log('[自动·蓝牙] 手机已经在相机热点上（' + (_camHTTP ? 'HTTP 已确认' : '按 SSID 判断，还没确认过 HTTP')
          + '）→ 不用再连蓝牙（' + why + '）');   /* 幂等（官方 既に接続済み）；r67：文案不再谎报"HTTP 通" */""")


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r67] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    bad = []
    for label, old, new in EDITS:
        n = html.count(old)
        if n != 1:
            bad.append('%s：锚点命中 %d 次（要求 1 次）' % (label, n))
    if bad:
        print('[r67] ✗ 以下锚点不匹配，页面可能已被改过 —— **不写盘**：')
        for b in bad:
            print('   · ' + b)
        return 1
    if '--check' in sys.argv:
        print('[r67] --check：%d 处锚点都命中 1 次（未写盘）：' % len(EDITS))
        for label, old, new in EDITS:
            print('   · ' + label)
        return 0
    for label, old, new in EDITS:
        html = html.replace(old, new, 1)
    assert MARK in html, '替换后标记不在页面里'
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    print('[r67] ✓ 已改 %d 处：连接链 5 处硬伤（等热点/停自动重连/HTTP 真通标记/步骤编号/文案）' % len(EDITS))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r67.html'), encoding='utf-8').read()
    print('[r67] 页面净增 %d 字节' % (len(html.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
