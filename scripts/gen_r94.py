# -*- coding: utf-8 -*-
"""第 94 轮：**打赏功能先隐藏**（需求方 2026-09-29：「不用嵌二维码，这个功能先隐藏，后面再做」）

做法：**不删代码，只把按钮藏起来**（`display:none`）——
- 收款码一行（`var OM3_DONATE_IMG = '';   /* r93:donate */`）原样留着；
- 按钮、弹窗、`om3Ask` 的 `img/onlyOk` 能力、`scripts/set_donate.py` 全部留着；
- 顶栏照旧（右上角不再出现 ☕）。

**以后想开（三步）**：
1. 去掉按钮上的 `style="display:none"`（这一行就是唯一的开关）；
2. `python scripts/set_donate.py 你的收款码.png`（内嵌收款码）；
3. 照常出包（`mkasset.py` → `build.sh`）。
（`scripts/dv_r94.py` 里有一键验证：把 style 去掉后，点 ☕ 能弹出带收款码的弹窗。）

## 显式声明
- 涉及：`app/base.html`（只加一个 `style="display:none"` + 注释）、`scripts/dv_r94.py`、本文档
  + `HANDOVER.md` + `AGENTS.md` + `README.md`（产物新名字）+ `TEST-camera.md`。
- 不涉及：**Java 不改**；相机连接链/BLE/配方数据不动；**新增 id：无**；**新增 data-tv：无**
  （`donate` 由第 93 轮声明，本轮只把它藏起来）。

用法：python scripts/gen_r94.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r94：'
OLD = '    <button type="button" class="donbtn" data-tv="donate" title="请我喝杯咖啡" aria-label="打赏">☕</button>'
NEW = ('    <!-- r94：**先隐藏**（需求方 2026-09-29「不用嵌二维码，这个功能先隐藏，后面再做」）。\n'
       '         想开：① 去掉下面那个 style="display:none"；② python scripts/set_donate.py 收款码.png；③ 出包。 -->\n'
       '    <button type="button" class="donbtn" data-tv="donate" style="display:none" '
       'title="请我喝杯咖啡" aria-label="打赏">☕</button>')


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r94] 已经是目标状态 —— 不重复改。')
        return 0
    if html.count(OLD) != 1:
        print('[r94] ✗ 找不到打赏按钮那一行（%d 处）—— **不写盘**' % html.count(OLD))
        return 1
    cur = html.replace(OLD, NEW, 1)
    if 'style="display:none" title="请我喝杯咖啡"' not in cur:
        print('[r94] ✗ 隐藏没写上去 —— **不写盘**')
        return 1
    if "var OM3_DONATE_IMG = '';" not in cur:
        print('[r94] ✗ 收款码那行不该动（用于以后填图）—— **不写盘**')
        return 1
    if '--check' in sys.argv:
        print('[r94] --check 通过（未写盘）：按钮会被藏起来，代码/入口全留着')
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(cur)
    print('[r94] ✓ 打赏按钮已隐藏（display:none）；收款码那一行、弹窗能力、set_donate.py 都留着')
    return 0


if __name__ == '__main__':
    sys.exit(main())
