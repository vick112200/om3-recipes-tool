# -*- coding: utf-8 -*-
"""第 94 轮的**收口**探针（口径已按第 95 轮更新）。

第 94 轮做的是"打赏按钮**先隐藏**"（`style="display:none"`，需求方当时说"不用嵌二维码，后面再做"）。
第 95 轮需求方改主意：**把打赏改成"去 GitHub 点个 Star"**，于是：
- ⭐ 按钮**可见**（不再隐藏）；
- 行为断言（弹窗 / 打开方式 / 浏览器兜底）都在 `dv_r95.py`；
- 第 94 轮那句"隐藏但一键能开"的验法**已由 dv_r95 取代**（口径记录见 `SPEC-round93.md` §6 与 `HANDOVER.md`）。

本文件现在只钉："按钮不再隐藏 + 打赏机制没被删"。
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
page = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()
OK, FAIL = [], []


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


print('=== 第 94 轮那件事的现状（第 95 轮之后） ===')
A('class="donbtn" data-tv="star"' in page, 'A1 右上角按钮还在（现在是 ⭐ 点 Star）')
_btn = page[page.index('class="donbtn" data-tv="star"'):]
_btn = _btn[:_btn.index('>')]
A('display:none' not in _btn, 'A2 它**不再隐藏**了（第 94 轮藏的，第 95 轮拿出来了）')
A("var OM3_DONATE_IMG = ''" in page and os.path.exists(os.path.join(ROOT, 'scripts', 'set_donate.py')),
  'A3 打赏那套机制没删（收款码那一行 + set_donate.py 都在，想恢复随时能恢复）')
A('r94：' in page, 'A4 `r94：` 的历史注释还在（能看出这段的来龙去脉）')
A('r95：' in page, 'A5 `r95：` 标记在（改法与行为验收见 dv_r95）')

print()
print('第 94 轮探针（收口版）：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
