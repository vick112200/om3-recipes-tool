# -*- coding: utf-8 -*-
"""第 81 轮（= 第 80 轮·下）：把「连接相机」做成**手动、有状态、能控制相机开 Wi-Fi**

需求方 2026-09-28 原话（本轮的规格来源）：
  「你可不能自动唤醒相机wifi啊…我们也要做成**显示蓝牙已连接**、并且**点击按钮才能控制相机开启wifi**。
    如果……就可以做成**只有在点击传输时再开启wifi传输配方**，因为**相机开启wifi和手机连相机wifi
    并不应该是个随随便便的行为**。你现在先把控制相机开启wifi做好。」

现状（第 80 轮·上做完之后）：进页面/点「连接相机」已经不自动跑蓝牙链了（`dv_r80` A1/A2 断言 `[]`），
但**没有**一个"让相机开 Wi-Fi"的显式按钮，也**没有**状态显示。

本轮做 6 件事（对应 SPEC-round81.md §1 UC-R81-01..06）：
  ① 连接卡加**状态区**（蓝牙 / 相机 Wi-Fi / 手机 Wi-Fi 三行，真实状态 + 颜色）
  ② 加**四个按钮**：① 连接相机蓝牙（只连，不发帧）② 让相机开 Wi-Fi（传输）③ 连接相机 Wi-Fi ④ 断开全部
  ③ 「②」是**唯一**会发「電源ON」帧的地方；发完按"热点出现"判成功（**不等 ACK**）
  ④ ③ 不再白等蓝牙（只有唤醒真的在跑才等）
  ⑤ ④ 断开全部（**不设 `_bleAutoStop`**，否则之后①再也跑不起来）
  ⑥ 保不变式：没有任何自动路径会动相机

不新增 id（新控件用 `data-tv` 选择器，见 SPEC-round81.md §4）；不动 Java / 构建。

用法：python scripts/gen_r81.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r81.html')
MARK = 'r81：手动控制台'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


# ---------------------------------------------------------------- ① CSS
CSS_ANCHOR = ('.camgate .gho{background:#242424;border:1px solid #3a3a3a;color:#ddd;border-radius:9px;'
              'padding:10px 14px;font-size:13.5px;font-family:inherit;cursor:pointer;margin:0 8px 8px 0}')
CSS_NEW = CSS_ANCHOR + '\n' + '''/* STEPS_MARK：状态区 + 四步按钮（每一步都要用户点；App 不自动动相机） */
.cvbox{background:#171717;border:1px solid #303030;border-radius:9px;padding:7px 11px;margin:4px 0 2px;font-size:12px;line-height:1.55;color:#cfd6e0}
.cvbox b{color:#fff}
.cvbox .cvline{margin:0}
.cvbtns{margin:2px 0 2px}
.cvbtns .bigsm{background:#242424;border:1px solid #3a3a3a;color:#ddd;border-radius:9px;padding:9px 12px;font-size:13px;font-family:inherit;cursor:pointer;margin:0 8px 8px 0}
.cvbtns .bigsm.primary{background:#2f8f74;color:#fff;border:0;font-weight:700}
.cvnote{font-size:11.5px;color:#9aa3b2;line-height:1.6;margin:0 0 4px}'''


# ---------------------------------------------------------------- ② HTML
HTML_ANCHOR = '    <button type="button" class="big gho" id="camGateScan">扫码连接（忘了密码时用）</button>'
HTML_NEW = HTML_ANCHOR + '''
    <!-- STEPS_MARK（需求方 2026-09-28：「我们也要做成显示蓝牙已连接、并且点击按钮才能控制相机开启wifi」
         「相机开启 wifi 和手机连相机 wifi 并不应该是个随随便便的行为」）：
         这里是连接卡的「手动控制台」：上面那个大按钮=③ 的快捷方式，下面这四个是**每一步一步来**的入口。
         规矩（探针 dv_r81 逐条断言）：进页面/点①③ 都**不发唤醒帧**；**唯一**会发「電源ON」帧的地方是「②」。
         注意：**不新增 id** —— 新控件一律用 data-tv 选择器（第 75/77 轮的做法）。 -->
    <div class="cvbox" data-tv="cvstate" aria-live="polite">状态读取中…</div>
    <div class="cvbtns">
      <button type="button" class="bigsm" data-tv="cv-ble">① 连接相机蓝牙</button>
      <button type="button" class="bigsm primary" data-tv="cv-wake">② 让相机开 Wi-Fi（传输）</button>
      <button type="button" class="bigsm" data-tv="cv-wifi">③ 连接相机 Wi-Fi</button>
      <button type="button" class="bigsm" data-tv="cv-off">④ 断开全部</button>
    </div>
    <div class="cvnote">每一步都要你点：<b>App 不会自己连蓝牙，也不会自己开相机 Wi-Fi</b>。
      「②」会让相机进入传输态（屏幕会亮、比较费电）—— 用完请点「④ 断开全部」。
      三个按钮各做一件事、互不代劳：① 只连蓝牙（不开 Wi-Fi）② 只让相机开 Wi-Fi ③ 只连手机↔相机 Wi-Fi。</div>'''


# ---------------------------------------------------------------- ③ 控制台 JS
JS_ANCHOR = '  window.__om3camWifiChain = camWifiChain;'
JS_NEW = JS_ANCHOR + '''

  /* ================= STEPS_MARK（状态 + 四步按钮） =================
     需求方 2026-09-28：「你可不能自动唤醒相机wifi啊…我们也要做成**显示蓝牙已连接**、并且
     **点击按钮才能控制相机开启wifi**…因为相机开启wifi和手机连相机wifi并不应该是个随随便便的行为。」
     规矩（写死在这里，探针 dv_r81 逐条断言）：
       · 没有"自动"：进页面 / 点①③ 都不发唤醒帧、不改相机状态；
       · **唯一**会发「電源ON」帧（= 让相机开 Wi-Fi）的地方 = 「② 让相机开 Wi-Fi（传输）」这个按钮
         （蓝牙工具卡里那几个**手动**帧按钮本来就要人点，不算自动）；
       · 状态看得见：蓝牙 / 相机 Wi-Fi / 手机 Wi-Fi(HTTP) 三行各显示真实状态。
     复用而不复制：① 走 camBleAuto(connectOnly) ② 走 camBleAuto / bleAutoWake ③ 走 camWifiChain
                   ④ 走 #camDisconnect 的既有处理器。 */
  var _cvWaking = false, _cvWakeAt = 0, _cvWakeT = null, _cvWakeHot = '';
  var CAM_CV_WAKE_MS = 20000;   /* 「②」之后等相机热点出现的上限（真机：相机不回 ACK，只能按热点判成功） */
  function camCvEl(){ return document.querySelector('[data-tv="cvstate"]'); }
  function camCvBtn(n){ return document.querySelector('[data-tv="' + n + '"]'); }
  function camCvSay(t, cls){
    try{ line($('camGateOut'), t, cls || ''); }catch(e){ om3err(e, "silent"); }
    try{ log('[手动·连接] ' + t, cls || ''); }catch(e2){ om3err(e2, "silent"); }
    try{ camCvRender(); }catch(e3){ om3err(e3, "silent"); }
  }
  /* 「②」的成败判据：**按"相机热点出现"判**，不等 ACK（SPEC-round80-plan.md §1 真机结论）。
     纯函数 —— 探针 dv_r81 直接喂样例（沿用第 67 轮 camWifiBleWait 的做法）。 */
  function camCvWakeVerdict(hotspot, waited, limit){
    if(hotspot) return 'up';
    if(waited >= limit) return 'timeout';
    return '';
  }
  /* 状态区：只读三条链路的真实状态，**不做任何动作** */
  function camCvRender(){
    var box = camCvEl(); if(!box) return;
    var L = [];
    /* ① 蓝牙：App 自己的 GATT 连接（BLEON） + 系统层面看到的（camOsBle） */
    var camConn = [];
    try{
      var osBl = camOsBle() || { conn: [], paired: [] }, cc = osBl.conn || [];
      for(var i = 0; i < cc.length; i++){
        var o1 = cc[i] || {}, n1 = String(o1.name || ''), a1 = String(o1.address || '');
        if(CAMNAME_RE.test(camBleNorm(n1)) || CAMNAME_RE.test(camBleNorm(a1))) camConn.push(n1 || a1 || '（无名）');
      }
    }catch(e1){ om3err(e1, "silent"); }
    if(BLEON){
      L.push('<div class="cvline"><b>蓝牙</b>：<span style="color:#bdf0cf">已连接</span>（'
        + esc(BLENAME || '（相机）') + (BLEMAC ? '　' + esc(BLEMAC) : '') + '）</div>');
    }else if(camConn.length){
      L.push('<div class="cvline"><b>蓝牙</b>：<span style="color:#ffd98a">手机蓝牙连着相机（'
        + esc(camConn.join('、')) + '），但 App 还没连上</span> → 点①</div>');
    }else{
      L.push('<div class="cvline"><b>蓝牙</b>：<span style="color:#9aa3b2">未连接</span>'
        + ' → 点①（相机要开机、蓝牙要开着）</div>');
    }
    /* ② 相机 Wi-Fi */
    var hot = false, cur = '', curCam = false;
    try{ hot = camHotspotVisible(); }catch(e2){ om3err(e2, "silent"); }
    try{ cur = camWifiSsid(); }catch(e3){ om3err(e3, "silent"); }
    try{ curCam = camIsCameraSsid(cur); }catch(e4){ om3err(e4, "silent"); }
    if(_cvWaking){
      L.push('<div class="cvline"><b>相机 Wi-Fi</b>：<span style="color:#ffd98a">开启中…'
        + '（已发「電源ON」，等热点出现）</span></div>');
    }else if(curCam){
      L.push('<div class="cvline"><b>相机 Wi-Fi</b>：<span style="color:#bdf0cf">已开启</span>（'
        + esc(cur) + '）</div>');
    }else if(hot || _cvWakeHot){
      L.push('<div class="cvline"><b>相机 Wi-Fi</b>：<span style="color:#bdf0cf">已开启</span>（'
        + esc(_cvWakeHot || '扫描里看到相机热点') + '）</div>');
    }else{
      L.push('<div class="cvline"><b>相机 Wi-Fi</b>：<span style="color:#9aa3b2">未知 / 还没开</span>'
        + ' → 点②让相机开，或在相机上进入传输状态</div>');
    }
    /* ③ 手机 ↔ 相机（HTTP，= App 说的"已连接"） */
    var onCam = document.body.classList.contains('cam-on'), httpOn = false;
    try{ httpOn = !!_camHTTP; }catch(e5){ om3err(e5, "silent"); }
    if(onCam && httpOn){
      L.push('<div class="cvline"><b>手机 Wi-Fi</b>：<span style="color:#bdf0cf">已连接'
        + '（HTTP 通，可以读/写配方）</span></div>');
    }else if(onCam){
      L.push('<div class="cvline"><b>手机 Wi-Fi</b>：<span style="color:#ffd98a">挂在相机热点上，'
        + '还没确认能通</span> → 点「检测相机」</div>');
    }else{
      L.push('<div class="cvline"><b>手机 Wi-Fi</b>：<span style="color:#9aa3b2">未连</span> → 点③</div>');
    }
    box.innerHTML = L.join('');
  }
  window.__om3cvRender = camCvRender;
  /* 「②」发完帧后的**热点观察窗**：最多等 CAM_CV_WAKE_MS，看到热点=成功、到点=明确失败。
     扫描要省着用：1 秒轮询但只在第 8 秒**强制真扫一次**（r74 的 __om3hotspotForce 就是给"刚唤醒"留的），
     其余轮询只读缓存/当前 SSID —— 不许回到"10 秒扫 20 次"。 */
  function camCvWakeWatch(){
    if(_cvWakeT){ clearInterval(_cvWakeT); _cvWakeT = null; }
    _cvWaking = true; _cvWakeAt = Date.now(); _cvWakeHot = ''; window.__om3cvForced = 0;
    camCvRender();
    camCvSay('② 唤醒帧已发 —— 相机不回 ACK（真机证实），所以按**热点出现**判成功：最多等 '
      + (CAM_CV_WAKE_MS / 1000) + ' 秒…');
    _cvWakeT = setInterval(function(){
      try{
        var waited = Date.now() - _cvWakeAt;
        if(waited >= 8000 && !window.__om3cvForced){
          window.__om3cvForced = 1;
          try{ if(window.__om3hotspotForce) window.__om3hotspotForce(); }catch(e1){ om3err(e1, "silent"); }
        }
        var hs = false;
        try{ hs = camHotspotVisible(); }catch(e2){ om3err(e2, "silent"); }
        var v = camCvWakeVerdict(hs, waited, CAM_CV_WAKE_MS);
        if(!v) return;
        clearInterval(_cvWakeT); _cvWakeT = null; _cvWaking = false; window.__om3cvForced = 0;
        if(v === 'up'){
          /* ⚠ 只有"看着就是相机"的 SSID 才拿出来显示 —— 此刻手机多半还挂在**家里的 Wi-Fi** 上，
             直接 camWifiSsid() 会把"我家WiFi"当成相机热点名（探针 A3e 抓过这个）。 */
          try{ var _hs0 = camWifiSsid() || ''; _cvWakeHot = camIsCameraSsid(_hs0) ? _hs0 : ''; }
          catch(e3){ om3err(e3, "silent"); }
          camCvSay('✅ 相机 Wi-Fi 起来了' + (_cvWakeHot ? '（' + _cvWakeHot + '）' : '')
            + ' —— 现在点③「连接相机 Wi-Fi」', 'ok');
          try{
            var b3 = camCvBtn('cv-wifi');
            if(b3){ b3.style.boxShadow = '0 0 0 3px #2f8f7455';
              setTimeout(function(){ try{ b3.style.boxShadow = ''; }catch(e4){} }, 5000); }
          }catch(e5){ om3err(e5, "silent"); }
        }else{
          camCvSay('等了 ' + (CAM_CV_WAKE_MS / 1000) + ' 秒没看到相机热点 —— 相机可能没收到唤醒帧。'
            + '看一眼相机屏幕：亮了吗？没亮就 ① 确认相机开机、MENU → Wi-Fi/蓝牙 里蓝牙是「开」'
            + ' ② 再点一次「② 让相机开 Wi-Fi」③ 还不行把日志发我', 'warn');
        }
        camCvRender();
      }catch(e6){ om3err(e6, "cv-watch"); }
    }, 1000);
  }
  /* 停掉正在跑的蓝牙链/唤醒/观察窗 —— ⚠ **不许设 _bleAutoStop**（那会让之后的①再也跑不起来） */
  function camCvStopBle(){
    _bleWakeRunning = false;
    _bleAutoRun = false;
    BLEON = false;                      /* 刚命令断开 → 状态区立刻如实变"未连接"（原生随后也会回 lost） */
    window.__om3bleAutoWake = false;
    window.__om3bleConnOnly = false;
    window.__om3bleAutoFound = null;
    window.__om3wakeOnConnect = false;
    try{ _bleAckCb = null; }catch(e0){ om3err(e0, "silent"); }
    try{ bleAutoClearT(); }catch(e1){ om3err(e1, "silent"); }
    try{ if(window.OM3Native && window.OM3Native.bleScanStop) window.OM3Native.bleScanStop(); }catch(e2){ om3err(e2, "silent"); }
    try{ if(window.OM3Native && window.OM3Native.bleDisconnect) window.OM3Native.bleDisconnect(); }catch(e3){ om3err(e3, "silent"); }
  }
  /* ① 只连蓝牙（**不发**唤醒帧） */
  function camCvBle(){
    if(BLEON){ camCvSay('① 蓝牙已经连着了（' + (BLENAME || '相机') + ' ' + (BLEMAC || '') + '）—— 不用重复连', 'ok'); return; }
    camCvSay('① 连接相机蓝牙：权限 → 蓝牙开关 → 只扫相机 → 连上。**只连，不发唤醒帧**（相机 Wi-Fi 不会因此打开）');
    try{ camBleAuto('点①连接相机蓝牙', false, { connectOnly: true }); }
    catch(e){ camCvSay('连蓝牙出错：' + e.message, 'err'); }
  }
  /* ② 让相机开 Wi-Fi（传输）—— **唯一**会发「電源ON」帧的按钮 */
  function camCvWake(){
    if(_cvWaking){ camCvSay('② 已经在让相机开 Wi-Fi 了（等热点）—— 要重来先点④「断开全部」', 'warn'); return; }
    if(BLEON){
      var blk = '';
      try{ blk = blePowerOnBlock(); }catch(e0){ om3err(e0, "silent"); }
      if(blk){ camCvSay('先不发开机帧：' + blk, 'warn'); return; }
      camCvSay('② 蓝牙已连 → 发「電源ON」帧让相机开 Wi-Fi（相机会进传输态、屏幕会亮）…');
      try{ bleAutoWake(); }catch(e1){ camCvSay('发唤醒帧出错：' + e1.message, 'err'); return; }
      camCvWakeWatch(); return;
    }
    camCvSay('② 蓝牙还没连 → 先连蓝牙（扫 → 连），连上后**自动发一次**「電源ON」（只发这一次）…');
    try{ camBleAuto('点②让相机开 Wi-Fi（传输）', false, {}); }
    catch(e2){ camCvSay('连蓝牙出错：' + e2.message, 'err'); return; }
    camCvWakeWatch();
  }
  /* ③ 只连相机 Wi-Fi（不碰蓝牙） */
  function camCvWifi(){
    camCvSay('③ 连相机 Wi-Fi：走正常连接链（直连 → 记住的凭据）。这一步**不碰蓝牙、不会让相机开 Wi-Fi**');
    try{ showStep(1); }catch(e0){ om3err(e0, "silent"); }
    try{ camWifiChain(); }catch(e){ camCvSay('连接链出错：' + e.message, 'err'); }
  }
  /* ④ 断开全部（蓝牙 + 相机 Wi-Fi；**相机那边的 Wi-Fi 不由我们关**） */
  function camCvOff(){
    if(_cvWakeT){ try{ clearInterval(_cvWakeT); }catch(e0){} _cvWakeT = null; }
    _cvWaking = false; _cvWakeHot = '';
    camCvStopBle();
    var d = $('camDisconnect');
    if(d){ try{ d.click(); }catch(e1){ om3err(e1, "cv-off"); } }
    camCvSay('④ 断开全部：相机蓝牙 + 相机 Wi-Fi 都断了（手机回到原来的 Wi-Fi）。'
      + '相机那边的 Wi-Fi 由它自己超时/你在相机上退出传输 —— 我们不擅自去关。', 'ok');
    camCvRender();
  }
  (function(){
    function cvBind(n, fn){
      var b = camCvBtn(n);
      if(b) b.addEventListener('click', fn);
      else log('[手动·连接] 找不到按钮 ' + n + '（页面结构变了？）', 'warn');
    }
    cvBind('cv-ble',  function(){ camCvBle(); });
    cvBind('cv-wake', function(){ camCvWake(); });
    cvBind('cv-wifi', function(){ camCvWifi(); });
    cvBind('cv-off',  function(){ camCvOff(); });
    /* 这四个按钮的处理器就在上面（cvBind → addEventListener）：'cv-ble' 'cv-wake' 'cv-wifi' 'cv-off' */
    try{ camCvRender(); }catch(e){ om3err(e, "cv-render"); }
  })();'''


# ---------------------------------------------------------------- 第 3~7 步（camBleAuto 只连模式）
@step('① 连接卡：插入「状态区 + 四步按钮」（data-tv 选择器，不新增 id）')
def s_html(html):
    assert html.count(HTML_ANCHOR) == 1, 'camGateScan 按钮锚点没找到'
    assert 'data-tv="cvstate"' not in html, '状态区已经插过了'
    return html.replace(HTML_ANCHOR, HTML_NEW, 1)


@step('② CSS：状态区 / 四步按钮样式')
def s_css(html):
    assert html.count(CSS_ANCHOR) == 1, '.camgate .gho 样式锚点没找到'
    return html.replace(CSS_ANCHOR, CSS_NEW, 1)


@step('③ camBleAuto 加第三个参数 opts.connectOnly（只连蓝牙、不发唤醒帧）')
def s_camBleAuto_sig(html):
    old = """  function camBleAuto(why, isResume){
    why = why || '进「连接相机」页';
    var N = window.OM3Native;"""
    assert html.count(old) == 1, 'camBleAuto 签名没找到'
    new = """  function camBleAuto(why, isResume, opts){
    why = why || '进「连接相机」页';
    /* STEPS_MARK：opts.connectOnly = **只连蓝牙**（服务发现完就收口，不发「電源ON」帧）。
       给控制台的「① 连接相机蓝牙」用 —— 让"连蓝牙"和"让相机开 Wi-Fi"分成两次点击。 */
    opts = opts || {};
    var _cvConnectOnly = !!opts.connectOnly;
    var N = window.OM3Native;"""
    return html.replace(old, new, 1)


@step('④ 蓝牙已连时：只连模式直接返回（不发帧）')
def s_camBleAuto_bleon(html):
    old = "    if(BLEON){ bleAutoWake(); return; }          /* 蓝牙已经连着 → 直接发唤醒帧 */"
    assert html.count(old) == 1, 'BLEON 快捷分支没找到'
    new = """    if(BLEON){
      if(_cvConnectOnly){ log('[手动·蓝牙] 蓝牙已经连着了（①只连模式：不重复扫/连，也不发唤醒帧）', 'ok'); return; }
      bleAutoWake(); return;                     /* 蓝牙已经连着 → 直接发唤醒帧 */
    }"""
    return html.replace(old, new, 1)


@step('⑤ 只连模式标记：起链时记下 __om3bleConnOnly')
def s_camBleAuto_flag(html):
    old = "    _bleAutoRun = true; _bleAutoDone = false; _bleAutoConnStarted = false;"
    assert html.count(old) == 1, '起链那段没找到'
    new = (old + "\n    window.__om3bleConnOnly = _cvConnectOnly;   /* STEPS_MARK：只连模式（svc 分支据此收口，不发帧） */")
    return html.replace(old, new, 1)


@step('⑥ 只连模式：连上后不置 __om3bleAutoWake')
def s_tryConn(html):
    old = "      window.__om3bleAutoWake = true;              /* 连上（服务发现完）后由 svc 分支接手发唤醒帧 */"
    assert html.count(old) == 1, 'tryConn 里那行没找到'
    new = "      window.__om3bleAutoWake = !_cvConnectOnly;   /* STEPS_MARK：只连模式不发唤醒帧 */"
    return html.replace(old, new, 1)


@step('⑦ 连接超时那条路：把只连模式标记一起清掉')
def s_timeout(html):
    old = "        _bleAutoRun = false; window.__om3bleAutoWake = false;"
    assert html.count(old) == 1, '超时收尾那行没找到'
    new = "        _bleAutoRun = false; window.__om3bleAutoWake = false; window.__om3bleConnOnly = false;"
    return html.replace(old, new, 1)


@step('⑧ svc 分支：只连模式收口（明确"没有发唤醒帧"）')
def s_svc(html):
    old = """          else if(window.__om3wakeOnConnect){
            window.__om3wakeOnConnect = false;"""
    assert html.count(old) == 1, 'svc 分支的 wakeOnConnect 没找到'
    new = """          else if(window.__om3bleConnOnly){
            /* STEPS_MARK：①「只连蓝牙」模式 —— 到此为止，**不发**唤醒帧 */
            window.__om3bleConnOnly = false;
            _bleAutoRun = false;
            bleRec('（①只连模式）蓝牙连好了，**没有**发唤醒帧 —— 要让相机开 Wi-Fi 请点②', 'ok');
            try{ camCvRender(); }catch(e0){ om3err(e0, "silent"); }
          }
          else if(window.__om3wakeOnConnect){
            window.__om3wakeOnConnect = false;"""
    return html.replace(old, new, 1)


@step('⑨ 蓝牙断开：清掉只连模式标记')
def s_lost(html):
    old = "      else if(ev === 'lost'){ BLEON = false; bleRec('蓝牙断开：' + a, 'warn'); bleRenderSvc(); }"
    assert html.count(old) == 1, 'lost 分支没找到'
    new = "      else if(ev === 'lost'){ BLEON = false; window.__om3bleConnOnly = false; bleRec('蓝牙断开：' + a, 'warn'); bleRenderSvc(); }"
    return html.replace(old, new, 1)


@step('⑩ 状态区跟着既有的 3.5 秒刷新（camLinkRender 末尾带一下）')
def s_render_hook(html):
    old = """    out.innerHTML = L.join('<br>');
  }
  window.__om3camLink = camLinkRender;"""
    assert html.count(old) == 1, 'camLinkRender 尾部没找到'
    new = """    out.innerHTML = L.join('<br>');
    /* STEPS_MARK：手动控制台的状态区跟着这条既有刷新走（同一份真实状态，不另开定时器） */
    try{ camCvRender(); }catch(e9){ om3err(e9, "cv-render"); }
  }
  window.__om3camLink = camLinkRender;"""
    return html.replace(old, new, 1)


@step('⑪ ③ 不再白等：只有唤醒/蓝牙链真的在跑才等热点')
def s_chain_wait(html):
    old = """      if(!blePossible){
        step('（这台设备没有蓝牙接口）→ 直接试 Wi-Fi', 'warn');
        wifi(); return;
      }"""
    assert html.count(old) == 1, 'camWifiChain 里 blePossible 那段没找到'
    new = old + """
      /* STEPS_MARK：现在**没有**在唤醒相机 → 不再白等（第 74 轮的坑：干等 10 秒像卡住）。
         "等热点"只在唤醒真的在跑时才有意义。 */
      if(!_bleWakeRunning && !_bleAutoRun){
        step('（现在没有在唤醒相机 → 不等了，直接试 Wi-Fi）', 'warn');
        wifi(); return;
      }"""
    return html.replace(old, new, 1)


@step('⑫ 插入控制台 JS（状态渲染 + 四个按钮 + 观察窗 + 只连模式收口）')
def s_js(html):
    assert html.count(JS_ANCHOR) == 1, 'camWifiChain 导出锚点没找到'
    assert 'cvBind(' not in html, '控制台 JS 已经插过了'
    return html.replace(JS_ANCHOR, JS_NEW, 1)


@step('⑬ 文案：把"点「用蓝牙唤醒相机」"改成指向控制台「② 让相机开 Wi-Fi（传输）」')
def s_text(html):
    pairs = [
        ('想让 App 代劳就点下面「用蓝牙唤醒相机」。',
         '想让 App 代劳就点下面「② 让相机开 Wi-Fi（传输）」。'),
        ("或点下面「用蓝牙唤醒相机」让它开", "或点下面「② 让相机开 Wi-Fi（传输）」让它开"),
        ("要相机开 Wi-Fi 请点「用蓝牙唤醒相机」", "要相机开 Wi-Fi 请点「② 让相机开 Wi-Fi（传输）」"),
    ]
    for old, new in pairs:
        assert html.count(old) == 1, '文案锚点没找到（%d 个）：%s' % (html.count(old), old)
        html = html.replace(old, new, 1)
    return html


def run(html):
    changed = []
    for label, fn in STEPS:
        before = html
        try:
            html = fn(html)
        except AssertionError as e:
            raise AssertionError('第「%s」步失败：%s' % (label, e or '锚点没找到'))
        except ValueError as e:
            raise AssertionError('第「%s」步失败（找不到锚点）：%s' % (label, e))
        if html == before:
            raise AssertionError('这一步什么都没改：' + label)
        changed.append(label)
    html = html.replace('STEPS_MARK', MARK)
    assert MARK in html, '标记没插进去'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r81] 已经是目标状态 —— 不重复改。')
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r81] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r81] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r81] ✓ 已改 %d 步：连接卡加「状态区 + 四步按钮」；② 是唯一发「電源ON」帧的按钮' % len(changed))
    if os.path.exists(OLD):
        before = io.open(OLD, encoding='utf-8').read()
        print('[r81] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
