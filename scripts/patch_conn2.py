# -*- coding: utf-8 -*-
"""根据真机日志修三处：
1) 手动/系统连上相机后，app 界面没切成"已连接"（状态只认原生回调）→ 改成：检测成功 或 Wi-Fi 已经是相机热点，就切
2) WifiNetworkSpecifier 在这台机器上抛 SecurityException → 换用系统弹窗 ACTION_WIFI_ADD_NETWORKS（安卓 11+，不需要特殊权限）
3) 扫码成功 3 秒后仍弹"摄像头没画面"（看门狗没被取消）→ 修
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
APK = TMP + r'\apk'
P = TMP + r'\app\base.html'

# ============================================================ 1. Java
p = APK + r'\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()

if 'addNetworkDialog' in j:
    print('Java: 已应用过，跳过')
else:
        old_exc = '''            } catch (SecurityException se) {
                    sCamCb = null;
                    return "sec_error:" + se.getMessage();'''
    assert j.count(old_exc) == 1
    new_exc = '''            } catch (SecurityException se) {
                    sCamCb = null;
                    android.util.Log.w("OM3", "requestNetwork SecurityException: " + se.getMessage());
                    String d = addNetworkDialog(ssid, pass);
                    return ("dialog".equals(d)) ? "dialog:" + se.getMessage() : "sec_error:" + se.getMessage();'''
    j = j.replace(old_exc, new_exc, 1)

    # 新增：用系统弹窗连接（Android 11+）
    anchor = '''        @JavascriptInterface
            public String disconnectCamera() {'''
    assert j.count(anchor) == 1
    ADD = '''        /** 安卓 11+：把热点交给系统弹窗确认（不需要额外权限，最稳） */
            @JavascriptInterface
            public String addNetworkDialog(final String ssid, final String pass) {
                if (Build.VERSION.SDK_INT < 30) return "unsupported";
                try {
                    android.net.wifi.WifiNetworkSuggestion s = new android.net.wifi.WifiNetworkSuggestion.Builder()
                            .setSsid(ssid)
                            .setWpa2Passphrase(pass)
                            .build();
                    java.util.ArrayList<android.net.wifi.WifiNetworkSuggestion> list =
                            new java.util.ArrayList<android.net.wifi.WifiNetworkSuggestion>();
                    list.add(s);
                    final Intent it = new Intent("android.settings.WIFI_ADD_NETWORKS");
                    it.putExtra("android.provider.extra.WIFI_NETWORK_LIST", list);
                    it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    runOnUiThread(new Runnable() {
                        @Override public void run() {
                            try { startActivity(it); } catch (Throwable t) {
                                try { startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS)
                                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); } catch (Throwable t2) { }
                            }
                        }
                    });
                    return "dialog";
                } catch (Throwable t) {
                    return "error:" + t.getClass().getSimpleName();
                }
            }

    ''' + anchor
    j = j.replace(anchor, ADD, 1)
    open(p, 'w', encoding='utf-8', newline='').write(j)
    print('Java: SecurityException → 系统弹窗连接（WIFI_ADD_NETWORKS）')

# ============================================================ 2. 页面
h = open(P, encoding='utf-8').read()

# 2a) 扫码看门狗：扫到就取消
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
h = h.replace(old_stop, """  function stopScan(){
    if(scanRAF){ try{ cancelAnimationFrame(scanRAF); }catch(e){} clearTimeout(scanRAF); scanRAF = null; }
    if(scanWatch){ clearTimeout(scanWatch); scanWatch = null; }""", 1)
old_var = """  var scanRAF = null, scanStream = null;"""
if h.count(old_var) == 1:
    h = h.replace(old_var, """  var scanRAF = null, scanStream = null, scanWatch = null;""", 1)
else:
    # 变量可能写法不同，兜底：在 stopScan 前插一个声明
    h = h.replace("  function stopScan(){", "  var scanWatch = null;\n  function stopScan(){", 1)
print('页面: 扫码看门狗可取消')

# 2b) connectNow：处理 dialog / 打印安全限制原因
old_d = """    else if(r === 'unsupported') camOut('这个安卓版本不支持 app 直接连热点。请打开系统 Wi-Fi 选 ' + ssid + '（密码：' + pass + '）。', 'warn');"""
assert h.count(old_d) == 1
h = h.replace(old_d, """    else if(r.indexOf('dialog') === 0) camOut('系统弹窗出来了 —— 点「连接」，手机就连上 ' + ssid + ' 了。', 'ok');
    else if(r === 'unsupported') camOut('这个安卓版本不支持 app 直接连热点。请打开系统 Wi-Fi 选 ' + ssid + '（密码：' + pass + '）。', 'warn');""", 1)
old_s = """    else if(r.indexOf('sec_error') === 0) camOut('系统不让我直接连热点（安全限制）。请点「打开系统 Wi-Fi 设置」，手动选 ' + ssid + '（密码：' + pass + '）——连过一次后系统就记住了。', 'warn');"""
assert h.count(old_s) == 1
h = h.replace(old_s, """    else if(r.indexOf('sec_error') === 0) camOut('系统不让 app 直接连热点。请点「打开系统 Wi-Fi 设置」，手动选 ' + ssid + '（密码：' + pass + '）——连上一次后系统就记住了。　[原因：' + r.slice(0, 90) + ']', 'warn');""", 1)
h = h.replace("  document.getElementById('camConnect').addEventListener('click', connectNow);",
              """  document.getElementById('camConnect').addEventListener('click', connectNow);
  var camWifiBtn = document.getElementById('camWifiSettings');""", 1)
print('页面: dialog / sec_error 提示已更新')

# 2c) 连接判定：检测成功 或 已经在相机热点上 → 视为已连接
old_check_start = """  document.getElementById('camCheck').addEventListener('click', async function(){"""
assert h.count(old_check_start) == 1
h = h.replace(old_check_start, old_check_start, 1)
# 在检测成功处切状态：找"结果：相机在线"那句
old_online = """line(o1, '结果：相机在线，可以做 ② 备份了。', 'ok');"""
assert h.count(old_online) == 1, h.count(old_online)
h = h.replace(old_online, """line(o1, '结果：相机在线，可以做 ② 备份了。', 'ok');
        setConn(true);""", 1)

# statusTick：Wi-Fi 已是相机热点 → 切成已连接
old_st = """  function statusTick(){
    if(Native && Native.cameraState){"""
assert h.count(old_st) == 1
h = h.replace(old_st, """  function statusTick(){
    if(Native && Native.wifiState){
      try{
        var ws = JSON.parse(Native.wifiState() || '{}');
        var cur = (ws.ssid || '');
        if(/^<?unknown/i.test(cur)) cur = '';
        var sv = camSaved();
        if(cur && ((sv && sv.ssid && cur === sv.ssid) || /^(OM-?3|OM-?D|OM-?1|OM-?5)/i.test(cur))){
          if(!document.body.classList.contains('cam-on')) setConn(true);
        }
      }catch(e){}
    }
    if(Native && Native.cameraState){""", 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面: 检测成功 / 已在相机热点 → 自动切「已连接」')
