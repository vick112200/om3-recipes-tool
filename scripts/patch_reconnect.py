# -*- coding: utf-8 -*-
"""「记住相机 + 再次连接」的交互补全：
- 原生：connectCamera / disconnectCamera / cameraState（WifiNetworkSpecifier，主动连相机热点，
  相机 HTTP 走这条网络；断开后自动回原来的 Wi-Fi）
- 页面：记住上次的 SSID/密码（localStorage）→ 下次一键「连接相机」，不用再扫
- 扫码成功后自动连接；状态条随连接状态变
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
APK = TMP + r'\apk'
P = TMP + r'\app\base.html'

# ============================================================ 1. Java
p = APK + r'\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()
assert 'connectCamera' not in j
anchor = '        /** 页面要调摄像头扫码时先问这个：ok / need_perm:xxx */'
assert j.count(anchor) == 1
j = j.replace(anchor, open(TMP + r'\bridge_connect.java.txt', encoding='utf-8').read() + anchor, 1)

# camReq 走已连接的相机网络
old_url = '''                java.net.HttpURLConnection c = (java.net.HttpURLConnection)
                        new java.net.URL("http://192.168.0.10/" + path).openConnection();'''
assert j.count(old_url) == 1
j = j.replace(old_url, '''                java.net.URL u = new java.net.URL("http://192.168.0.10/" + path);
                java.net.HttpURLConnection c = (java.net.HttpURLConnection)
                        ((sCamNet != null) ? sCamNet.openConnection(u) : u.openConnection());''', 1)
open(p, 'w', encoding='utf-8', newline='').write(j)
print('MainActivity: connectCamera / disconnectCamera / cameraState 已加；相机 HTTP 走相机网络')

# ============================================================ 2. 页面
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_reconnect.html', 'w', encoding='utf-8', newline='').write(h)

# 2a) 步骤 1 加「连接 / 断开」卡片
anchor = '  <div class="camcard">\n    <div class="camhd">连上了吗？</div>'
assert h.count(anchor) == 1
CARD = '''  <div class="camcard">
    <div class="camhd">连接 / 断开</div>
    <div class="camout" id="camSaved"></div>
    <button type="button" id="camConnect" class="camprimary">连接相机</button>
    <button type="button" id="camDisconnect">断开（回到原来的 Wi-Fi）</button>
    <button type="button" id="camForgetSaved" class="camghost">忘掉这台相机</button>
    <div class="camout" id="camConnectOut">扫过一次之后，这里会记住这台相机 —— 下次直接点「连接相机」就行，不用再扫。
连上后相机的设置写入会走这条连接；点「断开」或退出 app，手机会自动回到原来的 Wi-Fi。</div>
  </div>

'''
h = h.replace(anchor, CARD + anchor, 1)

# 2b) JS：记住 / 连接 / 断开 / 状态
OLD_JS_ANCHOR = "  /* ================= 顶部菜单：3 个步骤 + 日志操作 ================= */"
assert h.count(OLD_JS_ANCHOR) == 1
JS = '''  /* ================= 记住相机 + 再次连接 ================= */
  var CKEY = 'om3cam';
  function camSaved(){ try{ return JSON.parse(localStorage.getItem(CKEY) || 'null'); }catch(e){ return null; } }
  function camSave(o){ try{ localStorage.setItem(CKEY, JSON.stringify(o)); }catch(e){} }
  function camForget(){ try{ localStorage.removeItem(CKEY); }catch(e){} }
  function renderSaved(){
    var s = camSaved(), el = document.getElementById('camSaved');
    if(!el) return;
    if(s && s.ssid){
      el.innerHTML = '记住的相机：<b>' + esc(s.ssid) + '</b>' + (s.pass ? '（密码已存）' : '（没存密码）');
      var a = document.getElementById('camSsid'), b = document.getElementById('camPass');
      if(a && !a.value) a.value = s.ssid;
      if(b && !b.value && s.pass) b.value = s.pass;
    } else {
      el.textContent = '还没记住相机：扫一次二维码，或手动填 SSID / 密码后点「记住它」。';
    }
  }
  function camOut(msg, cls){ line(document.getElementById('camConnectOut'), msg, cls); }
  /* 原生回调：连接状态变化 */
  window.__om3camState = function(state){
    if(state === 'connected'){ camOut('已连上相机热点。', 'ok'); st('camStCam', '相机：已连接', 'ok'); }
    else if(state === 'lost'){ camOut('相机连接断了（相机休眠或走远了）。再点一次「连接相机」即可。', 'warn'); st('camStCam', '相机：已断开', 'warn'); }
    else if(state === 'unavailable'){ camOut('系统没能连上这个热点：确认相机 Wi-Fi 开着、就在旁边；也可以去系统 Wi-Fi 列表里手动选它。', 'err'); }
    var so = document.getElementById('camOut1');
    if(state === 'connected'){ o1.innerHTML = ''; line(o1, '手机已连上相机热点，可以点「检测相机」。', 'ok'); }
    else if(so && state === 'lost'){ /* 保留日志 */ }
  };
  function connectNow(){
    var s = camSaved() || {};
    var a = document.getElementById('camSsid'), b = document.getElementById('camPass');
    var ssid = ((a && a.value) || s.ssid || '').trim();
    var pass = ((b && b.value) || s.pass || '').trim();
    if(!ssid){ camOut('先扫二维码，或把 SSID 填上。', 'warn'); return; }
    if(!Native || !Native.connectCamera){ camOut('这个版本没有原生能力（桌面版页面）。', 'warn'); return; }
    camSave({ ssid: ssid, pass: pass });
    renderSaved();
    camOut('正在请系统连接 ' + ssid + ' …（如果弹窗，请点「连接」）');
    var r = '';
    try{ r = String(Native.connectCamera(ssid, pass)); }catch(e){ r = 'error:' + e.message; }
    if(r === 'asking') camOut('等系统确认中…连上后这里会显示「已连上相机热点」。', 'ok');
    else if(r.indexOf('need_perm') === 0) camOut('先在弹窗里允许「附近的设备 / 位置信息」，然后再点一次「连接相机」。', 'warn');
    else if(r === 'unsupported') camOut('这个安卓版本不支持 app 直接连热点。请打开系统 Wi-Fi 选 ' + ssid + '（密码：' + pass + '）。', 'warn');
    else camOut('没能发起连接（' + r + '）。可以点「打开系统 Wi-Fi 设置」手动连。', 'err');
    statusTick();
  }
  window.__om3connectNow = connectNow;
  document.getElementById('camConnect').addEventListener('click', connectNow);
  document.getElementById('camDisconnect').addEventListener('click', function(){
    try{ if(Native && Native.disconnectCamera) Native.disconnectCamera(); }catch(e){}
    camOut('已断开：手机回到原来的 Wi-Fi。', 'ok');
    st('camStCam', '相机：未连接');
    statusTick();
  });
  document.getElementById('camForgetSaved').addEventListener('click', function(){
    camForget(); renderSaved();
    camOut('已忘掉这台相机（下次要重新扫或手填）。', 'ok');
  });
  renderSaved();

'''
h = h.replace(OLD_JS_ANCHOR, JS + OLD_JS_ANCHOR, 1)

# 2c) 状态条按原生连接状态刷新
OLD_ST = """  function statusTick(){
    if(Native){"""
assert h.count(OLD_ST) == 1
h = h.replace(OLD_ST, """  function statusTick(){
    if(Native && Native.cameraState){
      try{
        var cs = JSON.parse(Native.cameraState() || '{}');
        if(cs.connected) st('camStCam', '相机：已连接', 'ok');
      }catch(e){}
    }
    if(Native){""", 1)

# 2d) 扫码成功后：记住 + 自动连接
OLD_SCAN_END = """    line(host, '密码也读到了。', 'ok');
    joinNow(p.ssid, p.pass);"""
assert h.count(OLD_SCAN_END) == 1
h = h.replace(OLD_SCAN_END, """    line(host, '密码也读到了。', 'ok');
    camSave({ ssid: p.ssid, pass: p.pass });
    renderSaved();
    joinNow(p.ssid, p.pass);          /* 交给系统记住：以后没有别的网时能自动连 */
    setTimeout(function(){ connectNow(); }, 400);   /* 同时主动请系统现在就连上 */""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：记住相机 + 连接/断开 + 扫码后自动连接，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
