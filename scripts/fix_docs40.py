# -*- coding: utf-8 -*-
"""修复：上一版用 `python -c "...反引号..."` 被 shell 做了命令替换，HANDOVER/README 里
反引号包着的版本号、md5、代码片段全被吃掉了。这里用文件方式干净地重写这两段。"""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
B = r'D:\workspace\om3-handbook'

TOP = '''# ▶▶▶ 最新（第四十轮 · v2.30，**接手请先看这段**）

> ## ★★★ 用户两条反馈：① 场景下拉「安卓原生的太丑」 ② 「一次性能滑好几个 / 滑完自动回到第一个」
>
> ### ① 下拉改**自绘**（原生控件在 WebView 里盖不住）
> `.scselnative` 把原生 `<select>` 藏起来**只当逻辑源**，上面盖自绘控件：`.scselbtn` 深色渐变卡片 +
> `.scmenu` 面板（两组绿色标题 + 27 项 + 可滚动 + 选中 ✓ + 点外部关闭）。选一项写回 `select.value`
> 并派发 `change` → **逻辑仍只有一处**（探针/旧代码都不用改）。
>
> ### ② 翻页改**手势级**（这才是本轮真正的 bug 修复，两个现象的根因如下）
> · 「一次能滑好几张」：原来把翻页交给 CSS `scroll-snap-type:x mandatory` + 140ms 防抖"事后拉回"，
>   **一甩到底根本拦不住**。现在 `touchstart/touchmove/touchend` 判方向、`scGo(scLast±1)`，
>   **一次手势只走一格**。
> · **「滑完自动回到第一个」的元凶**：`scStepW()` 写的是 `width + 12` —— 页签隐藏/未布局时 `width=0`，
>   于是返回 `12` 这个**假有效值**（非 0，躲过了所有"无效检查"），接着
>   `scrollLeft = (scLast±1)*12 ≈ 12px` —— **正好是第一张**。
>   修：量不到有效宽度（`!(w > 40)`）就返回 0 并且**不动作**；再叠加"页签不可见不动作"
>   （`!pager.offsetParent`）。实测：甩到 `scrollWidth` 停在 idx 49（共 50 张），隐藏期间连甩两次也不被拽走。
> · 另加 `scrollTo({behavior:'smooth'})` 的 **380ms 落点兜底**（部分环境会吞掉 smooth 滚动）。
>
> ### 验收 / 产物
> `scripts/dv_scene40.py` **23/23 全绿**（模拟真实触摸事件：一次手势=一张、甩到底不回弹、隐藏不动、
> 自绘下拉 27 项/切场景）；`dv_scene39` 27/27、`dv_r39` 35/35、`dv_r37` 全通过。
> 版本 **v2.30**（`versionCode 230`），APK md5 `c5d8ecdb2e74ff5d41152bffbfc4c4ef`（桌面已同步）。
> 规格：**`SPEC-round40.md`**；回退点 `app/base.before_r40.html`。
>
> ### 教训
> 1. 别把"手感"交给 CSS：`scroll-snap` + 防抖事后拉回，一甩到底就失控；**手势级**才可控。
> 2. **"假有效值"比 0 更危险**：`width + 12` 在隐藏时返回 12，非 0 所以躲过所有无效检查，然后把滚动拽到第一张。
> 3. 原生控件在 WebView 里盖不住 → 要好看得自绘；但**保留原生控件当逻辑源**（隐藏），逻辑才不会分叉。
> 4. 探针要**分开验"逻辑"与"动画落点"**：headless 里 smooth 滚动可能被吞，混在一个断言里会误判。

---

'''

p = B + r'\HANDOVER.md'
s = io.open(p, encoding='utf-8').read()
i = s.find('# ▶▶▶ 最新（第四十轮 · v2.30')
j = s.find('# ▶▶▶ 上一轮（第三十九轮 · v2.29）')
assert i > 0 and j > i, 'HANDOVER 段落定位失败 i=%d j=%d' % (i, j)
s = s[:i] + TOP + s[j:]   # 保留文件头（标题/最后更新那几行）
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('HANDOVER 顶部已重写')

R = '''> **★★★ v2.30（第四十轮）场景下拉改自绘 + 翻页手势化**
> - **下拉**：原生 `<select>` 藏起来只当逻辑源，改成**自绘下拉**（深色卡片按钮 `.scselbtn` + 面板 `.scmenu`：
>   两组绿色标题、27 项、选中 ✓、点外部关闭）。选一项写回 `select.value` 并派发 `change`（逻辑只有一处）。
> - **翻页**：改成**手势级**（`touchstart/touchmove/touchend` 判方向 → `scGo(scLast±1)`），**一次手势只走一格**；
>   原来是 `scroll-snap` + 防抖事后拉回，一甩到底拦不住。
> - **修掉"滑完自动回到第一个"**：`scStepW()` 在页签隐藏时量到宽度 0 → 返回 `0+12=12` 这个"假有效值" →
>   `scrollLeft=(scLast±1)*12≈12px` = 第一张。现在量不到有效宽度就返回 0 且**不动作**，页签不可见也不动作；
>   另加 `scrollTo({behavior:'smooth'})` 的 380ms 落点兜底。
> - 验收：`dv_scene40`（23/23，模拟真实触摸）、`dv_scene39`(27/27)、`dv_r39`(35/35)、`dv_r37` 全通过。

'''
p2 = B + r'\README.md'
r = io.open(p2, encoding='utf-8').read()
i2 = r.find('> **★★★ v2.30（第四十轮）')
j2 = r.find('\n## ', i2)
if j2 < 0:
    j2 = len(r)
assert i2 > 0, 'README 段落定位失败'
r = r[:i2] + R + r[j2:]
io.open(p2, 'w', encoding='utf-8', newline='').write(r)
print('README 条目已重写')
