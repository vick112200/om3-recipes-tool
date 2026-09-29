# -*- coding: utf-8 -*-
"""把 app/index.html 变成单文件：图片缩到 WIDTH 宽，一次性注入 window.IMGMAP。"""
import os, re, sys, base64, io
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
SRC = os.path.join(BASE, 'app', 'index.html')
SRCIMG = os.path.join(BASE, 'imgs960')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'single.html')
WIDTH = int(sys.argv[2]) if len(sys.argv) > 2 else 480
Q = int(sys.argv[3]) if len(sys.argv) > 3 else 78

h = open(SRC, encoding='utf-8').read()
files = sorted(set(re.findall(r'data-im="([^"]+)"', h)) | set(re.findall(r'"f":"([A-Za-z0-9_\-\.]+\.jpg)"', h)))
print('唯一图片', len(files))
missing = [f for f in files if not os.path.exists(os.path.join(SRCIMG, f))]
if missing:
    print('缺失', missing[:5])
    files = [f for f in files if f not in missing]

parts = []
total = 0
for fn in files:
    im = Image.open(os.path.join(SRCIMG, fn)).convert('RGB')
    if im.width > WIDTH:
        im = im.resize((WIDTH, max(1, round(im.height * WIDTH / im.width))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=Q, optimize=True, progressive=True)
    b = buf.getvalue()
    total += len(b)
    parts.append('"%s":"data:image/jpeg;base64,%s"' % (fn, base64.b64encode(b).decode('ascii')))

print('重编码 %.1f MB，base64 后 %.1f MB' % (total / 1048576, total * 4 / 3 / 1048576))
mapjs = 'window.IMGMAP={' + ','.join(parts) + '};'
i = h.rfind('<script>window.SC=')
assert i > 0, '找不到注入点'
h = h[:i] + '<script>' + mapjs + '</script>\n' + h[i:]

open(OUT, 'w', encoding='utf-8', newline='').write(h)
print('输出 %s  %.1f MB' % (OUT, os.path.getsize(OUT) / 1048576))
