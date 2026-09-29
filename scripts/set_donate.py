# -*- coding: utf-8 -*-
"""把收款码图片**内嵌**进 app/base.html（右上角 ☕ 打赏按钮用）。

用法：
    python scripts/set_donate.py 收款码.png            # 内嵌（幂等；换图再跑一次即可）
    python scripts/set_donate.py --show                # 只看现在嵌的是多大 / 什么时候嵌的
    python scripts/set_donate.py --clear               # 清掉（回到"还没放进来"）

说明：
- 离线单文件 App → 图片必须 base64 内嵌（手册里 3.8 MB 的样片也是这么做的）。
- 只改一行：`var OM3_DONATE_IMG = '…';   /* r93:donate */`
- 安全检查：文件必须是 PNG/JPEG/WebP/GIF（按魔数判断）；太大（>1.5 MB）会警告并拒绝
  （收款码一般几十 KB；太大说明多半选错了图）。
- 幂等：同一张图重复跑不会改坏（会先校验再写）。
"""
import base64
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'app', 'base.html')
LINE_RE = re.compile(r"var OM3_DONATE_IMG = '[^']*';\s*/\* r93:donate \*/")

MAGIC = [
    (b'\x89PNG\r\n\x1a\n', 'image/png'),
    (b'\xff\xd8\xff', 'image/jpeg'),
    (b'GIF87a', 'image/gif'), (b'GIF89a', 'image/gif'),
]
MAX = 1500 * 1024


def kind_of(data):
    for magic, mime in MAGIC:
        if data.startswith(magic):
            return mime
    if len(data) > 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return ''


def main():
    args = sys.argv[1:]
    page = io.open(PAGE, encoding='utf-8').read()
    m = LINE_RE.search(page)
    if not m:
        print('✗ 找不到那一行 `var OM3_DONATE_IMG = …;` —— 先跑 python scripts/gen_r93.py')
        return 1
    cur = m.group(0)

    if not args or args[0] == '--show':
        size = len(cur)
        has = "data:image" in cur
        print('现在：%s（占 %d 字节）' % ('已内嵌收款码' if has else '**还没内嵌**（弹窗会如实说"收款码还没放进来"）', size))
        print('那一行：' + (cur[:120] + '…' if len(cur) > 120 else cur))
        print('\n填图：python scripts/set_donate.py 你的收款码.png')
        return 0

    if args[0] == '--clear':
        page = page[:m.start()] + "var OM3_DONATE_IMG = '';   /* r93:donate */" + page[m.end():]
        io.open(PAGE, 'w', encoding='utf-8', newline='').write(page)
        print('✓ 已清掉收款码（弹窗回到"还没放进来"）')
        return 0

    path = args[0]
    if not os.path.exists(path):
        print('✗ 找不到文件：%s' % path)
        return 1
    data = io.open(path, 'rb').read()
    mime = kind_of(data)
    if not mime:
        print('✗ 这不是 PNG/JPEG/WebP/GIF（收款码请存成 PNG）')
        return 1
    if len(data) > MAX:
        print('✗ 图片太大（%.0f KB）—— 收款码一般几十 KB，请换一张（或先压缩）' % (len(data) / 1024.0))
        return 1
    uri = 'data:%s;base64,%s' % (mime, base64.b64encode(data).decode('ascii'))
    new = "var OM3_DONATE_IMG = '%s';   /* r93:donate */" % uri
    if new == cur:
        print('✓ 已经是这张图了（没变）')
        return 0
    page = page[:m.start()] + new + page[m.end():]
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(page)
    print('✓ 已内嵌收款码：%s（%s，%.0f KB → base64 %.0f KB）'
          % (os.path.basename(path), mime, len(data) / 1024.0, len(uri) / 1024.0))
    print('  下一步：python scripts/dv_r93.py 然后照常出包（build.sh）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
