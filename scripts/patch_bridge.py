# -*- coding: utf-8 -*-
"""根因修复：WebView 里 file:// 页面拿不到摄像头（getUserMedia 一直挂着，也不弹权限）。
- 页面改从 https://om3.local/ 虚拟源加载（安全上下文 → 摄像头可用）
- 相机 HTTP 全部改走原生桥（HttpURLConnection，绕开 https 页面的 CORS 限制）
- 扫码加 3 秒看门狗，失败会明确报错而不是干等
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
APK = TMP + r'\apk'
P = TMP + r'\app\base.html'

# ============================================================ 1. MainActivity
p = APK + r'\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()
open(APK + r'\java\com\om3\handbook\MainActivity.before_https.java', 'w', encoding='utf-8', newline='').write(j)
assert 'om3.local' not in j

# 1a) imports
j = j.replace('import android.net.wifi.WifiInfo;',
              'import android.net.Uri;\nimport android.net.wifi.WifiInfo;', 1)
j = j.replace('import android.webkit.WebViewClient;',
              'import android.webkit.WebResourceRequest;\nimport android.webkit.WebResourceResponse;\nimport android.webkit.WebViewClient;', 1)

# 1b) WebViewClient：把 https://om3.local/... 映射到 assets（这样页面是安全源，摄像头才给用）
OLD_CLIENT = '''        wv.setWebViewClient(new WebViewClient());'''
assert j.count(OLD_CLIENT) == 1
NEW_CLIENT = '''        wv.setWebViewClient(new WebViewClient() {
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
        });'''
j = j.replace(OLD_CLIENT, NEW_CLIENT, 1)

# 1c) 改从虚拟 https 源加载页面
OLD_LOAD = '''        wv.loadUrl("file:///android_asset/index.html");'''
assert j.count(OLD_LOAD) == 1
j = j.replace(OLD_LOAD, '''        // 用 https 虚拟源加载本页：WebView 只在安全上下文里给摄像头（file:// 会一直挂住）
        wv.loadUrl("https://om3.local/index.html");''', 1)

# 1d) 桥里加相机 HTTP（原生请求，不受页面 CORS/明文限制）
OLD_BRIDGE = '''        /** 页面要调摄像头扫码时先问这个：ok / need_perm:xxx */'''
assert j.count(OLD_BRIDGE) == 1
NEW_BRIDGE = '''        /* ---------- 相机 HTTP：由原生发起，绕开页面的 CORS / 混合内容限制 ---------- */

        private String jsonStr(String s) {
            if (s == null) s = "";
            StringBuilder sb = new StringBuilder("\\"");
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                switch (c) {
                    case '"':  sb.append("\\\\\\""); break;
                    case '\\\\': sb.append("\\\\\\\\"); break;
                    case '\\n': sb.append("\\\\n"); break;
                    case '\\r': sb.append("\\\\r"); break;
                    case '\\t': sb.append("\\\\t"); break;
                    default:
                        if (c < 0x20) sb.append(String.format("\\\\u%04x", (int) c));
                        else sb.append(c);
                }
            }
            return sb.append('"').toString();
        }

        private String camReq(String path, byte[] body, String method) {
            try {
                java.net.HttpURLConnection c = (java.net.HttpURLConnection)
                        new java.net.URL("http://192.168.0.10/" + path).openConnection();
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
                return "{\\"s\\":" + code + ",\\"t\\":" + jsonStr(new String(bo.toByteArray(), "UTF-8")) + "}";
            } catch (Throwable t) {
                String msg = "ERR " + t.getClass().getSimpleName()
                        + (t.getMessage() == null ? "" : (": " + t.getMessage()));
                return "{\\"s\\":0,\\"t\\":" + jsonStr(msg) + "}";
            }
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
                return "{\\"s\\":0,\\"t\\":" + jsonStr("bad body: " + t) + "}";
            }
        }

        /** 页面要调摄像头扫码时先问这个：ok / need_perm:xxx */'''
j = j.replace(OLD_BRIDGE, NEW_BRIDGE, 1)
open(p, 'w', encoding='utf-8', newline='').write(j)
print('MainActivity: 虚拟 https 源 + 原生相机 HTTP 桥（camGet/camPost）已加')

# ============================================================ 2. 页面：req 走桥
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_bridge.html', 'w', encoding='utf-8', newline='').write(h)

i = h.find('  /* 相机 API 是明文 HTTP；桌面版没有这个页签，所以不用考虑 CORS */')
k = h.find('\n  function sleep(ms)', i)
assert i > 0 and k > i, (i, k)
OLD_REQ = h[i:k]
NEW_REQ = '''  /* 相机请求：手机端走原生桥（不受 https 页面的 CORS 限制）；桌面/浏览器退回 XHR */
  function b64(bytes){
    var s = '', CH = 0x8000;
    for(var i=0;i<bytes.length;i+=CH) s += String.fromCharCode.apply(null, bytes.subarray(i, i+CH));
    return btoa(s);
  }
  function req(path, opt){
    opt = opt || {};
    if(Native && Native.camGet){
      return new Promise(function(resolve, reject){
        var raw = '';
        try{
          raw = opt.body ? String(Native.camPost(path, b64(opt.body)))
                         : String(Native.camGet(path));
        }catch(e){ reject(new Error(String(e))); return; }
        var j = {};
        try{ j = JSON.parse(raw); }catch(e){ reject(new Error('原生桥返回异常')); return; }
        if(!j || !j.s) reject(new Error((j && j.t) ? j.t : '连不上相机'));
        else resolve({status:j.s, text:j.t || '', url:BASE + path});
      });
    }
    return new Promise(function(resolve, reject){
      var x = new XMLHttpRequest(), done = false;
      var url = BASE + path;
      x.open(opt.method || 'GET', url, true);
      x.timeout = opt.timeout || 8000;
      x.onreadystatechange = function(){
        if(x.readyState !== 4 || done) return;
        done = true;
        resolve({status:x.status, text:x.responseText||'', url:url});
      };
      x.ontimeout = function(){ if(!done){ done = true; reject(new Error('超时（相机没应答）')); } };
      x.onerror = function(){ if(!done){ done = true; reject(new Error('连不上 '+BASE)); } };
      if(opt.body){
        x.setRequestHeader('Content-Type','application/octet-stream');
        x.send(opt.body);
      } else x.send();
    });
  }'''
h = h[:i] + NEW_REQ + h[k:]

# 2b) 扫码看门狗：3 秒没画面就明确报错
OLD_SCAN = """        scanRAF = requestAnimationFrame(tick);
      }, function(err){"""
assert h.count(OLD_SCAN) == 1
h = h.replace(OLD_SCAN, """        scanRAF = requestAnimationFrame(tick);
        setTimeout(function(){
          if(!scanStream){
            var so = document.getElementById('scanOut');
            so.innerHTML = '';
            line(so, '摄像头 3 秒内没有画面：这个 WebView 不给摄像头权限，或者被系统拦了。', 'err');
            line(so, '先把相机权限给到「本 app」（设置 → 应用 → OM-3 色彩配方 → 权限 → 相机），再点一次；还是不行就把这段日志发我。', 'warn');
            stopScan();
          }
        }, 3000);
      }, function(err){""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：相机请求改走原生桥 + 扫码看门狗，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
