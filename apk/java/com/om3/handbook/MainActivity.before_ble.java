package com.om3.handbook;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.net.wifi.WifiNetworkSuggestion;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.View;
import android.webkit.ValueCallback;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebViewClient;
import android.widget.Toast;

public class MainActivity extends Activity {

    private WebView wv;
    private Bridge bridge = null;

    private String pendSsid = null, pendPass = null;

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
        if (code == 4712) {
            boolean cam = res.length > 0 && res[0] == PackageManager.PERMISSION_GRANTED;
            jscall(cam ? "window.__om3camGranted&&window.__om3camGranted('ok')"
                       : "window.__om3camGranted&&window.__om3camGranted('denied')");
            return;
        }
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

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        wv = new WebView(this);
        WebSettings s = wv.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        // 允许 file:///android_asset 页面直接请求相机 Wi-Fi 上的 http://192.168.0.10/（明文 HTTP）
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        /* 关掉网页级缩放。
           用户 2026-09-23 反馈"写入页底部页签往下滚时跟着跑了（没钉住）" ——
           底栏确实是 position:fixed，祖先链里也没有 transform/filter（都量过，是干净的），
           但页面被**双指放大**之后，fixed 元素按"布局视口"定位，视觉视口一平移它就跟着动，
           看起来就是"没钉住"。网页级缩放对这个 app 没啥用（整页本来就按手机宽度设计，
           看样片走的是自带的看图浮层，里面是**自己实现的双指缩放**，不受这里影响）。 */
        s.setSupportZoom(false);
        s.setTextZoom(100);
        bridge = new Bridge();
        wv.addJavascriptInterface(bridge, "OM3Native");
        // 让页面能用 <video> 调摄像头扫码
        wv.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, android.webkit.ValueCallback<android.net.Uri[]> cb,
                                             FileChooserParams params) {
                try {
                    if (fileCb != null) { fileCb.onReceiveValue(null); }
                    fileCb = cb;
                    android.content.Intent i = new android.content.Intent(android.content.Intent.ACTION_GET_CONTENT);
                    i.addCategory(android.content.Intent.CATEGORY_OPENABLE);
                    i.setType("*/*");
                    startActivityForResult(android.content.Intent.createChooser(i, "选择方案文件"), 4714);
                    return true;
                } catch (Throwable t) {
                    fileCb = null;
                    Toast.makeText(MainActivity.this, "打不开文件选择器：" + t.getMessage(), Toast.LENGTH_SHORT).show();
                    return false;
                }
            }

            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    @Override public void run() { request.grant(request.getResources()); }
                });
            }
        });
        wv.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                try {
                    Uri u = req.getUrl();
                    if (u != null && "om3.local".equals(u.getHost())) {
                        String path = u.getPath();
                        if (path == null || path.length() == 0 || "/".equals(path)) path = "/index.html";
                        String name = path.startsWith("/") ? path.substring(1) : path;
                        String mime = name.endsWith(".html") ? "text/html"
                                    : name.endsWith(".js") ? "application/javascript"
                                    : name.endsWith(".css") ? "text/css"
                                    : name.endsWith(".png") ? "image/png"
                                    : name.endsWith(".jpg") || name.endsWith(".jpeg") ? "image/jpeg"
                                    : "application/octet-stream";
                        return new WebResourceResponse(mime, "utf-8", getAssets().open(name));
                    }
                } catch (Throwable t) {
                    return new WebResourceResponse("text/plain", "utf-8",
                            new java.io.ByteArrayInputStream(("asset error: " + t).getBytes()));
                }
                return null;
            }
        });
        wv.setBackgroundColor(0xFF161616);
        wv.setOverScrollMode(View.OVER_SCROLL_NEVER);

        setContentView(wv);
        // 用 https 虚拟源加载本页：WebView 只在安全上下文里给摄像头（file:// 会一直挂住）
        wv.loadUrl("https://om3.local/index.html");
    }

    /**
     * 返回键 / 侧滑返回：先问页面要不要接管。
     * 页面里 window.__handleBack() 依次处理：全屏看图 → 目录面板 → 页签回到「原版方案」，
     * 都处理不了才回退 WebView 历史，最后才退出应用。
     */
    @Override
    public void onBackPressed() {
        if (wv == null) {
            super.onBackPressed();
            return;
        }
        wv.evaluateJavascript(
                "(function(){try{return (window.__handleBack&&window.__handleBack())?1:0;}catch(e){return 0;}})()",
                new ValueCallback<String>() {
                    @Override
                    public void onReceiveValue(String value) {
                        if ("1".equals(value)) {
                            return;                 // 页面自己处理掉了
                        }
                        if (wv != null && wv.canGoBack()) {
                            wv.goBack();
                            return;
                        }
                        MainActivity.super.onBackPressed();
                    }
                });
    }

    /**
     * 给页面用的原生能力：连相机 Wi-Fi。
     * 页面里通过 window.OM3Native.xxx() 调用。
     */
    private android.webkit.ValueCallback<android.net.Uri[]> fileCb = null;

    @Override
    protected void onActivityResult(int req, int res, android.content.Intent data) {
        if (req == 4714) {
            android.net.Uri[] out = null;
            if (res == android.app.Activity.RESULT_OK && data != null) {
                if (data.getData() != null) {
                    out = new android.net.Uri[]{ data.getData() };
                } else if (data.getClipData() != null) {
                    int n = data.getClipData().getItemCount();
                    out = new android.net.Uri[n];
                    for (int k = 0; k < n; k++) out[k] = data.getClipData().getItemAt(k).getUri();
                }
            }
            if (fileCb != null) { fileCb.onReceiveValue(out); fileCb = null; }
            return;
        }
        super.onActivityResult(req, res, data);
    }

    public class Bridge {

        /* ===== 蓝牙（实验）：扫描相机广播的 BLE 设备 ===== */
        private final java.util.Map<String, String> sBle = new java.util.concurrent.ConcurrentHashMap<String, String>();
        private android.bluetooth.le.ScanCallback sBleCb = null;

        @android.webkit.JavascriptInterface
        public String blePerm() {
            try {
                if (android.os.Build.VERSION.SDK_INT >= 31) {
                    boolean a = checkSelfPermission("android.permission.BLUETOOTH_SCAN") == android.content.pm.PackageManager.PERMISSION_GRANTED;
                    boolean b = checkSelfPermission("android.permission.BLUETOOTH_CONNECT") == android.content.pm.PackageManager.PERMISSION_GRANTED;
                    if (!a || !b) return "need:android.permission.BLUETOOTH_SCAN,android.permission.BLUETOOTH_CONNECT";
                }
                return "ok";
            } catch (Throwable t) { return "err:" + t.getMessage(); }
        }

        @android.webkit.JavascriptInterface
        public void bleScanStart() {
            try {
                sBle.clear();
                final android.bluetooth.BluetoothAdapter ad = android.bluetooth.BluetoothAdapter.getDefaultAdapter();
                if (ad == null) { jsCall("window.__om3ble&&window.__om3ble('err','这台设备没有蓝牙')"); return; }
                if (!ad.isEnabled()) { jsCall("window.__om3ble&&window.__om3ble('err','蓝牙没打开')"); return; }
                android.bluetooth.le.BluetoothLeScanner sc = ad.getBluetoothLeScanner();
                if (sc == null) { jsCall("window.__om3ble&&window.__om3ble('err','拿不到扫描器')"); return; }
                android.bluetooth.le.ScanCallback cb = new android.bluetooth.le.ScanCallback() {
                    @Override public void onScanResult(int type, android.bluetooth.le.ScanResult r) {
                        try {
                            String mac = r.getDevice().getAddress();
                            String nm = r.getDevice().getName();
                            if (nm == null) nm = "";
                            int rssi = r.getRssi();
                            sBle.put(mac, nm + "#" + rssi);
                            jsCall("window.__om3ble&&window.__om3ble('found'," + jsonStr(nm) + "," + jsonStr(mac) + "," + rssi + ")");
                        } catch (Throwable t) { }
                    }
                };
                sc.startScan(cb);
                sBleCb = cb;
                jsCall("window.__om3ble&&window.__om3ble('start','')");
            } catch (Throwable t) {
                jsCall("window.__om3ble&&window.__om3ble('err'," + jsonStr("扫描失败：" + t.getMessage()) + ")");
            }
        }

        @android.webkit.JavascriptInterface
        public void bleScanStop() {
            try {
                android.bluetooth.BluetoothAdapter ad = android.bluetooth.BluetoothAdapter.getDefaultAdapter();
                if (ad != null && ad.getBluetoothLeScanner() != null && sBleCb != null) ad.getBluetoothLeScanner().stopScan(sBleCb);
            } catch (Throwable t) { }
            sBleCb = null;
        }

        @android.webkit.JavascriptInterface
        public String bleDevices() {
            StringBuilder sb = new StringBuilder("[");
            boolean first = true;
            for (java.util.Map.Entry<String, String> e : sBle.entrySet()) {
                String v = e.getValue();
                int i = v.indexOf('#');
                String nm = (i > 0) ? v.substring(0, i) : v;
                String rs = (i > 0) ? v.substring(i + 1) : "0";
                if (!first) sb.append(",");
                first = false;
                sb.append("{\"mac\":").append(jsonStr(e.getKey())).append(",\"name\":").append(jsonStr(nm)).append(",\"rssi\":").append(rs).append("}");
            }
            return sb.append("]").toString();
        }


        /** 系统分享面板：把文本（配方 JSON / .oes 内容）分享到微信等 */
        @android.webkit.JavascriptInterface
        public String shareText(final String name, final String text, final String mime) {
            try {
                final String t = (text == null) ? "" : text;
                final String nm = (name == null || name.length() == 0) ? "OM-3 配方" : name;
                final String m = (mime == null || mime.length() == 0) ? "text/plain" : mime;
                runOnUiThread(new Runnable() {
                    @Override public void run() {
                        try {
                            android.content.Intent i = new android.content.Intent(android.content.Intent.ACTION_SEND);
                            i.setType(m);
                            i.putExtra(android.content.Intent.EXTRA_SUBJECT, nm);
                            i.putExtra(android.content.Intent.EXTRA_TITLE, nm);
                            i.putExtra(android.content.Intent.EXTRA_TEXT, t);
                            android.content.Intent c = android.content.Intent.createChooser(i, "分享到…");
                            c.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
                            startActivity(c);
                        } catch (Throwable e2) {
                            Toast.makeText(MainActivity.this, "分享失败：" + e2.getMessage(), Toast.LENGTH_SHORT).show();
                        }
                    }
                });
                return "ok";
            } catch (Throwable e) { return "err:" + e.getMessage(); }
        }


        /** 当前 Wi-Fi 状态：{"wifi":true,"ssid":"OM-3-123456","sdk":34} */
        /* ---------- 桥调用硬超时：系统服务偶发卡住时，页面不能跟着卡死 ---------- */
        private final java.util.concurrent.ExecutorService POOL =
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
            return timedString("wifiState", 900, "{\"wifi\":false,\"ssid\":\"\",\"timeout\":true}",
                    new java.util.concurrent.Callable<String>() {
                @Override public String call() throws Exception {
                    WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    boolean on = false;
                    String ssid = "";
                    if (wm != null) {
                        on = wm.isWifiEnabled();
                        WifiInfo wi = wm.getConnectionInfo();
                        if (wi != null && wi.getSSID() != null) ssid = wi.getSSID().replace("\"", "");
                    }
                    if (ssid.startsWith("<")) ssid = "";
                    return "{\"wifi\":" + on + ",\"ssid\":\"" + ssid + "\"}";
                }
            });
        }

        private String jsonStr(String s) {
            if (s == null) s = "";
            StringBuilder sb = new StringBuilder("\"");
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                switch (c) {
                    case '"':  sb.append("\\\""); break;
                    case '\\': sb.append("\\\\"); break;
                    case '\n': sb.append("\\n"); break;
                    case '\r': sb.append("\\r"); break;
                    case '\t': sb.append("\\t"); break;
                    default:
                        if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                        else sb.append(c);
                }
            }
            return sb.append('"').toString();
        }

        private String camReq(String path, byte[] body, String method) {
            try {
                java.net.URL u = new java.net.URL("http://192.168.0.10/" + path);
                java.net.HttpURLConnection c = (java.net.HttpURLConnection)
                        ((sCamNet != null) ? sCamNet.openConnection(u) : u.openConnection());
                c.setConnectTimeout(8000);
                c.setReadTimeout(20000);
                c.setRequestMethod(method);
                c.setRequestProperty("Connection", "close");
                if (body != null) {
                    c.setDoOutput(true);
                    c.setFixedLengthStreamingMode(body.length);
                    c.setRequestProperty("Content-Type", "application/octet-stream");
                    java.io.OutputStream os = c.getOutputStream();
                    os.write(body);
                    os.flush();
                    os.close();
                }
                int code = c.getResponseCode();
                java.io.InputStream in = (code >= 400) ? c.getErrorStream() : c.getInputStream();
                java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
                if (in != null) {
                    byte[] buf = new byte[8192];
                    int n, total = 0;
                    while ((n = in.read(buf)) > 0) {
                        bo.write(buf, 0, n);
                        total += n;
                        if (total > 500000) break;
                    }
                    in.close();
                }
                c.disconnect();
                return "{\"s\":" + code + ",\"t\":" + jsonStr(new String(bo.toByteArray(), "UTF-8")) + "}";
            } catch (Throwable t) {
                String msg = "ERR " + t.getClass().getSimpleName()
                        + (t.getMessage() == null ? "" : (": " + t.getMessage()));
                return "{\"s\":0,\"t\":" + jsonStr(msg) + "}";
            }
        }

        private int sReqId = 0;

        /** 异步版：立刻返回请求号，结果由后台线程推回页面（页面不再被 HTTP 阻塞） */
        @JavascriptInterface
        public String camGetAsync(final String path) { return camAsync(path, null, "GET"); }

        @JavascriptInterface
        public String camPostAsync(final String path, final String b64) {
            byte[] body = null;
            try { body = android.util.Base64.decode(b64, android.util.Base64.DEFAULT); } catch (Throwable t) { }
            return camAsync(path, body, "POST");
        }

        private String camAsync(final String path, final byte[] body, final String method) {
            final String id = "r" + (++sReqId);
            POOL.execute(new Runnable() {
                @Override public void run() {
                    String json;
                    try { json = camReq(path, body, method); }
                    catch (Throwable t) { json = "{\"s\":0,\"t\":\"ERR " + t.getClass().getSimpleName() + "\"}"; }
                    jsCall("window.__om3http&&window.__om3http(" + jsonStr(id) + "," + json + ")");
                }
            });
            return id;
        }

        @JavascriptInterface
        public String camGet(String path) {
            return camReq(path, null, "GET");
        }

        @JavascriptInterface
        public String camPost(String path, String base64) {
            try {
                return camReq(path, android.util.Base64.decode(base64, android.util.Base64.DEFAULT), "POST");
            } catch (Throwable t) {
                return "{\"s\":0,\"t\":" + jsonStr("bad body: " + t) + "}";
            }
        }

        /* ---------- 「连接相机」：由 app 主动请系统连相机热点（Android 10+） ----------
           官方 app 那套是系统级连接；我们这里用 WifiNetworkSpecifier：
           点一次 → 系统弹窗确认 → 连上相机热点（此时相机 HTTP 走这条网络），
           断开或退出后自动回到原来的 Wi-Fi。凭据存在页面里，下次不用再扫。 */
        private android.net.Network sCamNet = null;          /* Bridge 是内部类，不能用 static */
        private android.net.ConnectivityManager.NetworkCallback sCamCb = null;

        private void jsCall(final String code) { jscall(code); }

        private String wifiPerm() {
            return Build.VERSION.SDK_INT >= 33
                    ? "android.permission.NEARBY_WIFI_DEVICES"
                    : "android.permission.ACCESS_FINE_LOCATION";
        }

        /** 请系统连相机热点：asking / connected 由页面回调，need_perm 需要先授权 */
        @JavascriptInterface
        public String connectCamera(final String ssid, final String pass) {
            if (ssid == null || ssid.length() == 0) return "bad_ssid";
            lastSsid = ssid;
            lastPass = (pass == null) ? "" : pass;
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
                android.util.Log.w("OM3", "requestNetwork SecurityException: " + se.getMessage());
                String d = addNetworkDialog(ssid, pass);
                return ("dialog".equals(d)) ? "dialog:" + se.getMessage() : "sec_error:" + se.getMessage();
            } catch (Throwable t) {
                sCamCb = null;
                return "error:" + t.getClass().getSimpleName();
            }
            return "asking";
        }

        private String lastSsid = "", lastPass = "";

        /** 关掉界面时用：撤掉我们发起的连接 + 撤掉交给系统的那个热点，让手机回到原来的 Wi-Fi */
        void autoDrop() {
            disconnectCamera();
            try {
                if (lastSsid != null && lastSsid.length() > 0 && Build.VERSION.SDK_INT >= 29) {
                    WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    if (wm != null) {
                        WifiNetworkSuggestion.Builder sb = new WifiNetworkSuggestion.Builder().setSsid(lastSsid);
                        if (lastPass != null && lastPass.length() >= 8) sb.setWpa2Passphrase(lastPass);
                        wm.removeNetworkSuggestions(java.util.Collections.singletonList(sb.build()));
                    }
                }
            } catch (Throwable t) { }
        }

        @JavascriptInterface
        public String dropCamera() { autoDrop(); return "ok"; }

        /** 权限自检：{"camera":bool,"fine":bool,"nearby":bool,"sdk":33} */
        @JavascriptInterface
        public String permState() {
            java.util.function.Function<String, Boolean> has = null;
            boolean cam = checkSelfPermission(android.Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
            boolean fine = checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
            boolean near = (Build.VERSION.SDK_INT >= 33)
                    ? checkSelfPermission(android.Manifest.permission.NEARBY_WIFI_DEVICES) == PackageManager.PERMISSION_GRANTED
                    : true;
            return "{\"camera\":" + cam + ",\"fine\":" + fine + ",\"nearby\":" + near + ",\"sdk\":" + Build.VERSION.SDK_INT + "}";
        }

        @JavascriptInterface
        public void openAppSettings() {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    try {
                        Intent it = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                        it.setData(Uri.parse("package:" + getPackageName()));
                        it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(it);
                    } catch (Throwable t) {
                        try { startActivity(new Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); } catch (Throwable t2) { }
                    }
                }
            });
        }

        /** 安卓 11+：把热点交给系统弹窗确认（不需要额外权限，最稳） */
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

        @JavascriptInterface
        public String disconnectCamera() {
            try {
                if (Build.VERSION.SDK_INT >= 29) {
                    android.net.ConnectivityManager cm =
                            (android.net.ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
                    if (cm != null && sCamCb != null) cm.unregisterNetworkCallback(sCamCb);
                }
            } catch (Throwable t) { }
            sCamCb = null;
            sCamNet = null;
            return "ok";
        }

        /** {"connected":true,"ssid":"OM-3-…"} */
        private android.net.ConnectivityManager.NetworkCallback sWatchCb = null;

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
            final String json = timedString("pushNet", 1200, "{\"wifi\":false,\"ssid\":\"\",\"timeout\":true}",
                    new java.util.concurrent.Callable<String>() {
                @Override public String call() throws Exception {
                    WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    String ssid = "";
                    boolean on = false;
                    if (wm != null) {
                        on = wm.isWifiEnabled();
                        WifiInfo wi = wm.getConnectionInfo();
                        if (wi != null && wi.getSSID() != null) ssid = wi.getSSID().replace("\"", "");
                    }
                    if (ssid.startsWith("<")) ssid = "";
                    return "{\"wifi\":" + on + ",\"ssid\":\"" + ssid + "\",\"cam\":" + (sCamNet != null) + "}";
                }
            });
            jsCall("window.__om3net&&window.__om3net(" + json + ")");
        }

        @JavascriptInterface
        public String cameraState() {
            /* 只报我们自己发起的连接：不碰 getConnectionInfo，避免一直触发定位查询 */
            return "{\"connected\":" + (sCamNet != null) + ",\"ssid\":\"" + lastSsid + "\"}";
        }

        /** 页面要调摄像头扫码时先问这个：ok / need_perm:xxx */
        @JavascriptInterface
        public String ensureCamera() {
            if (Build.VERSION.SDK_INT >= 23
                    && checkSelfPermission(android.Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{ android.Manifest.permission.CAMERA }, 4712);
                return "need_perm:android.permission.CAMERA";
            }
            return "ok";
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
        public String joinWifi(final String ssid, final String pass) {
            return timedString("joinWifi", 4000, "timeout", new java.util.concurrent.Callable<String>() {
                @Override public String call() throws Exception { return joinWifiInner(ssid, pass); }
            });
        }

        private String joinWifiInner(String ssid, String pass) {
            if (ssid == null || ssid.length() == 0) return "bad_ssid";
            lastSsid = ssid;
            lastPass = (pass == null) ? "" : pass;
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
            return timedString("forgetWifi", 3000, "timeout", new java.util.concurrent.Callable<String>() {
                @Override public String call() throws Exception { return forgetWifiInner(); }
            });
        }

        private String forgetWifiInner() {
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
    protected void onDestroy() {
        try { if (bridge != null) { bridge.stopWatch(); bridge.autoDrop(); } } catch (Throwable t) { }
        if (wv != null) {
            wv.destroy();
            wv = null;
        }
        super.onDestroy();
    }
}
