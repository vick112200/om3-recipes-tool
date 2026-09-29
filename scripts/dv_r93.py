# -*- coding: utf-8 -*-
"""第 93 轮的**收口**探针（口径已按第 95 轮更新）。

第 93 轮做的是"打赏按钮（展示收款码）"，第 95 轮按需求方要求改成了"**去 GitHub 点个 Star**"：
- 按钮：`data-tv="donate"`（打赏）→ `data-tv="star"`（点 Star），并且**取消隐藏**；
- 弹窗：收款码图 → "去 GitHub 点 Star"（App 用 om3Ask、浏览器用 confirm）；
- **打赏那套机制留着**：`var OM3_DONATE_IMG`（收款码内嵌那一行）+ `scripts/set_donate.py`。

所以本文件现在只钉"第 93 轮那部分机制还在不在"（行为层面全在 `dv_r95.py` 里验），
原文案/截图/嵌图那套行为断言已经**由 dv_r95 取代**（`SPEC-round93.md` §6 有口径说明）。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
page = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()
OK, FAIL = [], []


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


print('=== 第 93 轮机制的"现在仍然成立"部分 ===')
A('<title>om3 recipes tool</title>' in page and 'OM-3 色彩配方手册' not in page, 'A1 第 93 轮的改名仍然成立（页面标题）')
A('om3 recipes tool' in page, 'A2 名字仍是 om3 recipes tool')
A('data-tv="star"' in page, 'A3 右上角按钮现在是 star（第 95 轮改的）')
A('data-tv="donate"' not in page, 'A4 旧的 donate 选择器已经不在了')
A("var OM3_DONATE_IMG = ''" in page, 'A5 **打赏机制留着**：收款码那一行还在（`OM3_DONATE_IMG`）')
A(os.path.exists(os.path.join(ROOT, 'scripts', 'set_donate.py')), 'A6 `scripts/set_donate.py` 还在（想恢复打赏随时能填图）')
A('window.om3OpenUrl' in page and 'https://github.com/vick112200/om3-recipes-tool' in page,
  'A7 现在指向 GitHub 仓库（第 95 轮的行为，细节见 dv_r95）')
A('r95：' in page, 'A8 `r95：` 标记在（说明第 95 轮已应用）')

print()
print('第 93 轮探针（收口版）：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
