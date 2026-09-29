# -*- coding: utf-8 -*-
"""从 om-recipes.com 抓某条配方的原图，检查 MakerNote 是否带配方标签（0x2020 type3 count14）。"""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
PAT = b'\x20\x20\x03\x00\x0e\x00\x00\x00'
SLUGS = sys.argv[1:] or ['murder_pink_real']
for slug in SLUGS:
    url = 'https://om-recipes.com/recipes/' + slug
    html = subprocess.run(['curl', '-sL', '--max-time', '40', url],
                          capture_output=True).stdout.decode('utf-8', 'ignore')
    srcs = list(dict.fromkeys(re.findall(r'(?:src|href)="([^"]+\.(?:jpe?g|JPG))"', html)))
    print('== %s：页面 %d 字节，图 %d 个' % (slug, len(html), len(srcs)))
    for s in srcs[:8]:
        u = s if s.startswith('http') else 'https://om-recipes.com' + ('' if s.startswith('/') else '/') + s
        out = os.path.join('C:\\Users\\82302\\AppData\\Local\\Temp', '_probe.jpg')
        subprocess.run(['curl', '-sL', '--max-time', '90', '-o', out, u])
        if not os.path.exists(out):
            continue
        b = open(out, 'rb').read()
        has = PAT in b
        print('   %-62s %5dKB 标签=%s OLYMPUS=%s' % (u[-62:], len(b) // 1024, has, b'OLYMPUS' in b))
        if has:
            keep = os.path.join(r'C:\Users\82302\Desktop', 'OM3-原图-' + slug + '.jpg')
            open(keep, 'wb').write(b)
            print('   >>> 已保存到桌面：', keep)
            break
    else:
        print('   （这条没找到带标签的原图）')
