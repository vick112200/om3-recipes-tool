# -*- coding: utf-8 -*-
"""页面侧：
1) Wi-Fi 状态带缓存（20 秒）——不再每 2.5 秒触发一次定位查询
2) 状态条逻辑修正（原来最后一行会把"已连接"覆盖成"未检测"）
3) 「记住的相机」那一行可以直接点，连接按钮上带 SSID
4) 关掉界面（pagehide/退出）→ 通知原生断开相机、回到原来的 Wi-Fi
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

# ---------- 1+2. statusTick 重写 ----------
i = h.find('  function statusTick(){')
j = h.find('setInterval(statusTick', i)
assert 0 < i < j
NEW = '''  /* 省定位：Wi-Fi 状态带缓存（安卓 12+ 读 SSID 属于定位调用，别每次轮询都查） */
  var _wc = { at: 0, v: {} };
  function wifiCached(force){
    if(!Native || !Native.wifiState) return {};
    var now = Date.now();
    if(force || !_wc.at || (now - _wc.at) > 20000){
      try{ _wc.v = JSON.parse(Native.wifiState() || '{}'); }catch(e){ _wc.v = {}; }
      _wc.at = now;
    }
    return _wc.v;
  }
  window.__om3wifiCached = wifiCached;

  function statusTick(){
    var s = wifiCached(false);
    var ssid = s.ssid || '';
    if(/^<?unknown/i.test(ssid)) ssid = '';
    var isCam = /^(OM-?3|OM-?D|OM-?1|OM-?5)/i.test(ssid);
    var sv = camSaved();
    if(ssid && ((sv && sv.ssid && ssid === sv.ssid) || isCam)){
      if(!document.body.classList.contains('cam-on') && window.__om3setConn) window.__om3setConn(true);
    }
    st('camStWifi', ssid ? ('Wi-Fi：' + ssid) : (s.wifi ? 'Wi-Fi：未连热点' : 'Wi-Fi：关'),
       isCam ? 'ok' : (ssid ? 'warn' : ''));
    /* 相机状态：原生连接 > 检测结果 */
    var cs = {};
    try{ cs = JSON.parse((Native && Native.cameraState) ? (Native.cameraState() || '{}') : '{}'); }catch(e){}
    var t1 = o1.textContent || '';
    var camTxt = '相机：未检测', camCls = '';
    if(cs.connected || document.body.classList.contains('cam-on')){ camTxt = '相机：已连接'; camCls = 'ok'; }
    else if(/相机应答/.test(t1)){ camTxt = '相机：已连上'; camCls = 'ok'; }
    else if(/失败|连不上/.test(t1)){ camTxt = '相机：连不上'; camCls = 'warn'; }
    st('camStCam', camTxt, camCls);
    st('camStBak', document.getElementById('camDl').disabled ? '备份：无' : '备份：已有',
       document.getElementById('camDl').disabled ? '' : 'ok');
  }
'''
h = h[:i] + NEW + h[j:]

# ---------- wifiRefresh 用缓存（强制刷新那一次） ----------
old_wf = """    var st = {};
    try{ st = JSON.parse(Native.wifiState() || '{}'); }catch(e){}"""
assert h.count(old_wf) == 1
h = h.replace(old_wf, """    var st = wifiCached(true);""", 1)

# ---------- 3. 记住的相机那一行可点 ----------
old_rs = """      el.innerHTML = '记住的相机：<b>' + esc(s.ssid) + '</b>' + (s.pass ? '（密码已存）' : '（没存密码）');"""
assert h.count(old_rs) == 1
h = h.replace(old_rs, """      el.innerHTML = '记住的相机：<b>' + esc(s.ssid) + '</b>' + (s.pass ? '（密码已存）' : '（没存密码）') +
        '　<span style="color:#8fd8c2">点这一行直接连 →</span>';""" , 1)

old_rs2 = """  function camOut(msg, cls){ line(document.getElementById('camConnectOut'), msg, cls); }"""
assert h.count(old_rs2) == 1
h = h.replace(old_rs2, """  function camOut(msg, cls){ line(document.getElementById('camConnectOut'), msg, cls); }
  function bindSavedRow(){
    var el = document.getElementById('camSaved');
    if(!el) return;
    el.style.cursor = 'pointer';
    el.onclick = function(){ var s = camSaved(); if(s && s.ssid) connectNow(); };
    var cb = document.getElementById('camConnect');
    var s2 = camSaved();
    if(cb) cb.textContent = (s2 && s2.ssid) ? ('连接 ' + s2.ssid) : '连接相机';
  }""", 1)
old_rs3 = """    } else {
      el.textContent = '还没记住相机：扫一次二维码，或手动填 SSID / 密码后点「记住它」。';
    }"""
assert h.count(old_rs3) == 1
h = h.replace(old_rs3, old_rs3 + """
    bindSavedRow();""", 1)

# ---------- 4. 关掉界面 → 断开 ----------
old_end = """  setConn(false);"""
assert h.count(old_end) == 1
h = h.replace(old_end, """  setConn(false);
  /* 关界面/退出 → 断开相机热点，回到原来的 Wi-Fi（跟官方 app 一样） */
  function dropCam(){ try{ if(Native && Native.dropCamera) Native.dropCamera(); }catch(e){} }
  window.addEventListener('pagehide', dropCam);
  window.addEventListener('beforeunload', dropCam);
  document.addEventListener('visibilitychange', function(){
    if(!document.hidden){ wifiCached(true); statusTick(); }
  });""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：缓存 Wi-Fi 状态 / 状态条修正 / 记住的相机可点 / 退出断开')
