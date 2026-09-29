# -*- coding: utf-8 -*-
"""让 app 自己能连相机 Wi-Fi：
- MainActivity 加一个 JS 桥（读当前 Wi-Fi / 打开系统 Wi-Fi 设置 / 记住相机 SSID+密码并自动连接）
- 「导入相机」页加「连接助手」区块
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
APK = TMP + r'\apk'

# ============================================================ 1. MainActivity.java
p = APK + r'\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()
assert 'OM3Native' not in j
j = j.replace('''import android.app.Activity;
import android.os.Bundle;''', '''import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.net.wifi.WifiNetworkSuggestion;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;''', 1)
j = j.replace('''import android.webkit.WebViewClient;''', '''import android.webkit.JavascriptInterface;
import android.webkit.WebViewClient;
import android.widget.Toast;''', 1)

j = j.replace('''        wv.setWebViewClient(new WebViewClient());''',
              '''        wv.addJavascriptInterface(new Bridge(), "OM3Native");
        wv.setWebViewClient(new WebViewClient());''', 1)

BRIDGE = '''
    /**
     * 给页面用的原生能力：连相机 Wi-Fi。
     * 页面里通过 window.OM3Native.xxx() 调用。
     */
    public class Bridge {

        /** 当前 Wi-Fi 状态：{"wifi":true,"ssid":"OM-3-123456","sdk":34} */
        @JavascriptInterface
        public String wifiState() {
            try {
                WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                boolean on = wm != null && wm.isWifiEnabled();
                String ssid = "";
                if (wm != null) {
                    WifiInfo wi = wm.getConnectionInfo();
                    if (wi != null && wi.getSSID() != null) ssid = wi.getSSID().replace("\\"", "");
                }
                return "{\\"wifi\\":" + on + ",\\"ssid\\":\\"" + ssid + "\\",\\"sdk\\":" + Build.VERSION.SDK_INT + "}";
            } catch (Throwable t) {
                return "{\\"error\\":\\"" + t.getClass().getSimpleName() + "\\"}";
            }
        }

        @JavascriptInterface
        public void openWifiSettings() {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    try {
                        Intent it = new Intent(Settings.ACTION_WIFI_SETTINGS);
                        it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(it);
                    } catch (Throwable t) {
                        Toast.makeText(MainActivity.this, "打不开系统 Wi-Fi 设置", Toast.LENGTH_SHORT).show();
                    }
                }
            });
        }

        @JavascriptInterface
        public void toast(final String msg) {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    Toast.makeText(MainActivity.this, msg, Toast.LENGTH_SHORT).show();
                }
            });
        }

        /**
         * 记住相机的 SSID + 密码，交给系统，以后相机开机就自动连上（不用再手输）。
         * 返回 ok / need_perm:xxx / 其他错误码。
         */
        @JavascriptInterface
        public String joinWifi(String ssid, String pass) {
            if (ssid == null || ssid.length() == 0) return "bad_ssid";
            if (pass == null || pass.length() < 8) return "bad_pass";
            if (Build.VERSION.SDK_INT < 29) return "unsupported";
            String need = Build.VERSION.SDK_INT >= 33
                    ? "android.permission.NEARBY_WIFI_DEVICES"
                    : "android.permission.ACCESS_FINE_LOCATION";
            if (Build.VERSION.SDK_INT >= 23
                    && checkSelfPermission(need) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{ need }, 4711);
                return "need_perm:" + need;
            }
            try {
                WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                if (wm == null) return "no_wifi_service";
                WifiNetworkSuggestion s = new WifiNetworkSuggestion.Builder()
                        .setSsid(ssid)
                        .setWpa2Passphrase(pass)
                        .build();
                int r = wm.addNetworkSuggestions(java.util.Collections.singletonList(s));
                return r == WifiManager.STATUS_NETWORK_SUGGESTIONS_SUCCESS ? "ok" : ("code_" + r);
            } catch (Throwable t) {
                return "error:" + t.getClass().getSimpleName();
            }
        }

        /** 撤销之前记住的相机热点。 */
        @JavascriptInterface
        public String forgetWifi() {
            try {
                if (Build.VERSION.SDK_INT < 29) return "unsupported";
                WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                if (wm == null) return "no_wifi_service";
                int r = wm.removeNetworkSuggestions(java.util.Collections.<WifiNetworkSuggestion>emptyList());
                return r == WifiManager.STATUS_NETWORK_SUGGESTIONS_SUCCESS ? "ok" : ("code_" + r);
            } catch (Throwable t) {
                return "error:" + t.getClass().getSimpleName();
            }
        }
    }

    @Override
    protected void onDestroy() {'''
j = j.replace('''
    @Override
    protected void onDestroy() {''', BRIDGE, 1)
open(p, 'w', encoding='utf-8', newline='').write(j)
print('MainActivity: 已加 OM3Native 桥（wifiState/openWifiSettings/joinWifi/forgetWifi/toast）')

# ============================================================ 2. AndroidManifest
p = APK + r'\AndroidManifest.xml'
m = open(p, encoding='utf-8').read()
add = ''
if 'ACCESS_FINE_LOCATION' not in m:
    add += '    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />\n'
if 'NEARBY_WIFI_DEVICES' not in m:
    add += ('    <uses-permission android:name="android.permission.NEARBY_WIFI_DEVICES"\n'
            '        android:usesPermissionFlags="neverForLocation" />\n')
m = m.replace('    <uses-sdk', add + '    <uses-sdk', 1)
open(p, 'w', encoding='utf-8', newline='').write(m)
print('AndroidManifest: 位置/附近设备权限已加')

# ============================================================ 3. 页面：连接助手
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_camwifi.html', 'w', encoding='utf-8', newline='').write(h)

import re
m = re.search(r'<div class="camstep"><div class="camhd">① 检测相机</div>', h)
assert m
BLOCK = '''<div class="camstep"><div class="camhd">连接助手 · 先让手机连上相机</div>
<div class="camout" id="camWifiState">正在读当前 Wi-Fi…</div>
<label>相机 SSID：<input type="text" id="camSsid" placeholder="例如 OM-3-1234567" style="width:190px"></label>
<label>相机密码：<input type="text" id="camPass" placeholder="相机屏幕上显示的那串密码" style="width:190px"></label>
<button type="button" id="camJoin" class="camprimary">记住它，以后自动连</button>
<button type="button" id="camWifiSettings">打开系统 Wi-Fi 设置</button>
<button type="button" id="camForget" class="camghost">撤销记住的热点</button>
<div class="camout" id="camWifiOut">SSID 和密码在相机上：<b>MENU → Wi-Fi/蓝牙 → Wi-Fi 设置</b>（或屏幕上「连接智能手机」那一屏），会直接写出 SSID 和密码。
填进这里点「记住它」之后，系统会在相机热点出现时自动连上——<b>不用再装/开官方 app，也不用每次手输密码</b>。
连上后 Android 会提示「此网络无法访问互联网」，选「保持连接 / 仍然连接」即可。</div>
</div>

'''
h = h[:m.start()] + BLOCK + h[m.start():]

JS_OLD = """  /* ---------- ① 检测相机 ---------- */"""
assert h.count(JS_OLD) == 1
JS_NEW = """  /* ---------- 连接助手（走原生桥） ---------- */
  var Native = window.OM3Native || null;
  var oW = document.getElementById('camWifiState'), oWO = document.getElementById('camWifiOut');
  function wifiRefresh(){
    if(!Native){ oW.innerHTML = '<span class="warn">这个版本里没有原生桥（桌面版页面）。</span>'; return; }
    var st = {};
    try{ st = JSON.parse(Native.wifiState() || '{}'); }catch(e){}
    if(st.error){ oW.innerHTML = '<span class="warn">读不到 Wi-Fi 状态（' + esc(st.error) + '）——不影响使用，按提示手动连即可。</span>'; return; }
    var s = st.ssid || '';
    var isCam = /^OM-?3/i.test(s) || /^OM-?D/i.test(s) || /OM-3-/i.test(s);
    oW.innerHTML = (st.wifi ? 'Wi-Fi 已开' : '<span class="warn">Wi-Fi 没开</span>') +
      '　当前连接：<b>' + (s ? esc(s) : '（没有连 Wi-Fi）') + '</b>' +
      (isCam ? ' <span class="ok">← 已经是相机热点，可以往下做了</span>'
             : (s ? ' <span class="warn">← 不是相机热点，按下面做一次</span>' : ''));
  }
  if(Native){
    document.getElementById('camJoin').addEventListener('click', function(){
      var ssid = document.getElementById('camSsid').value.trim();
      var pass = document.getElementById('camPass').value.trim();
      if(!ssid || !pass){ line(oWO, '先把 SSID 和密码填上（相机屏幕上就有）。', 'warn'); return; }
      line(oWO, '正在把「' + ssid + '」交给系统…');
      var r = '';
      try{ r = String(Native.joinWifi(ssid, pass)); }catch(e){ r = 'error:' + e.message; }
      if(r === 'ok'){
        line(oWO, '已记住。相机开机（Wi-Fi 打开）时手机会自动连上它。', 'ok');
        line(oWO, '如果没自动连：点「打开系统 Wi-Fi 设置」，在列表里点一下 ' + ssid + ' 就会连（密码已经记住）。', 'ok');
        setTimeout(wifiRefresh, 1500);
      } else if(r.indexOf('need_perm') === 0){
        line(oWO, '需要在弹出的授权框里点「允许」（可能是"附近的设备"或"位置信息"权限），然后再点一次「记住它」。', 'warn');
      } else if(r === 'unsupported'){
        line(oWO, '这个安卓版本不支持自动记住热点，请点「打开系统 Wi-Fi 设置」手动连一次（密码：' + pass + '）。', 'warn');
      } else {
        line(oWO, '没成功（' + r + '）。可以点「打开系统 Wi-Fi 设置」手动连：SSID ' + ssid + '，密码 ' + pass, 'warn');
      }
    });
    document.getElementById('camWifiSettings').addEventListener('click', function(){
      Native.openWifiSettings();
      line(oWO, '已打开系统 Wi-Fi 设置：找到 ' + (document.getElementById('camSsid').value.trim() || 'OM-3-xxxxxxx') +
                ' 连上，再回到本 app 点 ① 检测相机。');
    });
    document.getElementById('camForget').addEventListener('click', function(){
      var r = ''; try{ r = String(Native.forgetWifi()); }catch(e){ r = 'error'; }
      line(oWO, r === 'ok' ? '已撤销记住的相机热点。' : ('撤销失败（' + r + '）。'), r === 'ok' ? 'ok' : 'warn');
    });
    wifiRefresh();
  } else {
    oW.innerHTML = '<span class="warn">桌面版没有这个能力：请在手机上用这套手册的 app，或用系统 Wi-Fi 设置手动连相机热点。</span>';
  }

  /* ---------- ① 检测相机 ---------- */"""
h = h.replace(JS_OLD, JS_NEW, 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：已加「连接助手」区块，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
