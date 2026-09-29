# -*- coding: utf-8 -*-
"""APK 侧改动：允许访问相机 Wi-Fi 上的明文 HTTP（192.168.0.10）+ WebView 允许 file:// 页面跨域请求。"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
APK = r'C:\Users\82302\AppData\Local\Temp\apk'

# ---------- 1. AndroidManifest.xml ----------
p = APK + r'\AndroidManifest.xml'
m = open(p, encoding='utf-8').read()
open(APK + r'\AndroidManifest.before_camera.xml', 'w', encoding='utf-8', newline='').write(m)
if 'android.permission.INTERNET' not in m:
    m = m.replace('    <uses-sdk', '    <uses-permission android:name="android.permission.INTERNET" />\n'
                                  '    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />\n'
                                  '    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />\n'
                                  '    <uses-permission android:name="android.permission.CHANGE_WIFI_STATE" />\n\n'
                                  '    <uses-sdk', 1)
if 'usesCleartextTraffic' not in m:
    m = m.replace('        android:hardwareAccelerated="true"',
                  '        android:hardwareAccelerated="true"\n        android:usesCleartextTraffic="true"', 1)
open(p, 'w', encoding='utf-8', newline='').write(m)
print('AndroidManifest: INTERNET/网络权限 =', 'INTERNET' in m, '| 明文 HTTP =', 'usesCleartextTraffic' in m)

# ---------- 2. MainActivity.java ----------
p = APK + r'\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()
open(APK + r'\java\com\om3\handbook\MainActivity.before_camera.java', 'w', encoding='utf-8', newline='').write(j)
OLD = '        s.setAllowContentAccess(true);'
assert j.count(OLD) == 1
j = j.replace(OLD, OLD + '''
        // 允许 file:///android_asset 页面直接请求相机 Wi-Fi 上的 http://192.168.0.10/（明文 HTTP）
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);''', 1)
open(p, 'w', encoding='utf-8', newline='').write(j)
print('MainActivity: 跨域设置 =', 'setAllowUniversalAccessFromFileURLs' in j and 'MIXED_CONTENT_ALWAYS_ALLOW' in j)

# ---------- 3. 资源注入小工具（APK 里打开「导入相机」页签）----------
mk = r'''# -*- coding: utf-8 -*-
"""把 app/index.html 复制成 apk/assets/index.html，并注入「这是 app 版」标记。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
src = r'C:\Users\82302\AppData\Local\Temp\app\index.html'
dst = r'C:\Users\82302\AppData\Local\Temp\apk\assets\index.html'
h = open(src, encoding='utf-8').read()
flag = '<script>window.__OM3_APP__=1;</script>\n'
i = h.find('<body')
j = h.find('>', i) + 1
h = h[:j] + flag + h[j:]
open(dst, 'w', encoding='utf-8', newline='').write(h)
print('assets/index.html %.1f MB（已注入 app 标记）' % (len(h.encode()) / 1048576))
'''
open(APK + r'\mkasset.py', 'w', encoding='utf-8', newline='').write(mk)
print('已生成 apk/mkasset.py')
