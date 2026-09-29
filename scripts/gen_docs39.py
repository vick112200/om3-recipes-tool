# -*- coding: utf-8 -*-
"""第 39 轮：HANDOVER 顶部换新 + README 加一条。"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
B = r'D:\workspace\om3-handbook'

TOP = '''# ▶▶▶ 最新（第三十九轮 · v2.29，**接手请先看这段**）

> ## ★★★ 用户三条：① 原版和优化版中间加独立「本站设计」页签（搜索/目录也要更新）
> ## ② 场景对比的"左右滑动图片对比"要保留 + 按场景放对题的图 ③ **上个版本图片全变占位**
>
> ### ③ 图片占位 = 我把 `data-im` 写成了 `images/xxx.jpg`（BUG，已修）
> 页面取图是 `IMG(f) = 'images/' + f`，只写文件名才对。我写成带前缀 → 请求 `images/images/xxx.jpg` → 全 404。
> 修了 `gen_recipes.py` / `gen_lab_slots.py`，并加了断言（`dv_r37` ⑤b）：**所有 data-im 必须是裸文件名且文件存在**。
> 场景页探针还实测了"图真的加载出来"：**50/50、13/13、9/9**（不是只查 DOM 有没有 img）。
>
> ### ② 场景对比：不是删了，是被我埋了（y=16727px）
> 第 37 轮我把 78 行的索引插在图片对比**上面**。现在按用户要求改成：
> · 删掉顶部大标题/小标题；`#scbar` 六个按钮**保留但隐藏**，前面加 **好看的 `<select id="scsel">`**
> · 下拉两组共 **27 项**：实拍对比 6 个（同一构图）+ 按场景挑 21 个
> · **一屏一张左右滑动的图片对比回到顶部**（原机制一行没动）
> · 「按场景挑」= 每条配方放**对题**的那张图：`scripts/gen_phototags.py` 用 PIL 给 444 张图打
>   画面归类标签（肤色/暗部/绿/蓝青/品红/高亮），场景要什么标签就优先放什么图；界面上写明"自动归类，偶尔看错"
> · 旧的 78 行索引整块注释掉；`window.__om3scIdx` 用新表重建做兼容
>
> ### ① 新页签「本站设计」（原版 → **本站设计** → 优化版 → 场景对比）
> · `#paneF` + 底栏按钮；12 张自设计卡片从 paneA **整段搬走**（paneA 因此变短）
> · **目录三份** `#toc`(A)/`#toc3`(F)/`#toc2`(B)，按页签开对应的那份，互斥
> · **搜索三个池** `RIDX`/`LIDX`/`OIDX` —— 顺手修好一个老 bug：`#toc2` 的搜索元素
>   当年"说好后面注入"其实没注入，**优化版搜索池以前是死的**，现在 12 条能搜到
> · 踩了 4 个坑，全都写进 SPEC-round39 §3/§6：页签清单有**两处**（`PANES`+`PS`）、
>   显示条件有 **4 处**写死 A|B|C、底栏按钮要转发到**顶栏隐藏代理** `#tabF`（漏了会连带点亮 A 页签）、
>   以及**生成器插入点**必须跟着改（`gen_recipes.py` 一重跑就把卡片搬回 paneA —— 本轮当场抓到）
>
> ### 验收 / 产物
> `scripts/dv_r39.py` **35/35 全绿**、`scripts/dv_scene39.py` **27/27 全绿**；
> `dv_r37`（含 data-im 体检）、`dv_r33`(0)、`dv_r34`(8/8)、`dv_r35`(8/8)、`dv_mpwheel`、`dv_mount`、
> `dv_barstep3`、`check_app`(70/105/35)、`verify_all`、`dv_clickall`(0/0) 全通过。
> 版本 **v2.29**（`versionCode 229`），APK md5 `201d7032302c47517bb4fa3fc6bdb455`（52.3MB，桌面已同步）。
> 规格/证据/回退：**`SPEC-round39.md`**；回退点 `app/base.before_r39.html`。

---

'''

p = B + r'\HANDOVER.md'
s = io.open(p, encoding='utf-8').read()
old = '# ▶▶▶ 最新（第三十八轮 · v2.28，**接手请先看这段**）'
assert old in s
s = s.replace(old, TOP + '# ▶▶▶ 上一轮（第三十八轮 · v2.28）—— 保留备查', 1)
s = s.replace('> 最后更新 2026-09-24（第三十八轮 · v2.28 · 交接）', '> 最后更新 2026-09-24（第三十九轮 · v2.29 · 交接）', 1)
s = s.replace('  从 v2.0 到 v2.28 一直是这把钥匙', '  从 v2.0 到 v2.29 一直是这把钥匙', 1)
s = s.replace('  本轮（第三十八轮 / v2.28）新增 `app/base.before_r38.html`',
              '  本轮（第三十九轮 / v2.29）新增 `app/base.before_r39.html`（= v2.28 源码）；\n'
              '  再往前（第三十八轮 / v2.28）的 `app/base.before_r38.html`', 1)
s = s.replace('- `SPEC-round38.md` —— **最新一轮（第三十八轮 / v2.28）的规格',
              '- `SPEC-round39.md` —— **最新一轮（第三十九轮 / v2.29）的规格 + 逐条验收 + 教训**；\n'
              '  再往前 `SPEC-round38.md`（第三十八轮 / v2.28）的规格', 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('HANDOVER 已更新')

p2 = B + r'\README.md'
r = io.open(p2, encoding='utf-8').read()
anchor = '## 已知待办\n\n'
add = '''## 已知待办

> **★★★ v2.29（第三十九轮）① 新增「本站设计」独立页签 ② 场景对比页改造 ③ 修"图片全变占位"**
> - **新页签**：底栏 `原版方案 → 本站设计 → 优化版 → 场景对比`；12 张自设计卡片从原版页搬进 `#paneF`（原版页变短）。
>   **目录变三份**（`#toc`/`#toc3`/`#toc2`，按页签互斥打开）；**搜索变三个池**（原版/本站设计/优化版）——
>   顺手修好一个老 bug：`#toc2` 的搜索框当年"说好后面注入"其实没注入，**优化版搜索池以前是死的**。
> - **场景对比**：删掉顶部大标题小标题；`#scbar` 按钮条隐藏，改用**好看的 `<select>`**（两组共 27 项：
>   实拍对比 6 + 按场景挑 21）；**一屏一张左右滑动的图片对比回到顶部**（上轮被 78 行索引顶到了 16727px 处）。
>   选场景后**按画面自动归类挑对题的图**（PIL 给 444 张图打标签：肤色/暗部/绿/蓝青/品红/高亮），图上标注"自动归类，偶尔看错"。
> - **修 BUG**：模拟预览图的 `data-im` 我多写了 `images/` 前缀 → 请求 `images/images/…` → **整片占位图**。
>   已改回只写文件名，并加断言（所有 data-im 必须裸文件名且文件存在）。场景页探针实测图**真的加载**：50/50、13/13、9/9。
> - 验收：`dv_r39`（35/35）、`dv_scene39`（27/27）、`dv_r37`（含 data-im 体检）、`dv_r33`(0)、`dv_r34`(8/8)、
>   `dv_r35`(8/8)、`dv_mpwheel`、`dv_mount`、`dv_barstep3`、`check_app`(70/105/35)、`verify_all`、`dv_clickall`(0/0) 全通过。
>
'''
assert anchor in r
r = r.replace(anchor, add, 1)
io.open(p2, 'w', encoding='utf-8', newline='').write(r)
print('README 已更新')
