# -*- coding: utf-8 -*-
"""打包前自动递增 versionCode / versionName，并把版本号写进 APK 的 index.html 页脚。"""
import datetime
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
MF = os.path.join(BASE, 'AndroidManifest.xml')

h = open(MF, encoding='utf-8').read()
m = re.search(r'android:versionCode="(\d+)"', h)
assert m, 'AndroidManifest.xml 里找不到 versionCode'
code = int(m.group(1)) + 1
# 自 2026-09-25（第 46 轮）起版本号进入 3.x：code 300 → 3.0，301 → 3.1，302 → 3.2 ……
# （第 16–45 轮是 2.x：code 200 → 2.0；再早是 name = '1.%d' % code）
minor = code - 300
if minor < 0: minor = 0            # 万一把 manifest 写回 2xx，也不要出现负数版本名
name = '3.%d' % minor

h = re.sub(r'android:versionCode="\d+"', 'android:versionCode="%d"' % code, h)
h = re.sub(r'android:versionName="[^"]*"', 'android:versionName="%s"' % name, h)
open(MF, 'w', encoding='utf-8', newline='').write(h)

HP = os.path.join(BASE, 'assets', 'index.html')
if os.path.exists(HP):
    d = open(HP, encoding='utf-8').read()
    css = ('.appver{text-align:center;color:#6e6e6e;font-size:11.5px;line-height:1.9;'
           'padding:20px 14px 30px;margin-top:22px;border-top:1px solid #2b2b2b}'
           '.appver b{color:#8fd8c2}')
    if '.appver{' not in d:
        i = d.rfind('</style>')
        d = d[:i] + css + d[i:]
    d = re.sub(r'<div class="appver">.*?</div>\s*', '', d, flags=re.S)
    # 注意：界面里**不许出现日期/"桌面版"字样**（用户明确要求），徽标只留版本号
    badge = ('<div class="appver">OM-3 色彩配方 App <b>v%s</b>（build %d）</div>'
             % (name, code))
    d = d.replace('</body>', badge + '\n</body>', 1)
    open(HP, 'w', encoding='utf-8', newline='').write(d)
    print('已写入版本徽标 v%s (build %d)' % (name, code))
else:
    print('未找到 assets/index.html，只递增版本号')

print('VERSION=%s VERSIONCODE=%d' % (name, code))
