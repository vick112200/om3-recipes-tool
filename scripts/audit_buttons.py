# -*- coding: utf-8 -*-
"""按钮体检：找出"点了没反应"的按钮（需求方 2026-09-28：「点了没啥反应」）。

背景：第 74 轮把「扫码连接」放回来时，**只放了按钮、没接上功能**（它的 click 只 `showStep(1)`），
于是用户点了完全没反应 —— 而探针当年只断言了"可见/排后/样式次要"，没断言"点了有反应"。
这个脚本就是补这个洞：把"有按钮、没处理器"的按钮列出来。

判定方法（启发式，但要够准）：
  对页面里每个 `<button … id="X">`，在 JS 里找 `'X'` 的**所有**出现位置，
  看附近有没有 `addEventListener` / `tvBind` / `uvBind` / `.onclick` / `.click()` /
  `data-act="X"` / `bindClick(` 这类"有人接手"的痕迹；一个都找不到 → 报"可能没处理器"。

用法：python scripts/audit_buttons.py [--pane paneD] [--pane paneT] [--all]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'app', 'base.html')

HANDLE = ('addEventListener', 'tvBind', 'uvBind', 'onclick', '.click()', 'bindClick', 'bindTap')


def main():
    s = io.open(PAGE, encoding='utf-8').read()
    want_all = '--all' in sys.argv
    panes = []
    for i, a in enumerate(sys.argv):
        if a == '--pane' and i + 1 < len(sys.argv):
            panes.append(sys.argv[i + 1])

    if panes:
        # 只看指定 pane 里的按钮（默认：连接页 + 测试页）
        segs = []
        for pn in panes:
            i0 = s.index('<div id="%s"' % pn)
            i1 = s.find('<div id="pane', i0 + 10)
            if i1 < 0:
                i1 = len(s)
            segs.append((pn, s[i0:i1]))
    elif want_all:
        segs = [('全页', s)]
    else:
        i0 = s.index('<div id="paneD"')
        i1 = s.index('<div id="paneE"')
        segs = [('paneD+paneT', s[i0:i1])]

    print('=== 按钮体检 ===')
    bad = []
    total = 0
    for name, seg in segs:
        ids = re.findall(r'<button[^>]*\bid="([A-Za-z0-9_]+)"', seg)
        # 也把 <button … data-tv="x"> 算进来（第 77/75/70 轮那批）
        ids += ['data-tv:' + x for x in re.findall(r'<button[^>]*data-tv="([a-z0-9\-]+)"', seg)]
        for bid in ids:
            total += 1
            key = bid.split(':', 1)[1] if bid.startswith('data-tv:') else bid
            # data-tv 那批：JS 里是按**名字字符串**找的（uvBind('uv-cmds', …)），所以两种写法都搜
            ptrn = re.compile(r"'" + re.escape(key) + r"'")
            hits = [m.start() for m in ptrn.finditer(s)]
            ok = False
            for h in hits:
                win = s[max(0, h - 200):h + 260]
                if any(k in win for k in HANDLE):
                    ok = True
                    break
            if not ok:
                bad.append((name, bid))
    print('检查了 %d 个按钮，**可能没人接手**的 %d 个：' % (total, len(bad)))
    for name, bid in bad:
        print('   ✗ %-12s %s' % (name, bid))
    print()
    if not bad:
        print('结论：paneD/paneT 里每个按钮都能找到处理器 ✅')
        return 0
    print('结论：上面这些**要么真没处理器，要么写法不在这套启发式里** —— 逐个手查（先查在客户页的：paneD）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
