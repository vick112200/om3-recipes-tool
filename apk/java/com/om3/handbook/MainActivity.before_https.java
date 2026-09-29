package com.om3.handbook;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
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
import android.webkit.WebViewClient;
import android.widget.Toast;

public class MainActivity extends Activity {

    private WebView wv;

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
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(true);
        s.setTextZoom(100);
        wv.addJavascriptInterface(new Bridge(), "OM3Native");
        // 让页面能用 <video> 调摄像头扫码
        wv.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    @Override public void run() { request.grant(request.getResources()); }
                });
            }
        });
        wv.setWebViewClient(new WebViewClient());
        wv.setBackgroundColor(0xFF161616);
        wv.setOverScrollMode(View.OVER_SCROLL_NEVER);

        setContentView(wv);
        wv.loadUrl("file:///android_asset/index.html");
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
                    if (wi != null && wi.getSSID() != null) ssid = wi.getSSID().replace("\"", "");
                }
                return "{\"wifi\":" + on + ",\"ssid\":\"" + ssid + "\",\"sdk\":" + Build.VERSION.SDK_INT + "}";
            } catch (Throwable t) {
                return "{\"error\":\"" + t.getClass().getSimpleName() + "\"}";
            }
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
    protected void onDestroy() {
        if (wv != null) {
            wv.destroy();
            wv = null;
        }
        super.onDestroy();
    }
}
