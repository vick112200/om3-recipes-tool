# -*- coding: utf-8 -*-
"""修 SecurityException：Android 13/14 上 WifiNetworkSpecifier 仍需 ACCESS_FINE_LOCATION。
- 权限：FINE_LOCATION + (13+) NEARBY_WIFI_DEVICES 一起请求，授权后自动重试连接
- 清单：去掉 neverForLocation（否则系统认定该权限不能用于可定位的 Wi-Fi 操作）
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
APK = TMP + r'\apk'

# ---------- 1. 清单：去掉 neverForLocation ----------
p = APK + r'\AndroidManifest.xml'
m = open(p, encoding='utf-8').read()
i = m.find('<uses-permission android:name="android.permission.NEARBY_WIFI_DEVICES"')
j = m.find('/>', i) + 2
assert i > 0 and j > i
old = m[i:j]
m = m[:i] + '<uses-permission android:name="android.permission.NEARBY_WIFI_DEVICES" />' + m[j:]
open(p, 'w', encoding='utf-8', newline='').write(m)
print('清单：NEARBY_WIFI_DEVICES 去掉 neverForLocation')
print('   原：', ' '.join(old.split())[:90])

# ---------- 2. MainActivity ----------
p = APK + r'\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()

# 2a) Activity 级 js 调用 + 待重试凭据
anchor = '    protected void onCreate(Bundle savedInstanceState) {'
assert j.count(anchor) == 1
j = j.replace(anchor, '''    private String pendSsid = null, pendPass = null;

    private void jscall(final String code) {
        runOnUiThread(new Runnable() {
            @Override public void run() {
                try { wv.evaluateJavascript(code + ";", null); } catch (Throwable t) { }
            }
        });
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] res) {
        super.onRequestPermissionsResult(code, perms, res);
        if (code != 4713) return;
        boolean ok = true;
        for (int i = 0; i < res.length; i++) if (res[i] != PackageManager.PERMISSION_GRANTED) ok = false;
        if (ok && pendSsid != null) {
            final String s = pendSsid, pw = pendPass;
            pendSsid = null; pendPass = null;
            jscall("window.__om3camState&&window.__om3camState('retry')");
            new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(new Runnable() {
                @Override public void run() { try { new Bridge().connectCamera(s, pw); } catch (Throwable t) { } }
            }, 300);
        } else {
            jscall("window.__om3camState&&window.__om3camState('denied')");
        }
    }

''' + anchor, 1)

# 2b) Bridge 的 jsCall 复用 Activity 的
old_js = '''        private void jsCall(final String code) {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    try { wv.evaluateJavascript(code + ";", null); } catch (Throwable t) { }
                }
            });
        }'''
assert j.count(old_js) == 1
j = j.replace(old_js, '''        private void jsCall(final String code) { jscall(code); }''', 1)

# 2c) connectCamera：权限两个一起要 + 授权后自动重试 + SecurityException 兜底
i = j.find('        public String connectCamera(final String ssid, final String pass) {')
k = j.find('        @JavascriptInterface\n        public String disconnectCamera() {')
assert 0 < i < k
NEW = '''        public String connectCamera(final String ssid, final String pass) {
            if (ssid == null || ssid.length() == 0) return "bad_ssid";
            if (Build.VERSION.SDK_INT < 29) { openWifiSettings(); return "unsupported"; }
            java.util.ArrayList<String> need = new java.util.ArrayList<String>();
            if (checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION)
                    != PackageManager.PERMISSION_GRANTED)
                need.add(android.Manifest.permission.ACCESS_FINE_LOCATION);
            if (Build.VERSION.SDK_INT >= 33
                    && checkSelfPermission(android.Manifest.permission.NEARBY_WIFI_DEVICES)
                       != PackageManager.PERMISSION_GRANTED)
                need.add(android.Manifest.permission.NEARBY_WIFI_DEVICES);
            if (!need.isEmpty()) {
                pendSsid = ssid;
                pendPass = pass;
                requestPermissions(need.toArray(new String[0]), 4713);
                return "need_perm:" + need.get(0);
            }
            android.net.ConnectivityManager cm =
                    (android.net.ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) return "no_cm";
            disconnectCamera();
            android.net.wifi.WifiNetworkSpecifier.Builder b =
                    new android.net.wifi.WifiNetworkSpecifier.Builder().setSsid(ssid);
            if (pass != null && pass.length() >= 8) b.setWpa2Passphrase(pass);
            android.net.NetworkRequest req = new android.net.NetworkRequest.Builder()
                    .addTransportType(android.net.NetworkCapabilities.TRANSPORT_WIFI)
                    .setNetworkSpecifier(b.build())
                    .build();
            sCamCb = new android.net.ConnectivityManager.NetworkCallback() {
                @Override public void onAvailable(android.net.Network n) {
                    sCamNet = n;
                    jsCall("window.__om3camState&&window.__om3camState('connected')");
                }
                @Override public void onLost(android.net.Network n) {
                    if (n == sCamNet) sCamNet = null;
                    jsCall("window.__om3camState&&window.__om3camState('lost')");
                }
                @Override public void onUnavailable() {
                    sCamNet = null;
                    jsCall("window.__om3camState&&window.__om3camState('unavailable')");
                }
            };
            try {
                cm.requestNetwork(req, sCamCb, 60000);
            } catch (SecurityException se) {
                sCamCb = null;
                return "sec_error:" + se.getMessage();
            } catch (Throwable t) {
                sCamCb = null;
                return "error:" + t.getClass().getSimpleName();
            }
            return "asking";
        }

'''
j = j[:i] + NEW + j[k:]
open(p, 'w', encoding='utf-8', newline='').write(j)
print('MainActivity：权限两项一起请求 + 授权后自动重连 + sec_error 兜底')

# ---------- 3. 页面：新状态与提示 ----------
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
old = """    else if(state === 'unavailable'){ camOut('系统没能连上这个热点：确认相机 Wi-Fi 开着、就在旁边；也可以去系统 Wi-Fi 列表里手动选它。', 'err'); }"""
assert h.count(old) == 1
h = h.replace(old, """    else if(state === 'unavailable'){ camOut('系统没能连上这个热点：确认相机 Wi-Fi 开着、就在旁边；也可以去系统 Wi-Fi 列表里手动选它。', 'err'); }
    else if(state === 'retry'){ camOut('权限已给，正在连接…', 'ok'); }
    else if(state === 'denied'){ camOut('权限被拒绝了。请到「设置 → 应用 → 本 app → 权限」里打开「位置信息 / 附近的设备」，再点「连接相机」。', 'warn'); }""", 1)

old2 = """    else camOut('没能发起连接（' + r + '）。可以点「打开系统 Wi-Fi 设置」手动连。', 'err');"""
assert h.count(old2) == 1
h = h.replace(old2, """    else if(r.indexOf('sec_error') === 0) camOut('系统不让我直接连热点（安全限制）。请点「打开系统 Wi-Fi 设置」，手动选 ' + ssid + '（密码：' + pass + '）——连过一次后系统就记住了。', 'warn');
    else camOut('没能发起连接（' + r + '）。可以点「打开系统 Wi-Fi 设置」手动连。', 'err');""", 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：retry / denied / sec_error 提示已加')
