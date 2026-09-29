# -*- coding: utf-8 -*-
"""补回被误删的原生相机 HTTP 桥 + 连接辅助方法。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = r'C:\Users\82302\AppData\Local\Temp\apk\java\com\om3\handbook\MainActivity.java'
s = open(p, encoding='utf-8').read()

anchor = '        @JavascriptInterface\n        public String camGet(String path) {'
assert s.count(anchor) == 1
ADD = '''        private android.net.Network sCamNet = null;
        private android.net.ConnectivityManager.NetworkCallback sCamCb = null;

        private void jsCall(final String code) { jscall(code); }

        private String wifiPerm() {
            return Build.VERSION.SDK_INT >= 33
                    ? "android.permission.NEARBY_WIFI_DEVICES"
                    : "android.permission.ACCESS_FINE_LOCATION";
        }

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
                return "{\\"s\\":" + code + ",\\"t\\":" + jsonStr(new String(bo.toByteArray(), "UTF-8")) + "}";
            } catch (Throwable t) {
                String msg = "ERR " + t.getClass().getSimpleName()
                        + (t.getMessage() == null ? "" : (": " + t.getMessage()));
                return "{\\"s\\":0,\\"t\\":" + jsonStr(msg) + "}";
            }
        }

'''
s = s.replace(anchor, ADD + anchor, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('已补回 jsonStr / camReq / sCamNet / camCb / jsCall / wifiPerm')
