# -*- coding: utf-8 -*-
"""给 GitHub 上的 README 产截图（一次性用；跑完可删）。

做法：headless Chrome 整屏截图，手机尺寸 412×900、2 倍像素密度；
      注入一小段脚本切到指定页签/滚动位置。
"""
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
OUT = os.path.join(ROOT, 'screenshots')
os.makedirs(OUT, exist_ok=True)
src = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()

# 名字, 切页签/滚动的脚本, 宽, 高, 缩放
SHOTS = [
    ('1-home',        "window.scrollTo(0,0);", 412, 900, 2),
    ('3-connect',     "setTimeout(function(){var t=document.getElementById('tabCam');"
                      "if(t)t.click();window.scrollTo(0,0);},600);", 412, 900, 2),
    ('4-gear',        "setTimeout(function(){var t=document.getElementById('tabB');"
                      "if(t)t.click();window.scrollTo(0,0);},600);", 412, 900, 2),
]


def build(name, js):
    i = src.find('<body')
    j = src.find('>', i) + 1
    inject = ('<script>window.__OM3_APP__=1;window.__errs=[];'
              # 只为截图：顶栏用了 margin:0 -16px（比视口宽 32px），不挡掉右边会被切
              "setTimeout(function(){"
              "var tb=document.querySelector('.topbar');"
              "if(tb){tb.style.marginLeft='0';tb.style.marginRight='0';}"   # 消掉 -16px 的横向溢出
              "document.body.style.overflowX='hidden';},1500);"
              # 只为截图：页面顶栏用了 margin:0 -16px，比视口宽 32px，不挡掉的话右边会被切
              "document.documentElement.style.overflowX='hidden';"
              "document.addEventListener('DOMContentLoaded',function(){document.body.style.overflowX='hidden';});"
              "window.addEventListener('error',function(e){window.__errs.push(e.message);});"
              "setTimeout(function(){try{" + js + "}catch(e){document.title='ERRSHOT:'+e.message;}},2200);"
              '</script>')
    p = os.path.join(TMP, 'shot_%s.html' % name)
    io.open(p, 'w', encoding='utf-8', newline='').write(src[:j] + inject + src[j:])
    return p


for name, js, w, h, sc in SHOTS:
    page = build(name, js)
    png = os.path.join(OUT, name + '.png')
    ud = os.path.join(TMP, 'shotprof_' + name)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                        '--user-data-dir=' + ud, '--window-size=%d,%d' % (w, h),
                        '--force-device-scale-factor=%d' % sc,
                        '--virtual-time-budget=9000', '--screenshot=' + png,
                        'file:///' + page.replace(os.sep, '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
    ok = os.path.exists(png)
    print('%-12s %s  %s' % (name, ('%.0f KB' % (os.path.getsize(png) / 1024.0)) if ok else '失败', (r.stderr or '')[-120:].strip()))


# ---- 配方卡：两趟截图（先量卡高，再按高截图；等懒加载图片落位）----
CARD_JS = ("document.querySelectorAll('img[data-im]').forEach(function(im){"
           "im.loading='eager';});"
           "setTimeout(function(){"
           "var n=document.querySelector('.card[id^=r-]');"
           "var w=document.createElement('div');w.id='SHOTCARD';"
           "w.style.cssText='margin:0;padding:0;width:412px;background:#141414;';"
           "w.appendChild(n);document.body.appendChild(w);"
           "document.body.style.padding='0';document.body.style.margin='0';"
           "Array.prototype.forEach.call(document.body.children,function(c){if(c!==w)c.style.display='none';});"
           "document.documentElement.style.background='#141414';document.body.style.background='#141414';"
           "setTimeout(function(){document.title='H='+Math.ceil(n.getBoundingClientRect().height);},900);"
           "},3500);")

page = build('card', CARD_JS)
ud = os.path.join(TMP, 'shotprof_card')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,1400', '--virtual-time-budget=12000',
                    '--dump-dom', 'file:///' + page.replace(os.sep, '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
import re
m = re.search(r'<title>H=(\d+)</title>', r.stdout or '')
h = int(m.group(1)) + 8 if m else 760
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
png = os.path.join(OUT, '2-recipe.png')
subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                '--user-data-dir=' + ud, '--window-size=412,%d' % h, '--force-device-scale-factor=2',
                '--virtual-time-budget=12000', '--screenshot=' + png,
                'file:///' + page.replace(os.sep, '/')],
               capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
print('2-recipe     %s（卡高 %d px，2 倍）' % ('%.0f KB' % (os.path.getsize(png) / 1024.0), h))
