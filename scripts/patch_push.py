# -*- coding: utf-8 -*-
"""架构修正（不再靠"轮询 + 同步桥"）：
改成事件推送——Java 侧注册网络回调，状态变化时主动把结果推给页面（window.__om3net）。
页面不再为了看状态去阻塞式地问原生；读 SSID 也放在后台线程（带超时）。
这样"自动显示状态"和"卡死"不再二选一。
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'

# ---------------- Java ----------------
p = TMP + r'\apk\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()
if 'startWatch' not in j:
    anchor = '        @JavascriptInterface\n        public String cameraState() {'
    assert j.count(anchor) == 1, j.count(anchor)
    ADD = '''        private android.net.ConnectivityManager.NetworkCallback sWatchCb = null;

        /** 页面加载时调一次：之后网络状态变化由原生主动推给页面（页面不用再问） */
        @JavascriptInterface
        public void startWatch() {
            try {
                final android.net.ConnectivityManager cm =
                        (android.net.ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
                if (cm == null || sWatchCb != null) return;
                sWatchCb = new android.net.ConnectivityManager.NetworkCallback() {
                    @Override public void onAvailable(android.net.Network n) { pushNet(); }
                    @Override public void onLost(android.net.Network n) { pushNet(); }
                    @Override public void onCapabilitiesChanged(android.net.Network n,
                                                               android.net.NetworkCapabilities c) { pushNet(); }
                };
                android.net.NetworkRequest req = new android.net.NetworkRequest.Builder()
                        .addTransportType(android.net.NetworkCapabilities.TRANSPORT_WIFI)
                        .build();
                cm.registerNetworkCallback(req, sWatchCb);
                pushNet();
            } catch (Throwable t) {
                android.util.Log.w("OM3", "startWatch: " + t);
            }
        }

        @JavascriptInterface
        public void stopWatch() {
            try {
                if (sWatchCb != null) {
                    android.net.ConnectivityManager cm =
                            (android.net.ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
                    if (cm != null) cm.unregisterNetworkCallback(sWatchCb);
                }
            } catch (Throwable t) { }
            sWatchCb = null;
        }

        /** 读 SSID 一律在后台线程（带超时），绝不在 JS 线程上做 */
        private void pushNet() {
            final String json = timedString("pushNet", 1200, "{\\"wifi\\":false,\\"ssid\\":\\"\\",\\"timeout\\":true}",
                    new java.util.concurrent.Callable<String>() {
                @Override public String call() throws Exception {
                    WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    String ssid = "";
                    boolean on = false;
                    if (wm != null) {
                        on = wm.isWifiEnabled();
                        WifiInfo wi = wm.getConnectionInfo();
                        if (wi != null && wi.getSSID() != null) ssid = wi.getSSID().replace("\\"", "");
                    }
                    if (ssid.startsWith("<")) ssid = "";
                    return "{\\"wifi\\":" + on + ",\\"ssid\\":\\"" + ssid + "\\",\\"cam\\":" + (sCamNet != null) + "}";
                }
            });
            jsCall("window.__om3net&&window.__om3net(" + json + ")");
        }

'''
    j = j.replace(anchor, ADD + anchor, 1)
    # onDestroy 里收掉监听
    j = j.replace('        try { if (bridge != null) bridge.autoDrop(); } catch (Throwable t) { }',
                  '        try { if (bridge != null) { bridge.stopWatch(); bridge.autoDrop(); } } catch (Throwable t) { }', 1)
    open(p, 'w', encoding='utf-8', newline='').write(j)
    print('Java: startWatch / stopWatch / pushNet 已加（事件推送）')
else:
    print('Java: 已应用过，跳过')

# ---------------- 页面 ----------------
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
if '__om3net' not in h:
    anchor = "  setConn(false);\n  /* 扫码别一直开着"
    assert h.count(anchor) == 1, h.count(anchor)
    ADD = '''  /* ================= 状态由原生"推"过来：页面不再阻塞式地问 ================= */
  window.__om3net = function(o){
    try{
      if(!o) return;
      _wc.v = o; _wc.at = Date.now();
      var ssid = o.ssid || '';
      var isCam = /^(OM-?3|OM-?D|OM-?1|OM-?5)/i.test(ssid);
      var sv = camSaved();
      if(o.cam || (ssid && ((sv && sv.ssid && ssid === sv.ssid) || isCam))){
        if(!document.body.classList.contains('cam-on') && window.__om3setConn) window.__om3setConn(true);
      }
      statusTick();
    }catch(e){}
  };
  /* 加载时订阅一次；之后全靠推送 */
  try{ if(Native && Native.startWatch) Native.startWatch(); }catch(e){}

'''
    h = h.replace(anchor, ADD + anchor, 1)
    open(P, 'w', encoding='utf-8', newline='').write(h)
    print('页面: __om3net 事件入口 + 启动订阅')
else:
    print('页面: 已应用过，跳过')
