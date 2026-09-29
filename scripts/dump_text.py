# -*- coding: utf-8 -*-
"""推演用：把某个元素**用户实际看得见**的文字整块打出来（innerText 会自动跳过 display:none 的：
  收起 .hid49 的、tab 未选中的、折叠 <details> 里的——正是"用户第一眼看到什么"）。
用法：python scripts/dump_text.py '#paneD' ["前置JS"]  （只读，不改文件）
"""
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
sel = sys.argv[1] if len(sys.argv) > 1 else '#paneD'
pre = sys.argv[2] if len(sys.argv) > 2 else "document.getElementById('tabCam').click();"
page = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()
tail = ('<script>setTimeout(function(){var e=document.querySelector(%r);var d=document.createElement("pre");'
        'd.id="TXT";d.textContent=e?e.innerText:"(找不到元素)";document.body.appendChild(d);},2600);</script>' % sel)
i0 = page.find('<body')
j0 = page.find('>', i0) + 1
out = (page[:j0] + '<script>window.__OM3_APP__=1;'
       'try{%s}catch(e){}</script>' % pre + page[j0:].replace('</body>', tail + '</body>', 1))
hp = os.path.join(TMP, 'dump_text.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'odt')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                    '--virtual-time-budget=20000', '--dump-dom', 'file:///' + hp.replace(os.sep, '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=240)
dom = r.stdout or ''
k = dom.find('id="TXT"')
txt = dom[k:].split('>', 1)[1].split('</pre>')[0] if k >= 0 else '(没拿到输出)'
txt = (txt.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
          .replace('&quot;', '"').replace('&#39;', "'"))
lines = [l.rstrip() for l in txt.split('\n')]
print('=== %s 用户看得见的文字（前置JS：%s）===' % (sel, pre))
n = 0
for l in lines:
    if l.strip():
        n += 1
        print('%3d| %s' % (n, l))
print('（以上 %d 行）' % n)
