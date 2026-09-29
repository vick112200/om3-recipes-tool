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

    private String pendSsid = null, pendPass = null, pendBssid = null;   /* r64：BSSID 也要一起挂起（授权回来才重连） */

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
        if (code == 4714) {                      /* 蓝牙运行时权限（API31+）申请结果 → 回页面 */
            boolean ok = true;
            for (int i = 0; i < res.length; i++) if (res[i] != PackageManager.PERMISSION_GRANTED) ok = false;
            jscall("window.__om3blePerm&&window.__om3blePerm(" + (ok ? "'ok'" : "'denied'") + ")");
            return;
        }
        if (code != 4713) return;
        boolean ok = true;
        for (int i = 0; i < res.length; i++) if (res[i] != PackageManager.PERMISSION_GRANTED) ok = false;
        if (ok && pendSsid != null) {
            final String s = pendSsid, pw = pendPass, bs = pendBssid;   /* r64：BSSID 别丢 */
            pendSsid = null; pendPass = null; pendBssid = null;
            jscall("window.__om3camState&&window.__om3camState('retry')");
            new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(new Runnable() {
                /* r64 顺手修：这里原来是 `new Bridge().connectCamera(s, pw)` —— **新建了临时 Bridge**，
                   于是连接状态与 lastSsid/lastBssid 全记在临时实例上，页面读的 bridge.cameraState()
                   看不到（"授权后重连"这条路上，"已连上哪个热点"是空白的）。改成用主实例。
                   注：bridge 在 onCreate 里就已建好；为稳妥仍判空，空则保持旧的兜底行为。 */
                @Override public void run() {
                    try {
                        if (bridge != null) bridge.connectCamera2(s, pw, bs);
                        else new Bridge().connectCamera(s, pw);
                    } catch (Throwable t) { }
                }
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

        /* ===== 官方 APK 的蓝牙常量（2026-09-24 反汇编 com.omdigitalsolutions.oishare 得到）=====
           用户报"蓝牙列表里根本看不出哪个是相机" —— 因为我们是**不带过滤器的全量扫描**，
           而官方是带过滤器扫的（混淆类 LN2/c 的扫描方法，逐条指令对过）：
             new ScanFilter.Builder().setServiceUuid(ParcelUuid.fromString(
                 "ADC505F9-4E58-4B71-B8CA-983BB8C73E4F")).build()
             scanner.startScan(filters, settings, callback)
           同一个 UUID 也是官方 getService() 用的那个服务；服务下三个特征值分别是
             82F949B4-…（官方字段 m，**写命令用**）、B7A8015C-…（字段 n，**写命令用**）、
             05A02050-…（字段 o，订阅通知用：写到 CCCD 00002902-…）。
           所以我们也可以按同一个 UUID 过滤 → 列表里只剩相机（找得到的情况下）。 */
        static final String OM3_BLE_SVC    = "ADC505F9-4E58-4B71-B8CA-983BB8C73E4F";
        static final String OM3_BLE_WRITE1 = "82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68";
        static final String OM3_BLE_WRITE2 = "B7A8015C-CB94-4EFA-BDA2-B7921FA9951F";
        static final String OM3_BLE_NOTIFY = "05A02050-0860-4919-8ADD-9801FBA8B6ED";

        /** 名字像不像相机（过滤器没命中时的兜底；和页面上的正则保持一致） */
        boolean bleCamLike(String nm) {          /* 注意：Bridge 是非静态内部类，--release 8 下不能声明 static 方法 */
            if (nm == null) return false;
            String s = nm.toUpperCase();
            return s.matches(".*(OM-?3|OM-?1|OM-?5|OM-?D|OM3|OM1|OM5|OMD|OMSYSTEM|E-M[0-9]|E-P[0-9]|PEN|STYLUS|TG-[0-9]).*");
        }

        /** 广播里带不带官方那个服务 UUID（带了 = 基本可以确定是相机） */
        boolean bleHasCamSvc(android.bluetooth.le.ScanResult r) {
            try {
                android.bluetooth.le.ScanRecord rec = r.getScanRecord();
                if (rec == null) return false;
                java.util.List<android.os.ParcelUuid> us = rec.getServiceUuids();
                if (us == null) return false;
                for (android.os.ParcelUuid u : us) {
                    if (u != null && OM3_BLE_SVC.equalsIgnoreCase(String.valueOf(u.getUuid()))) return true;
                }
            } catch (Throwable t) { }
            return false;
        }

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

        /* 主动申请蓝牙权限（用户 2026-09-24 报："点扫描只弹 app 自己的提示，没有系统弹窗；权限我都给了"）。
           原因：Android 12(API 31) 起 BLUETOOTH_SCAN / BLUETOOTH_CONNECT 是**运行时权限** ——
           写进清单只是"有资格申请"，不申请就永远拿不到；以前 JS 一看到 need 就 return，从来没申请过。
           结果 → onRequestPermissionsResult(4714) → window.__om3blePerm('ok'|'denied')。 */
        @android.webkit.JavascriptInterface
        public void bleAskPerm() {
            try {
                if (android.os.Build.VERSION.SDK_INT < 31) {
                    jsCall("window.__om3blePerm&&window.__om3blePerm('ok')");
                    return;
                }
                final java.util.ArrayList<String> need = new java.util.ArrayList<String>();
                if (checkSelfPermission("android.permission.BLUETOOTH_SCAN") != android.content.pm.PackageManager.PERMISSION_GRANTED)
                    need.add("android.permission.BLUETOOTH_SCAN");
                if (checkSelfPermission("android.permission.BLUETOOTH_CONNECT") != android.content.pm.PackageManager.PERMISSION_GRANTED)
                    need.add("android.permission.BLUETOOTH_CONNECT");
                if (need.isEmpty()) {
                    jsCall("window.__om3blePerm&&window.__om3blePerm('ok')");
                    return;
                }
                final MainActivity act = MainActivity.this;
                act.runOnUiThread(new Runnable() {
                    @Override public void run() {
                        try {
                            act.requestPermissions(need.toArray(new String[0]), 4714);
                        } catch (Throwable t) {
                            jsCall("window.__om3blePerm&&window.__om3blePerm('err:request:" + t.getMessage() + "')");
                        }
                    }
                });
            } catch (Throwable t) {
                jsCall("window.__om3blePerm&&window.__om3blePerm('err:" + t.getMessage() + "')");
            }
        }

        /* 缺哪个就报哪个（给「检查权限」用）—— 不要只说"需要权限" */
        @android.webkit.JavascriptInterface
        public String blePermDetail() {
            try {
                StringBuilder sb = new StringBuilder();
                sb.append("SDK=").append(android.os.Build.VERSION.SDK_INT);
                if (android.os.Build.VERSION.SDK_INT >= 31) {
                    sb.append("；BLUETOOTH_SCAN=").append(checkSelfPermission("android.permission.BLUETOOTH_SCAN") == android.content.pm.PackageManager.PERMISSION_GRANTED ? "有" : "缺");
                    sb.append("；BLUETOOTH_CONNECT=").append(checkSelfPermission("android.permission.BLUETOOTH_CONNECT") == android.content.pm.PackageManager.PERMISSION_GRANTED ? "有" : "缺");
                } else {
                    sb.append("；蓝牙权限=旧版本安装即给（不需要申请）");
                }
                android.bluetooth.BluetoothAdapter ad = android.bluetooth.BluetoothAdapter.getDefaultAdapter();
                sb.append("；蓝牙开关=").append(ad == null ? "无适配器" : (ad.isEnabled() ? "开" : "关"));
                return sb.toString();
            } catch (Throwable t) { return "err:" + t.getMessage(); }
        }

        /* ===== 2026-09-24（第 34 轮）：蓝牙开关状态 / 自动打开 / 跳系统设置 =====
           用户要"进页面自动连蓝牙"，官方 connectInner() 的做法是：蓝牙关着就自己打开
           （日志 BLE_INIT_BLE_OFF → BluetoothAdapter.enable()）。这里照做。 */

        /** 蓝牙开关状态：on / off / no_adapter（页面先问，避免无谓地去"打开"） */
        @android.webkit.JavascriptInterface
        public String bleState() {
            try {
                android.bluetooth.BluetoothAdapter ad = android.bluetooth.BluetoothAdapter.getDefaultAdapter();
                if (ad == null) return "no_adapter";
                return ad.isEnabled() ? "on" : "off";
            } catch (Throwable t) { return "no_adapter"; }
        }

        /** 蓝牙关着就打开。返回：
         *    already     本来就开着（幂等）
         *    turned_on   已请求打开
         *    need:xxx    还缺运行时权限（页面会拉起系统授权弹窗）
         *    err:xxx     系统不给开（有的 ROM 要求用户确认）→ 页面给「打开系统蓝牙设置」
         *    no_adapter  这台设备没有蓝牙 */
        @android.webkit.JavascriptInterface
        public String bleEnable() {
            try {
                android.bluetooth.BluetoothAdapter ad = android.bluetooth.BluetoothAdapter.getDefaultAdapter();
                if (ad == null) return "no_adapter";
                if (ad.isEnabled()) return "already";
                if (android.os.Build.VERSION.SDK_INT >= 31
                        && checkSelfPermission("android.permission.BLUETOOTH_CONNECT")
                           != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    return "need:android.permission.BLUETOOTH_CONNECT";
                }
                try {
                    return ad.enable() ? "turned_on" : "err:系统拒绝了打开蓝牙的请求";
                } catch (Throwable t) {
                    return "err:" + String.valueOf(t.getMessage());
                }
            } catch (Throwable t) { return "err:" + String.valueOf(t.getMessage()); }
        }

        /** 跳系统的蓝牙设置页（bleEnable 被系统拒时的退路：让用户自己点一下） */
        @android.webkit.JavascriptInterface
        public void openBtSettings() {
            try {
                android.content.Intent i = new android.content.Intent(
                        android.provider.Settings.ACTION_BLUETOOTH_SETTINGS);
                i.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(i);
            } catch (Throwable t) { }
        }

        /** 系统层蓝牙的连接情况（可能是系统设置或别的 app 连的，不是本 app 连的）。
         *  用户 2026-09-24："手机蓝牙界面已经显示连接上了，但 app 还是显示没连接" ——
         *  那两句话说的不是一回事（系统蓝牙 ≠ 相机 HTTP），页面要把两条链路摊开说清楚。
         *  返回 {"conn":[已连接...], "paired":[配对过但没连...]}（都带 name/address）。 */
        @android.webkit.JavascriptInterface
        public String bleOsConn() {
            try {
                if (android.os.Build.VERSION.SDK_INT >= 31
                        && checkSelfPermission("android.permission.BLUETOOTH_CONNECT")
                           != android.content.pm.PackageManager.PERMISSION_GRANTED) return "{}";
                android.bluetooth.BluetoothManager bm =
                        (android.bluetooth.BluetoothManager) getSystemService(android.content.Context.BLUETOOTH_SERVICE);
                if (bm == null) return "{}";
                java.util.List<android.bluetooth.BluetoothDevice> conn = new java.util.ArrayList<android.bluetooth.BluetoothDevice>();
                int[] profs = new int[] { android.bluetooth.BluetoothProfile.GATT,
                                          android.bluetooth.BluetoothProfile.GATT_SERVER };
                for (int i = 0; i < profs.length; i++) {
                    try {
                        java.util.List<android.bluetooth.BluetoothDevice> ds = bm.getConnectedDevices(profs[i]);
                        if (ds != null) {
                            for (int j = 0; j < ds.size(); j++) {
                                android.bluetooth.BluetoothDevice d = ds.get(j);
                                if (d == null) continue;
                                String ad = "";
                                try { ad = String.valueOf(d.getAddress()); } catch (Throwable t) { }
                                boolean dup = false;
                                for (int k = 0; k < conn.size(); k++) {
                                    String a2 = "";
                                    try { a2 = String.valueOf(conn.get(k).getAddress()); } catch (Throwable t) { }
                                    if (a2 != null && a2.equals(ad)) { dup = true; break; }
                                }
                                if (!dup) conn.add(d);
                            }
                        }
                    } catch (Throwable t) { }
                }
                StringBuilder sb = new StringBuilder("{\"conn\":[");
                for (int i = 0; i < conn.size(); i++) {
                    if (i > 0) sb.append(",");
                    sb.append(bleDevJson(conn.get(i)));
                }
                sb.append("],\"paired\":[");
                try {
                    java.util.Set<android.bluetooth.BluetoothDevice> bonded = bm.getAdapter() != null
                            ? bm.getAdapter().getBondedDevices() : null;
                    int n = 0;
                    if (bonded != null) {
                        for (android.bluetooth.BluetoothDevice d : bonded) {
                            if (d == null) continue;
                            if (n > 0) sb.append(",");
                            sb.append(bleDevJson(d));
                            n++;
                        }
                    }
                } catch (Throwable t) { }
                return sb.append("]}").toString();
            } catch (Throwable t) { return "{}"; }
        }

        /** 一个蓝牙设备的 {name, address}（拿不到名字就给空串，页面只显示地址） */
        private String bleDevJson(android.bluetooth.BluetoothDevice d) {
            String nm = "", ad = "";
            try { ad = String.valueOf(d.getAddress()); } catch (Throwable t) { }
            try { nm = String.valueOf(d.getName()); } catch (Throwable t) { nm = ""; }
            if ("null".equals(nm)) nm = "";
            if ("null".equals(ad)) ad = "";
            return "{\"name\":" + jsonStr(nm) + ",\"address\":" + jsonStr(ad) + "}";
        }

        @android.webkit.JavascriptInterface
        public void bleScanStart() { bleScanStart2(0); }

        /** 扫描。onlyCam=1 → **只扫相机**（按官方那个服务 UUID 过滤，列表里不会有别的设备）；
         *  0 → 全量扫，但每个设备都带一个"像不像相机"的标记（页面据此把相机排最前 + 标 📷）。 */
        @android.webkit.JavascriptInterface
        public void bleScanStart2(final int onlyCam) {
            try {
                sBle.clear();
                final android.bluetooth.BluetoothAdapter ad = android.bluetooth.BluetoothAdapter.getDefaultAdapter();
                if (ad == null) { jsCall("window.__om3ble&&window.__om3ble('err','这台设备没有蓝牙')"); return; }
                if (!ad.isEnabled()) { jsCall("window.__om3ble&&window.__om3ble('err','蓝牙没打开')"); return; }
                android.bluetooth.le.BluetoothLeScanner sc = null;
                try { sc = ad.getBluetoothLeScanner(); }
                catch (Throwable t) { jsCall("window.__om3ble&&window.__om3ble('err','拿不到扫描器：" + String.valueOf(t.getMessage()) + "（多半是没给 BLUETOOTH_SCAN 权限）')"); return; }
                if (sc == null) { jsCall("window.__om3ble&&window.__om3ble('err','拿不到扫描器（可能蓝牙刚被关）')"); return; }
                android.bluetooth.le.ScanCallback cb = new android.bluetooth.le.ScanCallback() {
                    @Override public void onScanResult(int type, android.bluetooth.le.ScanResult r) {
                        try {
                            String mac = r.getDevice().getAddress();
                            String nm = "";
                            try { nm = r.getDevice().getName(); } catch (Throwable t) { nm = ""; }   /* API31+ 需要 BLUETOOTH_CONNECT，没给会抛 */
                            if (nm == null) nm = "";
                            int rssi = r.getRssi();
                            /* 是不是相机：① 广播里带官方那个服务 UUID（最硬）② 名字像相机（兜底） */
                            boolean cam = bleHasCamSvc(r);
                            if (!cam) cam = bleCamLike(nm);
                            sBle.put(mac, nm + "#" + rssi + (cam ? "#cam" : ""));
                            jsCall("window.__om3ble&&window.__om3ble('found'," + jsonStr(nm) + "," + jsonStr(mac)
                                   + "," + rssi + "," + (cam ? 1 : 0) + ")");
                        } catch (Throwable t) { }
                    }
                };
                android.bluetooth.le.ScanSettings st = new android.bluetooth.le.ScanSettings.Builder()
                        .setScanMode(android.bluetooth.le.ScanSettings.SCAN_MODE_LOW_LATENCY).build();
                if (onlyCam == 1) {
                    java.util.List<android.bluetooth.le.ScanFilter> fs = new java.util.ArrayList<android.bluetooth.le.ScanFilter>();
                    fs.add(new android.bluetooth.le.ScanFilter.Builder()
                            .setServiceUuid(android.os.ParcelUuid.fromString(OM3_BLE_SVC)).build());
                    sc.startScan(fs, st, cb);
                } else {
                    sc.startScan(null, st, cb);      /* null = 不过滤（官方在"还没记过相机"时也会走这条路） */
                }
                sBleCb = cb;
                jsCall("window.__om3ble&&window.__om3ble('start'," + jsonStr(onlyCam == 1 ? "onlycam" : "all") + ")");
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

        /* ===== 蓝牙 GATT（实验）：连上相机 → 枚举服务/特征值 → 订阅通知 → 写帧 =====
           为什么要有这一层：官方 app 是靠 BLE 把相机叫醒、让它开 Wi-Fi 的。
           我们现在还不知道**确切指令帧**（要从官方 apk / 抓包拿，见 SPEC-round18 §0），
           所以这里先把"能连、能看、能读、能写、能看回包"的能力做全 ——
           等指令一到手，只要在页面上把帧填进去就能用；同时"探测"本身就能把
           真机上的服务/特征值列出来（这就是定协议的第一步）。
           安全性：只做 GATT 连接/读写，**不配对、不改相机设置、不上传任何数据**；
           一次只保留一个连接（连新的先关旧的）；所有回调都过 try/catch。 */
        private android.bluetooth.BluetoothGatt sGatt = null;
        private String sGattSvcJson = "[]";
        private String sGattMac = "";
        private int sGattMtu = 0;
        private String sGattMtuTxt = "";

        @android.webkit.JavascriptInterface
        public String bleConnect(final String mac) {
            try {
                if (mac == null || mac.length() == 0) return "err:没有 MAC 地址";
                android.bluetooth.BluetoothAdapter ad = android.bluetooth.BluetoothAdapter.getDefaultAdapter();
                if (ad == null) return "err:这台设备没有蓝牙";
                if (!ad.isEnabled()) return "err:蓝牙没打开";
                if (android.os.Build.VERSION.SDK_INT >= 31) {
                    if (checkSelfPermission("android.permission.BLUETOOTH_CONNECT") != android.content.pm.PackageManager.PERMISSION_GRANTED)
                        return "need:android.permission.BLUETOOTH_CONNECT";
                }
                bleCloseOld();                       /* 连新的先关旧的 */
                sGattSvcJson = "[]";
                sGattMac = mac;
                sGattMtu = 0;
                sGattMtuTxt = "";
                android.bluetooth.BluetoothDevice d = ad.getRemoteDevice(mac);
                android.bluetooth.BluetoothGattCallback cb = bleCb();
                android.bluetooth.BluetoothGatt g;
                if (android.os.Build.VERSION.SDK_INT >= 23) {
                    g = d.connectGatt(getApplicationContext(), false, cb, android.bluetooth.BluetoothDevice.TRANSPORT_LE);
                } else {
                    g = d.connectGatt(getApplicationContext(), false, cb);
                }
                if (g == null) return "err:系统没给连接对象";
                sGatt = g;
                jsCall("window.__om3ble&&window.__om3ble('connecting'," + jsonStr(mac) + ")");
                return "ok";
            } catch (Throwable t) {
                return "err:" + t;
            }
        }

        private void bleCloseOld() {
            try { if (sGatt != null) { sGatt.disconnect(); sGatt.close(); } } catch (Throwable t) { }
            sGatt = null;
        }

        @android.webkit.JavascriptInterface
        public String bleServices() { return sGattSvcJson; }

        @android.webkit.JavascriptInterface
        public String bleMtuInfo() { return sGattMtuTxt; }

        @android.webkit.JavascriptInterface
        public String bleDisconnect() {
            try { bleCloseOld(); } catch (Throwable t) { }
            jsCall("window.__om3ble&&window.__om3ble('lost','已断开')");
            return "ok";
        }

        /** 订阅通知：先本地 setCharacteristicNotification，再写 CCCD(0x2902) */
        @android.webkit.JavascriptInterface
        public String bleSubscribe(final String uuid) {
            try {
                if (sGatt == null) return "err:还没连上";
                android.bluetooth.BluetoothGattCharacteristic ch = bleFind(uuid);
                if (ch == null) return "err:找不到这个特征值";
                int p = ch.getProperties();
                if ((p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_NOTIFY) == 0
                        && (p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_INDICATE) == 0)
                    return "err:这个特征值不支持通知/指示";
                boolean okLoc = sGatt.setCharacteristicNotification(ch, true);
                boolean cccd = false;
                android.bluetooth.BluetoothGattDescriptor d =
                        ch.getDescriptor(java.util.UUID.fromString("00002902-0000-1000-8000-00805f9b34fb"));
                if (d != null) {
                    boolean ind = (p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_NOTIFY) == 0;
                    byte[] v = ind ? android.bluetooth.BluetoothGattDescriptor.ENABLE_INDICATION_VALUE
                                   : android.bluetooth.BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE;
                    if (android.os.Build.VERSION.SDK_INT >= 33) {
                        cccd = sGatt.writeDescriptor(d, v) == android.bluetooth.BluetoothStatusCodes.SUCCESS;
                    } else {
                        d.setValue(v);
                        cccd = sGatt.writeDescriptor(d);
                    }
                }
                jsCall("window.__om3ble&&window.__om3ble('sub'," + jsonStr(uuid) + "," + (okLoc && d != null) + ","
                        + jsonStr(d == null ? "没有 CCCD 描述符（只登记了本地通知）" : (cccd ? "CCCD 已写" : "CCCD 写没成功"))
                        + ")");
                return "ok:" + (cccd || d == null ? "subscribed" : "local_only");
            } catch (Throwable t) {
                return "err:" + t;
            }
        }

        @android.webkit.JavascriptInterface
        public String bleRead(final String uuid) {
            try {
                if (sGatt == null) return "err:还没连上";
                android.bluetooth.BluetoothGattCharacteristic ch = bleFind(uuid);
                if (ch == null) return "err:找不到这个特征值";
                if ((ch.getProperties() & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_READ) == 0)
                    return "err:这个特征值不支持读";
                boolean ok = sGatt.readCharacteristic(ch);
                return ok ? "ok:reading" : "err:系统不接受这次读（可能上一个操作还没完成）";
            } catch (Throwable t) {
                return "err:" + t;
            }
        }

        /** 写一帧：fmt = "hex"（支持 01 02 / 0102 / 0x01,0x02）或 "txt"（UTF-8）；mode = "req"（要应答）/ "cmd"（免应答） */
        @android.webkit.JavascriptInterface
        public String bleWrite(final String uuid, final String data, final String mode, final String fmt) {
            try {
                if (sGatt == null) return "err:还没连上";
                android.bluetooth.BluetoothGattCharacteristic ch = bleFind(uuid);
                if (ch == null) return "err:找不到这个特征值";
                int p = ch.getProperties();
                boolean wantCmd = "cmd".equals(mode);
                boolean canCmd = (p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0;
                boolean canReq = (p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_WRITE) != 0;
                int wt;
                if (wantCmd && canCmd) wt = android.bluetooth.BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE;
                else if (canReq) wt = android.bluetooth.BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT;
                else if (canCmd) wt = android.bluetooth.BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE;
                else return "err:这个特征值不支持写（也没有免应答写）";
                byte[] bytes;
                String d = (data == null) ? "" : data;
                if ("txt".equals(fmt)) {
                    bytes = d.getBytes("UTF-8");
                } else {
                    String h = d.replace("0x", "").replace("0X", "").replace(" ", "").replace(",", "").replace("-", "").replace(":", "");
                    if (h.length() == 0) return "err:没有内容";
                    if ((h.length() % 2) != 0) return "err:十六进制应该是偶数个字符（比如 01 02）";
                    if (!h.matches("[0-9a-fA-F]+")) return "err:十六进制里出现了非法字符";
                    bytes = new byte[h.length() / 2];
                    for (int i = 0; i < bytes.length; i++) {
                        bytes[i] = (byte) Integer.parseInt(h.substring(i * 2, i * 2 + 2), 16);
                    }
                }
                if (bytes.length == 0) return "err:没有内容";
                boolean ok;
                if (android.os.Build.VERSION.SDK_INT >= 33) {
                    ok = sGatt.writeCharacteristic(ch, bytes, wt) == android.bluetooth.BluetoothStatusCodes.SUCCESS;
                } else {
                    ch.setWriteType(wt);
                    ch.setValue(bytes);
                    ok = sGatt.writeCharacteristic(ch);
                }
                if (ok) jsCall("window.__om3ble&&window.__om3ble('wrote'," + jsonStr(uuid) + ","
                        + jsonStr(bleHex(bytes)) + "," + bytes.length + ")");
                return ok ? "ok:sent" : "err:系统不接受这次写（可能上一个操作还没完成）";
            } catch (Throwable t) {
                return "err:" + t;
            }
        }

        @android.webkit.JavascriptInterface
        public String bleMtu(final int mtu) {
            try {
                if (sGatt == null) return "err:还没连上";
                boolean ok = sGatt.requestMtu(mtu <= 0 ? 517 : mtu);
                return ok ? "ok:asking" : "err:系统不接受（可能上一个操作还没完成）";
            } catch (Throwable t) {
                return "err:" + t;
            }
        }

        @android.webkit.JavascriptInterface
        public String bleReadRemoteRssi() {
            try {
                if (sGatt == null) return "err:还没连上";
                boolean ok = sGatt.readRemoteRssi();
                return ok ? "ok:asking" : "err:系统不接受";
            } catch (Throwable t) {
                return "err:" + t;
            }
        }

        private android.bluetooth.BluetoothGattCharacteristic bleFind(String uuid) {
            try {
                if (sGatt == null || uuid == null) return null;
                java.util.UUID u = java.util.UUID.fromString(uuid.trim().toLowerCase());
                for (android.bluetooth.BluetoothGattService s : sGatt.getServices()) {
                    for (android.bluetooth.BluetoothGattCharacteristic c : s.getCharacteristics()) {
                        if (c.getUuid().equals(u)) return c;
                    }
                }
            } catch (Throwable t) { }
            return null;
        }

        /* 注：Bridge 是**内部类**（非 static）→ 这里不能写 static 方法（javac 会报"内部类中静态声明非法"） */
        private String bleHex(byte[] b) {
            if (b == null) return "";
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < b.length; i++) {
                String h = Integer.toHexString(b[i] & 0xFF);
                if (h.length() < 2) sb.append('0');
                sb.append(h);
            }
            return sb.toString();
        }

        /** 通知/读到的原始字节里挑出可打印字符（给页面显示"文本"那栏用） */
        private String bleText(byte[] b) {
            if (b == null) return "";
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < b.length; i++) {
                int c = b[i] & 0xFF;
                sb.append((c >= 32 && c < 127) || c == 10 || c == 13 ? (char) c : '.');
            }
            return sb.toString();
        }

        private android.bluetooth.BluetoothGattCallback bleCb() {
            return new android.bluetooth.BluetoothGattCallback() {
                @Override public void onConnectionStateChange(android.bluetooth.BluetoothGatt g, int status, int newState) {
                    try {
                        if (newState == android.bluetooth.BluetoothProfile.STATE_CONNECTED) {
                            jsCall("window.__om3ble&&window.__om3ble('connected'," + jsonStr(sGattMac) + "," + status + ")");
                            g.discoverServices();
                        } else if (newState == android.bluetooth.BluetoothProfile.STATE_DISCONNECTED) {
                            jsCall("window.__om3ble&&window.__om3ble('lost'," + jsonStr("连接断开（status=" + status + "）") + ")");
                        }
                    } catch (Throwable t) { }
                }

                @Override public void onServicesDiscovered(android.bluetooth.BluetoothGatt g, int status) {
                    try {
                        StringBuilder sb = new StringBuilder("[");
                        boolean first = true;
                        for (android.bluetooth.BluetoothGattService s : g.getServices()) {
                            if (!first) sb.append(",");
                            first = false;
                            sb.append("{\"uuid\":").append(jsonStr(s.getUuid().toString()))
                              .append(",\"type\":").append(s.getType())
                              .append(",\"chars\":[");
                            boolean f2 = true;
                            for (android.bluetooth.BluetoothGattCharacteristic c : s.getCharacteristics()) {
                                if (!f2) sb.append(",");
                                f2 = false;
                                int p = c.getProperties();
                                sb.append("{\"uuid\":").append(jsonStr(c.getUuid().toString()))
                                  .append(",\"props\":").append(p)
                                  .append(",\"read\":").append((p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_READ) != 0)
                                  .append(",\"write\":").append((p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_WRITE) != 0)
                                  .append(",\"wnr\":").append((p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0)
                                  .append(",\"notify\":").append((p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_NOTIFY) != 0)
                                  .append(",\"indicate\":").append((p & android.bluetooth.BluetoothGattCharacteristic.PROPERTY_INDICATE) != 0)
                                  .append(",\"cccd\":").append(c.getDescriptor(java.util.UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")) != null)
                                  .append("}");
                            }
                            sb.append("]}");
                        }
                        sGattSvcJson = sb.append("]").toString();
                        jsCall("window.__om3ble&&window.__om3ble('svc'," + jsonStr(sGattSvcJson) + "," + status + ")");
                    } catch (Throwable t) { }
                }

                @Override public void onCharacteristicChanged(android.bluetooth.BluetoothGatt g, android.bluetooth.BluetoothGattCharacteristic c, byte[] value) {
                    bleEmit("notify", c, value);
                }

                @Override public void onCharacteristicChanged(android.bluetooth.BluetoothGatt g, android.bluetooth.BluetoothGattCharacteristic c) {
                    try { bleEmit("notify", c, c.getValue()); } catch (Throwable t) { }
                }

                @Override public void onCharacteristicRead(android.bluetooth.BluetoothGatt g, android.bluetooth.BluetoothGattCharacteristic c, byte[] value, int status) {
                    bleEmit("read", c, value);
                }

                @Override public void onCharacteristicRead(android.bluetooth.BluetoothGatt g, android.bluetooth.BluetoothGattCharacteristic c, int status) {
                    try { bleEmit("read", c, c.getValue()); } catch (Throwable t) { }
                }

                @Override public void onCharacteristicWrite(android.bluetooth.BluetoothGatt g, android.bluetooth.BluetoothGattCharacteristic c, int status) {
                    try {
                        jsCall("window.__om3ble&&window.__om3ble('writeack'," + jsonStr(c.getUuid().toString()) + "," + status + ")");
                    } catch (Throwable t) { }
                }

                @Override public void onDescriptorWrite(android.bluetooth.BluetoothGatt g, android.bluetooth.BluetoothGattDescriptor d, int status) {
                    try {
                        jsCall("window.__om3ble&&window.__om3ble('cccd'," + jsonStr(d.getCharacteristic().getUuid().toString()) + "," + status + ")");
                    } catch (Throwable t) { }
                }

                @Override public void onMtuChanged(android.bluetooth.BluetoothGatt g, int mtu, int status) {
                    try {
                        sGattMtu = mtu;
                        sGattMtuTxt = "MTU=" + mtu + "（status=" + status + "）";
                        jsCall("window.__om3ble&&window.__om3ble('mtu'," + mtu + "," + status + ")");
                    } catch (Throwable t) { }
                }

                @Override public void onReadRemoteRssi(android.bluetooth.BluetoothGatt g, int rssi, int status) {
                    try { jsCall("window.__om3ble&&window.__om3ble('rssi'," + rssi + ")"); } catch (Throwable t) { }
                }
            };
        }

        private void bleEmit(String kind, android.bluetooth.BluetoothGattCharacteristic c, byte[] value) {
            try {
                String hex = bleHex(value);
                String txt = bleText(value);
                String u = (c == null) ? "" : c.getUuid().toString();
                jsCall("window.__om3ble&&window.__om3ble('" + kind + "'," + jsonStr(u) + ","
                        + jsonStr(hex) + "," + jsonStr(txt) + ")");
            } catch (Throwable t) { }
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

        /* 扫一遍附近的 Wi-Fi，把"像相机热点"的名字挑出来（用户 2026-09-24：
           「在我相机开启 wifi 时，点一下直接连到这个 wifi」）。
           权限：Android 13+ 用 NEARBY_WIFI_DEVICES，≤12 用 ACCESS_FINE_LOCATION（两个清单里都有）。
           返回：JSON 数组字符串 [{"ssid":"OM-3-1234567","level":-45,"cam":true}, ...]；失败给 err: 前缀。 */
        @JavascriptInterface
        public String wifiScanList() {
            try {
                WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                if (wm == null) return "[]";
                if (!wm.isWifiEnabled()) return "err:wifi_off";
                try { wm.startScan(); } catch (Throwable t) { /* 新系统上已废弃/受限，拿缓存结果也够用 */ }
                java.util.List<android.net.wifi.ScanResult> rs = null;
                try { rs = wm.getScanResults(); } catch (Throwable t) { return "err:no_scan:" + t.getMessage(); }
                if (rs == null) return "[]";
                /* 按信号强的前 24 个；同名只留一个（取信号最好的） */
                java.util.Collections.sort(rs, new java.util.Comparator<android.net.wifi.ScanResult>() {
                    @Override public int compare(android.net.wifi.ScanResult a, android.net.wifi.ScanResult b) {
                        return b.level - a.level;
                    }
                });
                java.util.LinkedHashMap<String, android.net.wifi.ScanResult> uniq =
                        new java.util.LinkedHashMap<String, android.net.wifi.ScanResult>();
                for (int i = 0; i < rs.size(); i++) {
                    android.net.wifi.ScanResult r = rs.get(i);
                    /* ⚠ 2026-09-24（第 34 轮）修：SSID **去掉两边的引号**。
                       官方 APK 里专门有个 convertSSID() 干这件事 —— 说明真机上拿到的 SSID 会带引号
                       （"\"OM-3 1234\""）。带引号时下面那个 cam 正则 ^(OM[- ]?\d… 会匹配失败，
                       于是相机热点永远标不出 📷 → 页面「连接相机」的直连第一条路永远走不通。
                       注意：去掉的是引号本身，SSID 内容不含引号，所以对本来就不带引号的设备无副作用。 */
                    String s = r.SSID == null ? "" : r.SSID.replace("\"", "");
                    if (s.length() == 0) continue;
                    if (!uniq.containsKey(s)) uniq.put(s, r);
                    if (uniq.size() >= 24) break;
                }
                StringBuilder sb = new StringBuilder("[");
                java.util.Iterator<java.util.Map.Entry<String, android.net.wifi.ScanResult>> it = uniq.entrySet().iterator();
                boolean first = true;
                while (it.hasNext()) {
                    java.util.Map.Entry<String, android.net.wifi.ScanResult> e = it.next();
                    String s = e.getKey();
                    boolean cam = s.matches("(?i)^(OM[- ]?\\d.*|OM[- ]?D.*|OMSYSTEM.*|E[- ]?M\\d.*|E[- ]?P\\d.*|STYLUS.*|PEN.*|Tough.*)");
                    /* r64：把 BSSID 一起给页面 —— 连接时"只连这一个 AP"要用它（官方也是从 ScanResult 取）。 */
                    String bs = "";
                    try { bs = camMacNorm(e.getValue().BSSID); } catch (Throwable t) { bs = ""; }
                    if (!first) sb.append(",");
                    first = false;
                    sb.append("{\"ssid\":").append(jsonStr(s))
                      .append(",\"level\":").append(e.getValue().level)
                      .append(",\"cam\":").append(cam ? "true" : "false")
                      .append(",\"bssid\":").append(jsonStr(bs)).append("}");
                }
                sb.append("]");
                return sb.toString();
            } catch (Throwable t) { return "err:" + t.getMessage(); }
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
            String r = camReqOnce(path, body, method, (sCamNet != null));
            if (r != null && r.startsWith("{\"s\":0,")
                    && (r.indexOf("EPERM") >= 0 || r.indexOf("Binding socket") >= 0
                        || r.indexOf("SecurityException") >= 0)) {
                /* r78：**真机日志里出现 16 次**：
                   `ERR SocketException: Binding socket to network 254 failed: EPERM (Operation not permitted)`
                   —— 我们缓存的 sCamNet 在"相机休眠/断开"之后就**过期**了，绑上去内核直接拒。
                   时间线（logs/OM3-真机-2026-09-28-2232.txt）：22:27:37 掉线 → 22:28:04~08 连续 15 条 EPERM
                   → 22:28:57 重新 requestNetwork 后 22:29:01 又 HTTP 200。
                   所以：**丢掉过期句柄 + 退到默认路由重试一次**（手机连的就是相机热点，默认路由也通），
                   并把"退到默认路由"写进结果里，页面上能一眼看出来。 */
                sCamNet = null;
                String r2 = camReqOnce(path, body, method, false);
                if (r2 != null && !r2.startsWith("{\"s\":0,")) {
                    return r2.substring(0, r2.length() - 1) + ",\"w\":\"bind_fail→default\"}";
                }
                return r2;
            }
            return r;
        }

        /** 发一次请求；bound=true 时用 sCamNet（绑在相机那条网络），false 时走默认路由 */
        private String camReqOnce(String path, byte[] body, String method, boolean bound) {
            try {
                java.net.URL u = new java.net.URL("http://192.168.0.10/" + path);
                java.net.HttpURLConnection c = (java.net.HttpURLConnection)
                        ((bound && sCamNet != null) ? sCamNet.openConnection(u) : u.openConnection());
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
           断开或退出后自动回到原来的 Wi-Fi。凭据存在页面里，下次不用再扫。
           r64：官方用的是 **SSID + BSSID**（钉住那一个 AP）→ 新增 connectCamera2(ssid, pass, bssid)，
           老方法 connectCamera(ssid, pass) 保留（内部转调、行为不变）。 */
        private android.net.Network sCamNet = null;          /* Bridge 是内部类，不能用 static */
        private android.net.ConnectivityManager.NetworkCallback sCamCb = null;

        private void jsCall(final String code) { jscall(code); }

        private String wifiPerm() {
            return Build.VERSION.SDK_INT >= 33
                    ? "android.permission.NEARBY_WIFI_DEVICES"
                    : "android.permission.ACCESS_FINE_LOCATION";
        }

        /** 请系统连相机热点（**只按 SSID**）：asking / connected 由页面回调，need_perm 需要先授权 */
        @JavascriptInterface
        public String connectCamera(final String ssid, final String pass) {
            return connectCamera2(ssid, pass, null);
        }

        /** 同 connectCamera，但可以**再钉住一个 BSSID**（第 64 轮新增）。
         *
         *  为什么要有它：官方 APK 连相机热点用的是 SSID **+ BSSID**（`J2/e$b.run`：
         *  `str.wifi.camera.bssid` → `WifiNetworkSpecifier.Builder.setBssid(MacAddress.fromString(...))`）。
         *  只给 SSID 时系统会在"所有叫这个名字的 AP"里挑 —— 扫到过同名残留热点/邻居同名热点时可能连错，
         *  连错了相机 HTTP（192.168.0.10）自然不通。给 BSSID = 只连那一个。
         *
         *  ⚠ 照官方两处细节：① **只有 SDK_INT > 30 才设 BSSID**（官方 `const/16 30` + `if-ge`：
         *  "Android 11 以前不做"）；② 不合法就当没给，**不许因为 BSSID 让连接失败**。
         *
         *  返回值与 connectCamera 完全一致，**外加后缀 `@bssid`**（仅当这次真的把 BSSID 交给系统时）
         *  —— 页面据此如实说明"按 SSID+BSSID 连"还是"只按 SSID 连"。
         */
        @JavascriptInterface
        public String connectCamera2(final String ssid, final String pass, final String bssid) {
            if (ssid == null || ssid.length() == 0) return "bad_ssid";
            lastSsid = ssid;
            lastPass = (pass == null) ? "" : pass;
            lastBssid = camMacNorm(bssid);
            boolean pinned = false;
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
                pendBssid = bssid;                 /* r64：授权回来时按同一个 BSSID 重连 */
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
            /* r64：有 BSSID 且**系统版本够**就钉住它（照官方：SDK_INT > 30 才 setBssid） */
            if (lastBssid != null && lastBssid.length() > 0) {
                if (Build.VERSION.SDK_INT > 30) {
                    try {
                        b.setBssid(android.net.MacAddress.fromString(lastBssid));
                        pinned = true;
                    } catch (Throwable t) {
                        /* 只是"没法更精确"，不能让连接失败 */
                        android.util.Log.w("OM3", "setBssid 失败（" + lastBssid + "）：" + t);
                    }
                } else {
                    android.util.Log.i("OM3", "有 BSSID(" + lastBssid + ") 但 SDK=" + Build.VERSION.SDK_INT
                            + " ≤ 30 → 按官方做法不设，只按 SSID 连");
                }
            }
            android.net.NetworkRequest req = new android.net.NetworkRequest.Builder()
                    .addTransportType(android.net.NetworkCapabilities.TRANSPORT_WIFI)
                    .setNetworkSpecifier(b.build())
                    .build();
            sCamCb = new android.net.ConnectivityManager.NetworkCallback() {
                @Override public void onAvailable(android.net.Network n) {
                    sCamNet = n;
                    jsCall("window.__om3camState&&window.__om3camState('connected')");
                    /* r64：顺便问一句"实际连到哪个 AP"（拿不到就算了，绝不影响连接） */
                    try {
                        android.net.ConnectivityManager c2 = (android.net.ConnectivityManager)
                                getSystemService(Context.CONNECTIVITY_SERVICE);
                        camNoteBssid(c2 == null ? null : c2.getNetworkCapabilities(n));
                    } catch (Throwable t) { }
                }
                /* r64：官方就是在 onCapabilitiesChanged 里存 BSSID 的（dis.txt 51570~51635） */
                @Override public void onCapabilitiesChanged(android.net.Network n, android.net.NetworkCapabilities caps) {
                    try { camNoteBssid(caps); } catch (Throwable t) { }
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
            return pinned ? "asking@bssid" : "asking";
        }

        private String lastSsid = "", lastPass = "";
        /* r64：已知/已连上的 BSSID（`AA:BB:CC:DD:EE:FF`，拿不到就是空串）。
           NetworkCallback 在系统线程写、JS 线程读 → volatile。 */
        private volatile String lastBssid = "";

        /** r64：把 BSSID 规范成合法大写 MAC；不合法（或系统给的假值）一律返回 ""。
         *  系统在"权限不够/拿不到真值"时会给出 02:00:00:00:00:00 这类占位值。 */
        private String camMacNorm(String mac) {
            try {
                if (mac == null) return "";
                String s = mac.trim().toUpperCase();
                if (!s.matches("[0-9A-F]{2}(:[0-9A-F]{2}){5}")) return "";
                if ("00:00:00:00:00:00".equals(s) || "FF:FF:FF:FF:FF:FF".equals(s)
                        || "02:00:00:00:00:00".equals(s)) return "";
                return s;
            } catch (Throwable t) { return ""; }
        }

        /** r64：连上之后，把"实际连到哪个 AP"的 BSSID 回给页面（照官方 J2/e$c.onCapabilitiesChanged）。
         *
         *  官方判据（dis.txt 51570~51635）逐条照搬：
         *    ① Android 11 以前什么都不做（日志原文「Android11以前は何もしない」）；
         *    ② SSID / BSSID 有一个是空 → 不做；
         *    ③ BSSID **以 "00:00" 结尾** → 假值，不做；
         *    ④ **SSID 必须等于本次请求的那个**（官方 `f$a.b.equals(ssid)`）→ 别把别的网络报成相机；
         *    ⑤ 值没变就不重复推。
         *  ⚠ 官方在这里还多要求"prefBSSID 非空才更新"（即只更新、不首次写入）—— 我们**故意放宽**：
         *    首次连上就把真值记下来更有用，而且我们存的是"这是一台相机连过的热点"，没有别的歧义。
         */
        private void camNoteBssid(android.net.NetworkCapabilities caps) {
            try {
                if (Build.VERSION.SDK_INT < 30) return;                 /* ① 官方：Android 11 以前不做 */
                if (caps == null) return;
                android.net.TransportInfo ti = caps.getTransportInfo();
                if (!(ti instanceof WifiInfo)) return;
                WifiInfo wi = (WifiInfo) ti;
                String ssid = wi.getSSID();
                String bssid = wi.getBSSID();
                if (ssid == null) ssid = ""; else ssid = ssid.replace("\"", "");
                if (bssid == null) bssid = "";
                if (ssid.length() == 0 || bssid.length() == 0) return;    /* ② */
                if (bssid.endsWith("00:00")) return;                      /* ③ */
                if (lastSsid != null && lastSsid.length() > 0 && !lastSsid.equals(ssid)) return;   /* ④ */
                String b = camMacNorm(bssid);
                if (b.length() == 0) return;
                if (b.equals(lastBssid)) return;                          /* ⑤ 没变不重复推 */
                lastBssid = b;
                jsCall("window.__om3camBssid&&window.__om3camBssid("
                        + jsonStr(ssid) + "," + jsonStr(b) + ",\"cap\")");
            } catch (Throwable t) { }
        }

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

        /** {"connected":true,"ssid":"OM-3-…","bssid":"AA:BB:…"}（r64：多了 bssid，拿不到就是空串） */
        @JavascriptInterface
        public String cameraState() {
            /* 只报我们自己发起的连接：不碰 getConnectionInfo，避免一直触发定位查询 */
            return "{\"connected\":" + (sCamNet != null) + ",\"ssid\":" + jsonStr(lastSsid)
                 + ",\"bssid\":" + jsonStr(lastBssid) + "}";
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
