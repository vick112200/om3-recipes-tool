# -*- coding: utf-8 -*-
"""MainActivity：省定位 + 退出自动断连
- cameraState() 不再调 getConnectionInfo（那是需要定位权限的调用，轮询时会一直查位置）
- 记住最后用过的 SSID/密码
- dropCamera() / onDestroy → 撤掉我们发起的连接 + 撤掉交给系统的热点（关掉 app 就断开）
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = r'C:\Users\82302\AppData\Local\Temp\apk\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()

# 1) 保存 Bridge 引用
old = '        wv.addJavascriptInterface(new Bridge(), "OM3Native");'
assert j.count(old) == 1
j = j.replace(old, '        bridge = new Bridge();\n        wv.addJavascriptInterface(bridge, "OM3Native");', 1)
old2 = '    private WebView wv;\n'
assert j.count(old2) == 1
j = j.replace(old2, '    private WebView wv;\n    private Bridge bridge = null;\n', 1)

# 2) cameraState 不碰 WifiManager
i = j.find('        public String cameraState() {')
k = j.find('        /** 页面要调摄像头扫码时先问这个', i)
assert 0 < i < k, (i, k)
j = j[:i] + (
    '        public String cameraState() {\n'
    '            /* 只报我们自己发起的连接：不碰 getConnectionInfo，避免一直触发定位查询 */\n'
    '            return "{\\"connected\\":" + (sCamNet != null) + ",\\"ssid\\":\\"" + lastSsid + "\\"}";\n'
    '        }\n\n') + j[k:]

# 3) lastSsid/lastPass + autoDrop + dropCamera
old3 = '        /** 安卓 11+：把热点交给系统弹窗确认（不需要额外权限，最稳） */'
assert j.count(old3) == 1
NEW = (
    '        private String lastSsid = "", lastPass = "";\n\n'
    '        /** 关掉界面时用：撤掉我们发起的连接 + 撤掉交给系统的那个热点，让手机回到原来的 Wi-Fi */\n'
    '        void autoDrop() {\n'
    '            disconnectCamera();\n'
    '            try {\n'
    '                if (lastSsid != null && lastSsid.length() > 0 && Build.VERSION.SDK_INT >= 29) {\n'
    '                    WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);\n'
    '                    if (wm != null) {\n'
    '                        WifiNetworkSuggestion.Builder sb = new WifiNetworkSuggestion.Builder().setSsid(lastSsid);\n'
    '                        if (lastPass != null && lastPass.length() >= 8) sb.setWpa2Passphrase(lastPass);\n'
    '                        wm.removeNetworkSuggestions(java.util.Collections.singletonList(sb.build()));\n'
    '                    }\n'
    '                }\n'
    '            } catch (Throwable t) { }\n'
    '        }\n\n'
    '        @JavascriptInterface\n'
    '        public String dropCamera() { autoDrop(); return "ok"; }\n\n')
j = j.replace(old3, NEW + old3, 1)

# 4) 记录 lastSsid/lastPass
old4 = ('        public String connectCamera(final String ssid, final String pass) {\n'
        '            if (ssid == null || ssid.length() == 0) return "bad_ssid";')
assert j.count(old4) == 1
j = j.replace(old4, old4 + '\n            lastSsid = ssid;\n            lastPass = (pass == null) ? "" : pass;', 1)
old5 = ('        public String joinWifi(String ssid, String pass) {\n'
        '            if (ssid == null || ssid.length() == 0) return "bad_ssid";')
assert j.count(old5) == 1
j = j.replace(old5, old5 + '\n            lastSsid = ssid;\n            lastPass = (pass == null) ? "" : pass;', 1)

# 5) onDestroy 自动断连
old6 = '    protected void onDestroy() {\n        if (wv != null) {'
assert j.count(old6) == 1
j = j.replace(old6, '    protected void onDestroy() {\n        try { if (bridge != null) bridge.autoDrop(); } catch (Throwable t) { }\n        if (wv != null) {', 1)

open(p, 'w', encoding='utf-8', newline='').write(j)
print('MainActivity: 已省定位查询 / 退出自动断连')
