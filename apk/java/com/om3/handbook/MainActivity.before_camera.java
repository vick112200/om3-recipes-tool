package com.om3.handbook;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.webkit.ValueCallback;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

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
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(false);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(true);
        s.setTextZoom(100);
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

    @Override
    protected void onDestroy() {
        if (wv != null) {
            wv.destroy();
            wv = null;
        }
        super.onDestroy();
    }
}
