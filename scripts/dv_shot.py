# -*- coding: utf-8 -*-
"""把某个元素单独「抠」出来截图，用来肉眼核对布局（色轮那一列/空白）。

用法：python scripts/dv_shot.py 输出png [选择器] [宽] [高] [app|desktop]
默认：选择器 .card[id^=r-]（第一张配方卡）、412x1400、app 模式
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

out = sys.argv[1] if len(sys.argv) > 1 else (SRC + r'\_shot.png')
sel = sys.argv[2] if len(sys.argv) > 2 else '.card[id^=r-]'
w = sys.argv[3] if len(sys.argv) > 3 else '412'
h = sys.argv[4] if len(sys.argv) > 4 else '1400'
appmode = not (len(sys.argv) > 5 and sys.argv[5] == 'desktop')

head = "<script>" + ("window.__OM3_APP__=1;" if appmode else "") + "</script>"

# 等待渲染完成 → 把目标元素抠到一个独立容器里 → 隐藏其它所有顶层节点 → 画个外框便于看边界
tail = ("<script>setTimeout(function(){"
        "var n=document.querySelector(%r);"
        "if(!n){document.title='NOTFOUND';return;}"
        "var wrap=document.createElement('div');wrap.id='SHOT';"
        "wrap.style.cssText='padding:0;margin:0;background:#141414;width:'+%s+'px';"
        "wrap.appendChild(n);"
        "document.body.appendChild(wrap);"
        "document.body.style.padding='0';"
        "Array.prototype.forEach.call(document.body.children,function(c){"
        "  if(c!==wrap)c.style.display='none';});"
        "document.documentElement.style.background='#141414';"
        "document.body.style.background='#141414';"
        "window.scrollTo(0,0);"
        "},2600);</script>") % (sel, w)

i = src.find('<body')
j = src.find('>', i) + 1
out_html = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_shot.html'
open(p, 'w', encoding='utf-8', newline='').write(out_html)

ud = TMP + r'\oshot'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=%s,%s' % (w, h),
                    '--virtual-time-budget=15000',
                    '--screenshot=' + out,
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
print('渲染模式=%s 选择器=%s 尺寸=%sx%s' % ('app' if appmode else 'desktop', sel, w, h))
print('截图 →', out)
print('Chrome stderr:', (r.stderr or '')[-300:])
