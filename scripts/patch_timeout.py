# -*- coding: utf-8 -*-
"""卡死根因（这一次是真的）：跨语言调用没有超时
页面调 Native.wifiState() 时，如果 ROM 那边"读 Wi-Fi 状态"卡住，JS 线程会一起卡住
→ 状态条永远停在"读取中"，所有按钮都点不动。
修法：桥里所有会碰系统服务的调用都套一层"硬超时"（后台线程 + Future.get(ms)），
超时就返回兜底值，绝不把页面拖死。
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = r'C:\Users\82302\AppData\Local\Temp\apk\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()

if 'bridge timeout' in j:
    print('已应用过，跳过')
    sys.exit(0)

anchor = '        @JavascriptInterface\n        public String wifiState() {'
assert j.count(anchor) == 1, j.count(anchor)
i = j.find(anchor)
k = j.find('        @JavascriptInterface', i + 10)

NEW = '''        /* ---------- 桥调用硬超时：系统服务偶发卡住时，页面不能跟着卡死 ---------- */
        private static final java.util.concurrent.ExecutorService POOL =
                java.util.concurrent.Executors.newCachedThreadPool();

        private String timedString(final String tag, long ms, final String fallback,
                                   final java.util.concurrent.Callable<String> job) {
            java.util.concurrent.Future<String> f = POOL.submit(job);
            try {
                return f.get(ms, java.util.concurrent.TimeUnit.MILLISECONDS);
            } catch (Throwable e) {
                f.cancel(true);
                android.util.Log.w("OM3", "bridge timeout: " + tag + " -> " + e);
                return fallback;
            }
        }

        @JavascriptInterface
        public String wifiState() {
            return timedString("wifiState", 900, "{\\"wifi\\":false,\\"ssid\\":\\"\\",\\"timeout\\":true}",
                    new java.util.concurrent.Callable<String>() {
                @Override public String call() throws Exception {
                    WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    boolean on = false;
                    String ssid = "";
                    if (wm != null) {
                        on = wm.isWifiEnabled();
                        WifiInfo wi = wm.getConnectionInfo();
                        if (wi != null && wi.getSSID() != null) ssid = wi.getSSID().replace("\\"", "");
                    }
                    if (ssid.startsWith("<")) ssid = "";
                    return "{\\"wifi\\":" + on + ",\\"ssid\\":\\"" + ssid + "\\"}";
                }
            });
        }

        @JavascriptInterface
        public String cameraState() {
            /* 只报我们自己发起的连接：不碰 getConnectionInfo，避免一直触发定位查询 */
            return "{\\"connected\\":" + (sCamNet != null) + ",\\"ssid\\":\\"" + lastSsid + "\\"}";
        }

'''
j = j[:i] + NEW + j[k:]

# joinWifi / forgetWifi 也套超时
old_join = '        public String joinWifi(String ssid, String pass) {'
assert j.count(old_join) == 1
j = j.replace(old_join, '''        public String joinWifi(final String ssid, final String pass) {
            return timedString("joinWifi", 4000, "timeout", new java.util.concurrent.Callable<String>() {
                @Override public String call() throws Exception { return joinWifiInner(ssid, pass); }
            });
        }

        private String joinWifiInner(String ssid, String pass) {''', 1)
old_forget = '        public String forgetWifi() {'
assert j.count(old_forget) == 1
j = j.replace(old_forget, '''        public String forgetWifi() {
            return timedString("forgetWifi", 3000, "timeout", new java.util.concurrent.Callable<String>() {
                @Override public String call() throws Exception { return forgetWifiInner(); }
            });
        }

        private String forgetWifiInner() {''', 1)

open(p, 'w', encoding='utf-8', newline='').write(j)
print('MainActivity：wifiState / joinWifi / forgetWifi 都加了硬超时')
