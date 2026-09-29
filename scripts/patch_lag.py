# -*- coding: utf-8 -*-
"""卡死硬化：状态轮询不再做任何跨语言(JS↔Java)调用
- 同步桥调用会卡住 JS 线程（某些 ROM 上读 Wi-Fi 状态很慢）→ 轮询里一律不调
- 轮询改成 5 秒、页面不可见时不动、加防重入
- 相机模块整体 try/catch + 全局错误写进日志
- 扫码 90 秒自动收工，页面隐藏时停
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- 1. 轮询：不调桥 ----------
i = h.find('  function statusTick(){')
j = h.find('setInterval(statusTick', i)
assert 0 < i < j
NEW = '''  var _tickBusy = false;
  function statusTick(){
    if(_tickBusy) return;                 /* 防重入 */
    _tickBusy = true;
    try{
      var s = _wc.v || {};                /* 只用缓存，绝不在这里调原生（同步桥调用会卡住 JS） */
      var ssid = s.ssid || '';
      if(/^<?unknown/i.test(ssid)) ssid = '';
      var isCam = /^(OM-?3|OM-?D|OM-?1|OM-?5)/i.test(ssid);
      st('camStWifi', ssid ? ('Wi-Fi：' + ssid) : (s.wifi ? 'Wi-Fi：未连热点' : 'Wi-Fi：—'),
         isCam ? 'ok' : (ssid ? 'warn' : ''));
      var camTxt = '相机：未检测', camCls = '';
      var t1 = o1.textContent || '';
      if(_camOn){ camTxt = '相机：已连接'; camCls = 'ok'; }
      else if(/相机应答/.test(t1)){ camTxt = '相机：已连上'; camCls = 'ok'; }
      else if(/失败|连不上/.test(t1)){ camTxt = '相机：连不上'; camCls = 'warn'; }
      st('camStCam', camTxt, camCls);
      st('camStBak', document.getElementById('camDl').disabled ? '备份：无' : '备份：已有',
         document.getElementById('camDl').disabled ? '' : 'ok');
    }catch(e){ }
    _tickBusy = false;
  }
'''
h = h[:i] + NEW + h[j:]

# ---------- 2. 轮询频率 & 可见性 ----------
old_iv = 'setInterval(statusTick, 2500);'
assert h.count(old_iv) == 1
h = h.replace(old_iv, '''setInterval(function(){ if(!document.hidden) statusTick(); }, 5000);''', 1)

# ---------- 3. 只读缓存 + 节流 ----------
old_wc = '''  var _wc = { at: 0, v: {} };
  function wifiCached(force){
    if(!Native || !Native.wifiState) return {};
    var now = Date.now();
    if(force || !_wc.at || (now - _wc.at) > 20000){
      try{ _wc.v = JSON.parse(Native.wifiState() || '{}'); }catch(e){ _wc.v = {}; }
      _wc.at = now;
    }
    return _wc.v;
  }'''
assert h.count(old_wc) == 1
NEW_WC = '''  var _wc = { at: 0, v: {} };
  /* 只有"明确要看一眼状态"时才调原生；同一秒内的重复请求直接吃缓存（同步桥调用会卡 JS 线程） */
  function wifiCached(force){
    if(!Native || !Native.wifiState) return _wc.v || {};
    var now = Date.now();
    if(force && (now - _wc.at) < 1500) force = false;
    if(force || !_wc.at){
      var t0 = Date.now();
      try{ _wc.v = JSON.parse(Native.wifiState() || '{}'); }catch(e){ _wc.v = _wc.v || {}; }
      _wc.at = Date.now();
      if(Date.now() - t0 > 400) log('Wi-Fi 状态读取偏慢：' + (Date.now() - t0) + 'ms', 'warn');
    }
    return _wc.v || {};
  }'''
h = h.replace(old_wc, NEW_WC, 1)

# ---------- 4. _camOn 标记（供轮询使用，不再调 cameraState） ----------
old_flag = '  function setConn(on){\n    document.body.classList.toggle(\'cam-on\', !!on);'
assert h.count(old_flag) == 1
h = h.replace(old_flag, '  var _camOn = false;\n  function setConn(on){\n    _camOn = !!on;\n    document.body.classList.toggle(\'cam-on\', !!on);', 1)

# ---------- 5. 相机模块整体 try/catch + 全局错误入日志 ----------
old_head = "  if(!App) return;                                  /* 桌面版没有这个页签 */"
assert h.count(old_head) == 1
h = h.replace(old_head, old_head + '''

  /* 任何未捕获的错误都写进日志（避免"页面卡死/没反应却查不到原因"） */
  window.addEventListener('error', function(ev){
    try{ log('页面错误：' + (ev.message || '') + ' @' + (ev.lineno || '?'), 'err'); }catch(e){}
  });''', 1)

# ---------- 6. 扫码 90 秒自动收工 + 页面隐藏时停 ----------
old_end = '  setConn(false);\n  /* 关界面/退出 → 断开相机热点'
assert h.count(old_end) == 1
h = h.replace(old_end, '''  setConn(false);
  /* 扫码别一直开着：90 秒自动收工；页面切走也停（省电、避免看着像"卡住"） */
  setInterval(function(){
    if(scanStream && scanStartedAt && (Date.now() - scanStartedAt > 90000)){
      stopScan();
      camOut('扫码等太久，已经关掉了。再点一次「扫二维码」或直接手动填。', 'warn');
    }
  }, 5000);
  document.addEventListener('visibilitychange', function(){
    if(document.hidden && scanStream){
      stopScan();
      camOut('切到后台，扫码已关闭。', 'warn');
    }
  });
  /* 关界面/退出 → 断开相机热点''', 1)

old_ss = '  function startScanNow(){\n    pendingScan = false;'
assert h.count(old_ss) == 1
h = h.replace(old_ss, '  function startScanNow(){\n    pendingScan = false;\n    scanStartedAt = Date.now();', 1)
old_var = '  var scanRAF = null, scanStream = null, scanWatch = null;'
if h.count(old_var) == 1:
    h = h.replace(old_var, '  var scanRAF = null, scanStream = null, scanWatch = null, scanStartedAt = 0;', 1)
else:
    h = h.replace('  var scanWatch = null;', '  var scanWatch = null, scanStartedAt = 0;', 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('卡死硬化完成，base.html %.1f KB（+%d 字节）' % (len(h.encode('utf-8')) / 1024, len(h) - n0))
