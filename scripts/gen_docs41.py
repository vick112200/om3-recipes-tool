# -*- coding: utf-8 -*-
"""第 41 轮：SPEC + HANDOVER 顶部 + README 条目（用文件方式写，避免 shell 引号/反引号被吃）。"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
B = r'D:\workspace\om3-handbook'

SPEC = '''# SPEC-round41.md · v2.31 —— 滑动**回到最初那版**（原生拖动 + CSS 吸附），JS 不再拦

> 用户 2026-09-24：「滑动还是不行，**回到最初那版**可以不，就是**只把滑动这个换成最初对比的那个**」

## 0. 用户要的是什么

第 33 轮用户提过"一次滑动只换一张"→ 我先用 140ms 防抖事后拉回（第 33 轮），
第 40 轮又改成**手势级拦截**（`touchstart/touchmove/touchend` + 强制落点 + 380ms 兜底）。
结果**真机上滑不动** —— 原因是那套 JS 会跟浏览器的原生拖动/惯性滚动**抢控制权**。
用户现在的取舍很明确：**手感优先，回到最初那版**（第 33 轮之前的样子）。

## 1. 改法：删掉 JS 拦截，改成"原生 + 一个 CSS 属性"

| # | 改动 | 说明 |
|---|---|---|
| 1 | **删除** `pager.addEventListener('touchstart'/'touchmove'/'touchend')` | 不再拦手势 |
| 2 | **删除** `pager.addEventListener('wheel')` 的 `preventDefault` | 桌面横滚也交回浏览器 |
| 3 | **删除** `scGo()` 强制落点 + 380ms 兜底 + `pager.scrollTo` | 不顶着用户的手 |
| 4 | `scroll` 事件**只更新位置标签**（`3 – 3 / 50`）；另外只做一次只读记账（量到有效宽度时记 `scLast`），**不碰 scrollLeft** | 最初那版就是这样 |
| 5 | `‹ ›` 按钮回到最初那种"翻一屏"：`pager.scrollBy({left: ±(clientWidth + 12), behavior:'smooth'})` | |
| 6 | **"一次只换一张"改用纯 CSS**：`.scslide{scroll-snap-stop:always}` | 浏览器自己在一次滑动里**只停一个吸附点**，不需要 JS；Chrome / Android WebView 75+ 支持，**不支持就退化成自由滚（= 最初那版行为，不会坏）** |

保留不动：`scroll-snap-type:x mandatory`（最初那版就有）、位置标签 `upd()`、场景下拉「按场景挑」、
`window.__scIdx()` 只读接口（原来的 `window.__scGo` 已删）。

## 2. 验收（`python scripts/dv_scene41.py` → 19/19 全绿）

静态：
- 代码里**没有** `pager.addEventListener('touchstart'/'touchmove'/'touchend'/'wheel')`；全书已无 `scGo`；
  无 `pager.scrollTo` / `if (smooth)` 兜底
- `scroll` 事件体里只有 `upd()`（更新标签）
- `‹ ›` 用 `scrollBy({left: ∓(clientWidth+12)})`
- `.scslide` 有 `scroll-snap-stop:always`；`.scpager` 仍是 `scroll-snap-type:x mandatory`

运行时（headless + 真实图 + 真实布局）：
- 步长 522px；`getComputedStyle(.scslide).scrollSnapStop === 'always'`（**浏览器真的认了**）；
  `scrollSnapType = x mandatory`
- 手动滚到第 4 张（`scrollLeft=1566`）→ **位置被保留**（1566/1566），位置标签 = `4 – 4 / 50`
- **甩到 `scrollWidth` → 停在末尾 25578，不会跳回第一张**
- `‹ ›` 按钮（用 spy 看实际入参）：`› → +522`、`‹ → −522`（正好一屏）
- 场景下拉切「夜景霓虹」仍生效（9 张）且回到第一张
- 全程 0 JS 报错

> 说明：`scripts/dv_scene40.py`（第 40 轮那套手势的验收）**已删除** —— 它测的行为被本轮按用户要求撤掉了。

## 3. 产物

| 项 | 值 |
|---|---|
| `app/base.html` | md5 `2fb7cf72bedfb69365eec5197afefe88` |
| `apk/build/om3.apk` | **v2.31**（`versionCode 231`），md5 `5cb18a6f625b0f8f67a6adab3d909b75` |
| `apk/assets/index.html` | md5 `8dbc5d1ee89537e262ece8b2f081701f`（徽标 v2.31 / build 231） |
| APK 内自查 | 有 `scroll-snap-stop:always`；**没有** `pager.addEventListener('touchstart'`；**没有** `scGo(`；有自绘下拉 `#scselbtn` |
| `~/Desktop/OM-3色彩配方手册.apk` | 已同步（签名未变，可直接覆盖） |

回退点：`app/base.before_r41.html`（= v2.30 源码）

## 4. 教训（本轮最贵的一条）

**别跟浏览器的原生滚动抢控制权。** 两轮下来：
- 第 33 轮「防抖事后拉回」→ 一甩到底拦不住；
- 第 40 轮「手势拦截 + 强制落点」→ 真机上**滑不动**（JS 与原生拖动互抢）。
- 想要"一次一张"，正确解法是**声明式**的：`scroll-snap-stop: always` —— 浏览器原生行为，零 JS，退化也安全。

另一条：**探针要验真实代码，不要验注释**（本轮静态检查一度被我自己的注释文字误命中），
以及**能用 spy 就别依赖动画**（headless 里 smooth 滚动不生效，直接量 `scrollLeft` 会误判）。

## 5. 留给下一轮

1. 真机确认"滑动恢复正常" + 「一次是否还会跳好几张」（若 WebView 不支持 `scroll-snap-stop`，就会是自由滚）。
2. 若用户仍想更"一板一眼"，可考虑**去掉 `scroll-snap-type`** 或加 `scroll-snap-stop` 的组合微调 —— 但**不要再上 JS 拦滚动**。
'''

io.open(B + r'\SPEC-round41.md', 'w', encoding='utf-8', newline='').write(SPEC)
print('SPEC-round41.md 已写')

TOP = '''# ▶▶▶ 最新（第四十一轮 · v2.31，**接手请先看这段**）

> ## ★★★ 用户：「滑动还是不行，**回到最初那版**，只把滑动换成最初对比的那个」
>
> ### 为什么滑不动（第 40 轮我干错了）
> 第 40 轮我把翻页改成**手势级拦截**（`touchstart/touchmove/touchend` + `scGo` 强制落点 + 380ms 兜底），
> 它会和浏览器的**原生拖动 / 惯性滚动抢控制权** → 真机上表现为"滑不动"。
> 第 33 轮那版（140ms 防抖事后拉回）同样不对：一甩到底拦不住。**两次都是 JS 插手滚动，方向就错了。**
>
> ### 本轮改法：删掉 JS 拦截，回到最初那版 + 一个 CSS 属性
> - **删**：`pager` 上的 touchstart/move/end 手势、wheel 拦截、`scGo` 强制落点、`scrollTo` 兜底
> - **留**：`scroll` 事件只更新位置标签（`3 – 3 / 50`，**不碰 scrollLeft**）；`‹ ›` 用最初那种
>   `scrollBy({left: ±(clientWidth+12)})` 翻一屏；`scroll-snap-type:x mandatory`（最初那版就有）
> - **"一次只换一张"改成声明式**：`.scslide{scroll-snap-stop:always}` —— 浏览器原生行为、零 JS，
>   不支持的环境就退化成自由滚（= 最初那版行为，**不会坏**）
>
> ### 验收 / 产物
> `scripts/dv_scene41.py` **19/19 全绿**：浏览器真的认 `scrollSnapStop='always'`；滚到第 4 张**位置被保留**
> （1566/1566，标签 `4 – 4 / 50`）；**甩到末尾 25578 不跳回第一张**；`‹ ›` 位移 ±522（正好一屏）；
> 自绘下拉/按场景挑仍正常；0 报错。`dv_scene39`(27/27)、`dv_r39`(35/35)、`dv_r37` 全通过。
> （`dv_scene40.py` 测的是被撤掉的那套手势，**已删除**。）
> 版本 **v2.31**（`versionCode 231`），APK md5 `5cb18a6f625b0f8f67a6adab3d909b75`（桌面已同步）；
> APK 内自查：有 `scroll-snap-stop:always`、**无**手势拦截、**无** `scGo(`。
> 规格：**`SPEC-round41.md`**；回退点 `app/base.before_r41.html`。
>
> ### 教训（最贵的一条）
> **别跟浏览器的原生滚动抢控制权。** 想要"一次一张"就写成**声明式**（`scroll-snap-stop: always`），
> 而不是 JS 事后纠正或手势拦截。另：**探针要验真实代码别验注释**；**能用 spy 就别依赖动画**
> （headless 里 smooth 滚动不生效，直接量 scrollLeft 会误判）。

---

'''

p = B + r'\HANDOVER.md'
s = io.open(p, encoding='utf-8').read()
i = s.find('# ▶▶▶ 最新（第四十轮 · v2.30')
j = s.find('# ▶▶▶ 上一轮（第三十九轮 · v2.29）')
assert i > 0 and j > i, 'HANDOVER 段落 i=%d j=%d' % (i, j)
s = s[:i] + TOP + s[j:]
s = s.replace('> 最后更新 2026-09-24（第四十轮 · v2.30 · 交接）', '> 最后更新 2026-09-24（第四十一轮 · v2.31 · 交接）', 1)
s = s.replace('  从 v2.0 到 v2.30 一直是这把钥匙', '  从 v2.0 到 v2.31 一直是这把钥匙', 1)
s = s.replace('  本轮（第四十轮 / v2.30）新增 `app/base.before_r40.html`',
              '  本轮（第四十一轮 / v2.31）新增 `app/base.before_r41.html`（= v2.30 源码）；\n'
              '  再往前（第四十轮 / v2.30）的 `app/base.before_r40.html`', 1)
s = s.replace('- `SPEC-round40.md` —— **最新一轮（第四十轮 / v2.30）的规格',
              '- `SPEC-round41.md` —— **最新一轮（第四十一轮 / v2.31）的规格 + 教训**；\n'
              '  再往前 `SPEC-round40.md`（第四十轮 / v2.30）的规格', 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('HANDOVER 已更新')

R = '''> **★★★ v2.31（第四十一轮）滑动回到最初那版（原生拖动 + CSS 吸附）**
> - 用户反馈「滑动还是不行，回到最初那版」：第 40 轮我加的手势拦截（touchstart/move/end + 强制落点 + 380ms 兜底）
>   会跟浏览器**原生拖动抢控制权** → 真机"滑不动"。本轮把 JS 拦截**整套删除**。
> - 现在：`scroll` 事件只更新位置标签（不碰 scrollLeft）；`‹ ›` 用 `scrollBy({left: ±(clientWidth+12)})` 翻一屏；
>   `scroll-snap-type:x mandatory` 保持（最初那版就有）。
> - 「一次只换一张」改成**声明式**：`.scslide{scroll-snap-stop:always}`（浏览器原生行为、零 JS；
>   不支持就退化成自由滚，不会坏）。
> - 验收：`dv_scene41`（19/19：浏览器认 `scrollSnapStop=always`、滚到第 4 张位置被保留、甩到末尾不跳回第一张、
>   `‹ ›` 位移 ±522）、`dv_scene39`(27/27)、`dv_r39`(35/35)、`dv_r37` 全通过；`dv_scene40.py` 已删除（测的是被撤掉的行为）。
>
'''

p2 = B + r'\README.md'
r = io.open(p2, encoding='utf-8').read()
i2 = r.find('> **★★★ v2.30（第四十轮）')
j2 = r.find('\n## ', i2)
assert i2 > 0, 'README 段落定位失败'
r = r[:i2] + R + r[j2:]
io.open(p2, 'w', encoding='utf-8', newline='').write(r)
print('README 已更新')
