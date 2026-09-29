# -*- coding: utf-8 -*-
"""三修：
   1) 连接页加"流程说明"（相机需进传输态 → 手机连它的 Wi-Fi）
   2) 状态检测修真实：__om3net 补"断开"分支 + cam-on 时每 3 秒轻量探测相机是否还在线
   3) 扫码不再越扫越卡：画布只设一次 + 降低请求分辨率 + 限制日志写入
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- 1) 连接页流程说明 ----------
anchor_card = None
for cand in ['<div class="camhd">① 连接相机（扫码或手动）</div>', '<div class="camhd">① 连接相机</div>']:
    if h.count(cand) == 1:
        anchor_card = cand
        break
if anchor_card:
    h = h.replace(anchor_card, anchor_card + '''
    <div class="camout" style="border-color:#33507e">
      <b>连接流程（照这个顺序）：</b><br>
      1. 相机上：菜单 → Wi-Fi / 蓝牙 → 把相机切到 <b>Wi-Fi 传输状态</b>（屏幕会显示二维码 / SSID）<br>
      2. 手机：点「扫码连接」扫相机屏幕上的二维码（或手动填 SSID + 密码）<br>
      3. 系统弹窗点「连接」→ 手机会连上相机的热点（此后无需重复）<br>
      4. 连上后这里会显示 <b>OM-3 · 已连接</b>，就可以备份 / 写入配方了<br>
      <span style="color:#d8b45a">注：相机一旦关机或离开传输状态，手机会自动断 —— 状态球会变回"未连接"。</span>
    </div>''', 1)
    print('连接页流程说明已加')
else:
    print('（未找到连接卡片锚点，跳过说明）')

# ---------- 2) 状态检测：断开分支 + 在线探测 ----------
old_net = """      if(o.cam || (ssid && ((sv && sv.ssid && ssid === sv.ssid) || isCam))){
        if(!document.body.classList.contains('cam-on') && window.__om3setConn) window.__om3setConn(true);
      }"""
assert h.count(old_net) == 1, h.count(old_net)
new_net = """      var lookedLikeCam = o.cam || (ssid && ((sv && sv.ssid && ssid === sv.ssid) || isCam));
      if(lookedLikeCam){
        if(!document.body.classList.contains('cam-on') && window.__om3setConn) window.__om3setConn(true);
      } else {
        /* 关键修复：相机热点消失（关机/退出传输态）→ 明确置为未连接 */
        if(document.body.classList.contains('cam-on') && window.__om3setConn) window.__om3setConn(false);
      }"""
h = h.replace(old_net, new_net, 1)

# 在线探测：cam-on 时每 3 秒轻量查一次 caminfo（异步桥，不阻塞）
anchor_ping = "  window.__om3net = function(o){"
assert h.count(anchor_ping) == 1
PING = '''  /* 相机在线探测：只要显示"已连接"，就每 3 秒轻查一次（异步、不占界面线程） */
  (function(){
    var fail = 0;
    setInterval(function(){
      try{
        if(document.hidden) return;
        if(!document.body.classList.contains('cam-on')) { fail = 0; return; }
        req('get_caminfo.cgi', { timeout: 2500 }).then(function(){
          fail = 0;
        }).catch(function(){
          fail++;
          if(fail >= 2){
            fail = 0;
            log('检测不到相机（可能已关机/退出传输态）→ 标记为未连接', 'warn');
            if(window.__om3setConn) window.__om3setConn(false);
          }
        });
      }catch(e){}
    }, 3000);
  })();

''' + anchor_ping
h = h.replace(anchor_ping, PING, 1)

# ---------- 3) 扫码性能：画布只设一次 + 分辨率降 + 日志限流 ----------
old_cam = """    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},
        width:{ideal:1280}, height:{ideal:720}}, audio:false})"""
assert h.count(old_cam) == 1, h.count(old_cam)
h = h.replace(old_cam, """    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},
        width:{ideal:640}, height:{ideal:480}}, audio:false})""", 1)

old_draw = """        function canvasTry(){
          if(!(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth)) return false;
          var sc = Math.min(1, MAXW / Math.max(v.videoWidth, v.videoHeight));
          var w = Math.max(1, Math.round(v.videoWidth * sc)), hh = Math.max(1, Math.round(v.videoHeight * sc));
          c.width = w; c.height = hh;
          ctx.drawImage(v, 0, 0, w, hh);"""
assert h.count(old_draw) == 1, h.count(old_draw)
h = h.replace(old_draw, """        var fixed = false;
        function canvasTry(){
          if(!(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth)) return false;
          var sc = Math.min(1, MAXW / Math.max(v.videoWidth, v.videoHeight));
          var w = Math.max(1, Math.round(v.videoWidth * sc)), hh = Math.max(1, Math.round(v.videoHeight * sc));
          if(!fixed || c.width !== w || c.height !== hh){    /* 只设一次，避免每帧重建画布造成越来越卡 */
            c.width = w; c.height = hh; fixed = true;
          }
          ctx.drawImage(v, 0, 0, w, hh);""", 1)

# 扫码日志限流：设备列表最多写 40 行
old_found = """      else if(ev === 'found'){ log('[BLE] 发现：' + a + '　' + b + '　RSSI ' + c);"""
if h.count(old_found) == 1:
    h = h.replace(old_found, """      else if(ev === 'found'){
        window.__bleN = (window.__bleN || 0) + 1;
        if(window.__bleN <= 40) log('[BLE] 发现：' + a + '　' + b + '　RSSI ' + c);""", 1)

# 扫描日志限流：scanSay 每 500ms 才写一次
old_say = "  function scanSay(msg){"
if h.count(old_say) == 1:
    h = h.replace(old_say, """  var _lastSay = 0;
  function scanSay(msg){
    if(Date.now() - _lastSay < 500) return;
    _lastSay = Date.now();""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('三修完成（%+d 字节）' % (len(h) - n0))
