# -*- coding: utf-8 -*-
"""页面侧三处修复（Java 侧已在 patch_conn2.py 应用）：
1) 检测成功 / Wi-Fi 已是相机热点 → 界面切成「已连接」
2) connectNow 处理 dialog / sec_error 文案
3) 扫码看门狗可取消（扫到了不再误报"摄像头没画面"）
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---- 1. 看门狗可取消 ----
old_wd = """        setTimeout(function(){
          if(!scanStream){
            var so = document.getElementById('scanOut');"""
assert h.count(old_wd) == 1
h = h.replace(old_wd, """        scanWatch = setTimeout(function(){
          if(!scanStream){
            var so = document.getElementById('scanOut');""", 1)

old_stop = """  function stopScan(){
    if(scanRAF){ try{ cancelAnimationFrame(scanRAF); }catch(e){} clearTimeout(scanRAF); scanRAF = null; }"""
assert h.count(old_stop) == 1
h = h.replace(old_stop, """  var scanWatch = null;
  function stopScan(){
    if(scanRAF){ try{ cancelAnimationFrame(scanRAF); }catch(e){} clearTimeout(scanRAF); scanRAF = null; }
    if(scanWatch){ clearTimeout(scanWatch); scanWatch = null; }""", 1)

# ---- 2. connectNow 文案 ----
old_d = """    else if(r === 'unsupported') camOut('这个安卓版本不支持 app 直接连热点。请打开系统 Wi-Fi 选 ' + ssid + '（密码：' + pass + '）。', 'warn');"""
assert h.count(old_d) == 1
h = h.replace(old_d, """    else if(r.indexOf('dialog') === 0) camOut('系统弹窗出来了 —— 点「连接」，手机就连上 ' + ssid + ' 了。', 'ok');
    else if(r === 'unsupported') camOut('这个安卓版本不支持 app 直接连热点。请打开系统 Wi-Fi 选 ' + ssid + '（密码：' + pass + '）。', 'warn');""", 1)

old_s = """    else if(r.indexOf('sec_error') === 0) camOut('系统不让我直接连热点（安全限制）。请点「打开系统 Wi-Fi 设置」，手动选 ' + ssid + '（密码：' + pass + '）——连过一次后系统就记住了。', 'warn');"""
assert h.count(old_s) == 1
h = h.replace(old_s, """    else if(r.indexOf('sec_error') === 0) camOut('系统不让 app 直接连热点。请点「打开系统 Wi-Fi 设置」，手动选 ' + ssid + '（密码：' + pass + '）——连上一次后系统就记住了。　[原因：' + r.slice(0, 90) + ']', 'warn');""", 1)

# ---- 3. 状态判定 ----
old_online = """        line(o1, '结果：相机在线，可以做 ② 备份了。', 'ok');"""
assert h.count(old_online) == 1
h = h.replace(old_online, old_online + """
        if(window.__om3setConn) window.__om3setConn(true);""", 1)

old_st = """  function statusTick(){
    if(Native && Native.cameraState){"""
assert h.count(old_st) == 1
h = h.replace(old_st, """  function statusTick(){
    if(Native && Native.wifiState){
      try{
        var ws0 = JSON.parse(Native.wifiState() || '{}');
        var cur0 = (ws0.ssid || '');
        if(/^<?unknown/i.test(cur0)) cur0 = '';
        var sv0 = camSaved();
        if(cur0 && ((sv0 && sv0.ssid && cur0 === sv0.ssid) || /^(OM-?3|OM-?D|OM-?1|OM-?5)/i.test(cur0)))
          if(!document.body.classList.contains('cam-on') && window.__om3setConn) window.__om3setConn(true);
      }catch(e){}
    }
    if(Native && Native.cameraState){""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面三处修复完成，base.html %.1f KB（+%d 字节）' % (len(h.encode('utf-8')) / 1024, len(h) - n0))
