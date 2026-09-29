# -*- coding: utf-8 -*-
"""扫码体验修复：
1) 扫到之后把结果显示在页面上（原来写进已经关闭的浮层里，等于没提示）
2) 二维码里没有密码 / 解析失败 → 直接引导手动填
3) 自动连接统一走一个函数，成功/缺权限/失败都在页面上说清楚
4) 扫码画面卡：解码降到 ~8 帧/秒 + 降到 800px 再解码 + 采集分辨率压到 720p
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_scan2.html', 'w', encoding='utf-8', newline='').write(h)

# ---------- 1. 采集分辨率 + 解码降采样 + 限帧 ----------
old = """    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}}, audio:false})"""
assert h.count(old) == 1
h = h.replace(old, """    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},
        width:{ideal:1280}, height:{ideal:720}}, audio:false})""", 1)

old = """        var ctx = c.getContext('2d');
        function tick(){
          if(!scanStream) return;
          if(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth){
            c.width = v.videoWidth; c.height = v.videoHeight;
            ctx.drawImage(v, 0, 0, c.width, c.height);
            var found = null;
            try{
              var img = ctx.getImageData(0, 0, c.width, c.height);
              found = window.jsQR(img.data, img.width, img.height, {inversionAttempts:'dontInvert'});
            }catch(e){}
            if(found && found.data){ onScan(found.data); return; }
          }
          scanRAF = requestAnimationFrame(tick);
        }
        scanRAF = requestAnimationFrame(tick);"""
assert h.count(old) == 1
new = """        var ctx = c.getContext('2d');
        var MAXW = 800;                      /* 解码用的小图：够认二维码，手机不卡 */
        function tick(){
          if(!scanStream) return;
          if(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth){
            var sc = Math.min(1, MAXW / Math.max(v.videoWidth, v.videoHeight));
            var w = Math.max(1, Math.round(v.videoWidth * sc)), hh = Math.max(1, Math.round(v.videoHeight * sc));
            c.width = w; c.height = hh;
            ctx.drawImage(v, 0, 0, w, hh);
            var found = null;
            try{
              var img = ctx.getImageData(0, 0, w, hh);
              found = window.jsQR(img.data, img.width, img.height, {inversionAttempts:'dontInvert'});
            }catch(e){}
            if(found && found.data){ onScan(found.data); return; }
          }
          scanRAF = setTimeout(tick, 120);   /* ≈8 帧/秒，识别够用，画面也不卡 */
        }
        scanRAF = setTimeout(tick, 120);"""
h = h.replace(old, new, 1)

old = """  function stopScan(){
    if(scanRAF){ cancelAnimationFrame(scanRAF); scanRAF = null; }"""
assert h.count(old) == 1
h = h.replace(old, """  function stopScan(){
    if(scanRAF){ try{ cancelAnimationFrame(scanRAF); }catch(e){} clearTimeout(scanRAF); scanRAF = null; }""", 1)

# ---------- 2. 扫到之后：结果写页面 + 引导 ----------
i = h.find('  function onScan(text){')
j = h.find('})();', i)          # onScan 是模块最后一个函数，到 IIFE 结束
assert 0 < i < j
NEW_ONSCAN = '''  /* 扫码结果一律写在页面上（浮层马上要关，写里面等于没提示） */
  function scanHost(){ return document.getElementById('camWifiOut'); }
  function showManual(msg, cls){
    document.getElementById('camManualCard').style.display = '';
    var host = scanHost();
    if(msg) line(host, msg, cls);
    setTimeout(function(){
      var c = document.getElementById('camManualCard');
      var top = c.getBoundingClientRect().top + window.pageYOffset - 70;
      window.scrollTo(0, top > 0 ? top : 0);
    }, 60);
  }
  /* 把相机交给系统记住：成功 / 缺权限 / 失败都在页面上说清楚 */
  function joinNow(ssid, pass){
    var host = scanHost();
    if(!ssid){ line(host, '先把 SSID 填上。', 'warn'); return; }
    if(!pass){ line(host, '先把密码填上（相机屏幕上那串）。', 'warn'); return; }
    if(!Native){ line(host, '这个版本没有原生桥（桌面版页面），请用手机上的 app。', 'warn'); return; }
    line(host, '正在把这台相机交给系统记住…');
    var r = '';
    try{ r = String(Native.joinWifi(ssid, pass)); }catch(e){ r = 'error:' + e.message; }
    if(r === 'ok'){
      line(host, '已记住：以后相机开机、Wi-Fi 打开，手机会自动连上——不用再扫、不用官方 app。', 'ok');
      line(host, '下一步：点右上角 ☰ → 「② 备份设置」。', 'ok');
      setTimeout(function(){ wifiRefresh(); statusTick(); }, 1200);
    } else if(r.indexOf('need_perm') === 0){
      line(host, '还差一步授权：弹出的「附近的设备 / 位置信息」点「允许」，然后再点一次「记住它，以后自动连」。', 'warn');
    } else if(r === 'unsupported'){
      line(host, '这个安卓版本不支持自动记住热点。点「打开系统 Wi-Fi 设置」手动连一次即可 —— SSID：' + ssid + '　密码：' + pass, 'warn');
    } else {
      line(host, '自动记住没成功（' + r + '）。点「打开系统 Wi-Fi 设置」手动连也行 —— SSID：' + ssid + '　密码：' + pass, 'warn');
    }
  }
  window.__om3joinNow = joinNow;

  function onScan(text){
    stopScan();
    document.getElementById('camSsid').value = '';
    document.getElementById('camPass').value = '';
    var p = parseWifi(text);
    var host = scanHost();
    host.innerHTML = '';
    showManual('扫到内容：' + text, 'ok');
    if(!p.ssid){
      line(host, '没认出 SSID / 密码。请照相机屏幕上写的，把上面两格填上，再点「记住它，以后自动连」。', 'warn');
      line(host, '（顺便把这行「扫到内容」发我，我加上解析规则。）', 'warn');
      return;
    }
    document.getElementById('camSsid').value = p.ssid;
    document.getElementById('camPass').value = p.pass || '';
    line(host, '识别到 SSID：' + p.ssid, 'ok');
    if(!p.pass){
      line(host, '二维码里没有密码。请看相机屏幕上的那串密码，填进上面「相机密码」再点「记住它」。', 'warn');
      setTimeout(function(){ try{ document.getElementById('camPass').focus(); }catch(e){} }, 200);
      return;
    }
    line(host, '密码也读到了。', 'ok');
    joinNow(p.ssid, p.pass);
  }
  window.__om3onScan = onScan;

'''
h = h[:i] + NEW_ONSCAN + h[j:]

# ---------- 3. 「记住它」按钮改走同一个函数 ----------
i = h.find("    document.getElementById('camJoin').addEventListener('click', function(){")
j = h.find("    document.getElementById('camWifiSettings').addEventListener('click', function(){")
assert 0 < i < j
h = h[:i] + """    document.getElementById('camJoin').addEventListener('click', function(){
      joinNow(document.getElementById('camSsid').value.trim(), document.getElementById('camPass').value.trim());
    });
""" + h[j:]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('扫码结果反馈 + 限帧降采样 已完成，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
