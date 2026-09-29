# SPEC-round32.md · v2.19（第三十三轮）

> ## 本轮是怎么接手的（很重要，先说清楚）
> 上一轮（v2.18）**做了一半就断了**：`app/base.html` 和 `apk/java/com/om3/handbook/MainActivity.java`
> 都停在 21:35 改到一半的状态 —— 有代码、**没有验收、没有构建、没有 SPEC、没有交接**。
>
> 所以本轮 = **收尾第 33 轮**：把已经写进去的 6 件事逐条验一遍，**查出并修掉 4 个真 bug**
> （其中 2 个会让用户报的问题"看起来改了其实没改"），然后才构建 v2.19。
> 下面「用户原话」都是从代码注释里还原的（用户 2026-09-24 提的）。
>
> ### ⚠ 最要紧的一条：上一轮的「搜索目录」修复**打在了一层根本跑不到的代码上**
> 用户报「**原版方案的搜索目录，点开发现是优化版的**」。
> 上一轮改的是**块02** 里的 `panel()`（让它跟着页签走）。但 🔍 的真正入口是**块07**：
> 它用 `document.addEventListener('click', …, true)`（**捕获阶段**）抢下 `#tocbtn`，
> 然后 `ev.stopPropagation()` —— 块02 给 `#tocbtn` 挂的是冒泡阶段的 click，**永远轮不到**。
> 而块07 里写死了 `$('toc2')`。⇒ **用户看到的行为一点没变**（探针实测：在 A 页签点🔍 开出来仍是 `#toc2`）。
> 本轮把修复挪到块07（真入口），块02 那份保留当兜底。

---

## 0. 一眼版

用户 2026-09-24 提的 6 件事（都写在代码注释里），本轮逐条验完，并修掉 4 个 bug：

| # | 事项 | 状态 |
|---|---|---|
| 1 | 「手机蓝牙界面显示连上了，app 还说没连接」→ 「两条链路」卡（蓝牙 / Wi-Fi / HTTP 分开说） | 已实现，6 种状态验收通过；修掉文案里漏出的 markdown `**`（bug ③） |
| 2 | 「原版方案的搜索目录，点开发现是优化版的」→ 🔍 面板跟着页签 | **上一轮等于没改**（打错层）；本轮挪到块07 真入口（bug ②） |
| 3 | 场景对比卡上的**小色轮** | 有占位但**一个都画不出来**（查不到数据）；本轮修掉（bug ①）**注：是我核出来的** |
| 4 | 场景卡的描述**默认展开** | 已实现（100/100 默认展开，仍可手动收起） |
| 5 | 「快速滑会连着滑过好几张」→ **一次只换一屏** | 已实现（夹取目标：1 屏 / 2 屏 / 正常跨一屏不干预） |
| 6 | 底栏 `fixed` 钉不住时**滚动会"动一下"** → 加 `sticky` 中间级 + 跟手 | 已实现（三级兜底 + `barFollow`） |

**本轮查出的 4 个 bug**（前 2 个直接决定"用户看到的问题有没有真的被修"）：

| bug | 症状 | 根因 |
|---|---|---|
| ① | 场景卡小色轮**永远画不出来**（占位在、SVG 无） | 索引用的键不对：`__OM3RECIPES__[].slug` 是裸 slug，场景卡的 `it.i` 是 `r-<slug>` → **实测 0/289 命中**，去掉 `r-` 前缀后 **289/289 命中** |
| ② | 🔍 仍开优化版目录（用户报的那条**没修好**） | 修在被 `stopPropagation` 挡死的块02；真入口是块07（写死 `#toc2`） |
| ③ | 蓝牙那行直接显示 `**配对过但没连**` | markdown 星号漏进了 `innerHTML` |
| ④ | `#toc` 里的「✕ 关闭」按钮没样式（裸按钮） | CSS 只写了 `#toc2 .om3tocclose`，`#toc` 开起来后不匹配 |

版本 **v2.19**（`versionCode 219`）。回退点 `app/base.before_r33.html`（= v2.18 源码，md5 `2dcc2314fd3bd1cd070e06beae407f52`）。

---

## 1. ①「两条链路」卡：蓝牙 ≠ Wi-Fi ≠ 已连接

**用户的困惑**：手机蓝牙设置里明明显示"已连接"，app 却还是"未连接"。
两句说的**不是一回事** —— app 的"已连接"指的是 **HTTP 通**（备份/写入要用它），蓝牙只是"喊相机开 Wi-Fi"的另一条链路。

- 页面新增 `#camLinkCard`（在「连接相机」页签 = paneD），标题「两条链路：蓝牙管唤醒 · Wi-Fi 管写入」。
- 三段状态 + 一句结论：

| 段 | 数据来源 | 说什么 |
|---|---|---|
| 蓝牙 | 原生 `OM3Native.bleOsConn()` → `{conn:[…], paired:[…]}` | 相机蓝牙已连 / **配对过但没连** / 连着 N 个但不是相机 / 一个都没连 |
| Wi-Fi | 原生 `OM3Native.wifiState()` → `{ssid}` + `camLookLikeCamera(ssid)` | 现在是「XX」（这是相机热点 / 不是） |
| 相机 HTTP | `document.body.classList.contains('cam-on')` | 通 → 已连接，可以备份/写入 / 不通 → 相机没在传输状态 |

- 结论行会直接告诉用户**下一步点哪个按钮**（蓝牙已连但 HTTP 不通 → 点「用蓝牙唤醒相机」）。
- 卡上的「用蓝牙唤醒相机」= **转发点击既有的 `#bleWake`**，不复制第二份实现。
- 状态每 3.5 秒刷一次，但**不在这一页就不刷**（`#paneD` 带 `hide` 就跳过）。
- 原生侧新增（`MainActivity.java`）：`bleOsConn()`（GATT/GATT_SERVER 两档 `getConnectedDevices` + 去重 + `getBondedDevices`）、
  `bleDevJson()`；两者都要 `BLUETOOTH_CONNECT`（API31+），没给就返回 `{}`。

**兼容性**：页面把 `{}`（新原生的空态）、`[]`（老原生/无接口）两种返回都兜住 —— 探针专门造了"返回数组"的老原生场景，不抛错。

**bug ③**（本轮修）：`'相机蓝牙**配对过但没连**：'` → 改成 `<b>配对过但没连</b>`。
探针里 7 个场景逐个断言 `text` 里**不含 `**`**。

---

## 2. ② 🔍 面板跟着页签（把修复挪到真正的入口）

**期望**：在「原版方案」页签点🔍 → 开 `#toc`（原版目录）；在「优化版」页签 → 开 `#toc2`（优化版目录）。

**实情**（本轮查出）：

| 位置 | 谁在管 🔍 | 上一轮的状态 |
|---|---|---|
| **块07**（主脚本，14754 起） | **捕获阶段** `stopPropagation` + 写死 `$('toc2')` | ✗ 没改 → **用户看到的行为没变** |
| 块02（1525 起） | `panel()` 按 `curMod()` 选面板 | 上一轮改了，但**被块07 挡死，跑不到** |
| 块09（18720 起） | 兜底，`if(window.__om3tocToggle) return;` | APK 里让路（`__om3tocToggle` 由块07 注册） |

**本轮改法**（块07）：`apply()` 不再写死 `#toc2`，改为每次按**当前页签**选：

```js
function panelOf(){
  var want2 = (String(window.__om3cur || '') === 'B');    /* B = 优化版 */
  var p1 = $('toc'), p2 = $('toc2');
  return (want2 ? (p2 || p1) : (p1 || p2));
}
```
- 开一个**必须收掉另一个**（含内联 `display` 与 `.open`）—— 块02 也会 toggle 它们，残留会叠成两层。
- 关闭按钮按当前面板插；日志区分「已打开搜索 / 目录（原版方案）」/「（优化版）」。
- **bug ④**（本轮修）：`.om3tocclose` 的 CSS 原来只写了 `#toc2 .om3tocclose`，`#toc` 开起来后按钮是裸的 → 选择器改成 `#toc .om3tocclose,#toc2 .om3tocclose`。
- 块02 那份**保留**（`curMod()` / `panel()` / `jumpToPane()`）：它是兜底，而且 `jumpToPane()` 只在这里。

### 2.1 目录里的锚点：实测归属（决定 jumpToPane 有没有用）

本轮把两份目录的锚点**点了一遍数**：

| 面板 | 锚点数 | 目标所在页签 |
|---|---|---|
| `#toc`（原版方案目录） | 87 | **全部** paneA |
| `#toc2`（优化版目录） | 31 | **全部** paneB |

⇒ **天然的跨页签锚点不存在**，`jumpToPane()` 属兜底逻辑。本轮用一个**人为构造**的跨页签锚点验了它：
在 B 页签点 `#toc` 里指向 paneA 卡片的锚点 → 可见页签从 B **自动切到 A** ✅。

### 2.2 验收（`scripts/verify_all.py` 同步更新）

`verify_all.py` 第 3 条原来断言"点🔍 → `#toc2` display=block"，**这正是在本轮被改掉的行为**，
所以同轮把它改成"跟着页签"的口径。新输出：

```
搜索面板[A 页签应开 #toc] #toc=block #toc2=none 有内容=true 有关闭按钮=true
✕关闭后 #toc=none #toc2=none
搜索面板[B 页签应开 #toc2] #toc=none #toc2=block
```

---

## 3. ③ 场景对比卡的小色轮（bug ①：一个都画不出来）

**做法**：场景卡标题前放一个 `<span class="scwheel" data-v="12个数">` 占位，
由**同一个**色轮渲染器 `mpWheelSVG()` 填 —— 不抄第二份画轮子的代码。

**改完看着没问题的写法**：
```js
var SCV = {};
for (…RA…) if (RA[ri].slug && RA[ri].v) SCV[RA[ri].slug] = RA[ri].v;
…
var wheel = SCV[it.i] ? (…) : '';          /* ← 这里永远取不到 */
```

**为什么一个都没有**：`__OM3RECIPES__[].slug` 是**裸 slug**（`murder_pink_real`），
而场景卡（`SC[].items[].i`）和目录索引（`IDX[].h`）用的是**带前缀的锚点**（`r-<slug>` / `k-<slug>` / `o-<slug>`）。
本轮用数据核了一遍：**直接命中 0/289，去掉 `r-` 前缀 289/289**。

**修法**：两种键都登记（不猜前缀，slug 和 `r-slug` 都放进去）。

**验收**（`scripts/dv_r33.py`）：50 张场景卡 → `.scwheel` 占位 50、已填 SVG 50；
逐张比对 `data-v` 与 `__OM3RECIPES__` 的 12 个色轴值 → **50/50 完全一致**；重复调 `__om3fillWheels()` 幂等。

**顺带验的**（第 ④ 条）：`details.scfold` 100 个**全部**带 `open`（默认展开），仍可手动收起。

---

## 4. ⑤ 一次滑动只换一屏

**用户原话**：「快速滑会连着滑过好几张」。

**做法**：手指抬起、滚动停下（**140ms 没动静**）之后，看这一下跨了几屏：
跨了**不止一屏**就平滑拉回"只跨一屏"，按 `perView()` 算（手机 1 张 / 宽屏 2~3 张，与「上一屏/下一屏」按钮一致）。

**验收**（`scripts/dv_r33.py`，把 `scrollTo` 换成记录器，验**算出来的目标位置**，不受无头浏览器平滑滚动影响）：

| 场景 | 夹取目标 | 期望 |
|---|---|---|
| 0 → 一下滑到第 5 屏 | 第 1 屏 | 第 1 屏 ✅ |
| 第 1 屏 → 一下滑到第 4 屏 | 第 2 屏（= 上次位置 + 一屏） | 第 2 屏 ✅ |
| 只跨一屏的正常滚动 | **不夹** | 不夹 ✅ |

---

## 5. ⑥ 底栏三级兜底 + 跟手

底栏在真机上 `position:fixed` 曾经不好使（v2.16/v2.18 已做 absolute 兜底）。
本轮再加一级：**先试 `sticky`**（由合成器负责，滚动时**不会**"动一下"），sticky 也不行才 absolute。

```
① fixed 写完量一次 → 贴底就用它（绝大多数设备走这条）
② 量出来没贴底 → 试 sticky（bottom:0）→ 贴底就停在这
③ sticky 也不行 → absolute + 按滚动位置自己算 top，并注册 touchmove/touchstart/scroll 跟手（barFollow）
```

- `barFollow()` **只在 absolute 模式下动手**（fixed/sticky 交给浏览器）。为便于验收，导出 `window.__om3barFollow`。
- 切到 ② / ③ 时各写一行日志（不静默降级）。

**验收**（本地 Chrome 的 `fixed` 永远正常，所以直接调机制）：

| 项 | 结果 |
|---|---|
| 正常时 | `__om3barMode=fixed`，不改写 ✅ |
| 第 2 级 sticky（照代码写的那几条样式） | `position=sticky`，**距底 0px**，宽 526 ≤ 视口 526 ✅ |
| 第 3 级 absolute 兜底 | 距底 0px、宽不超屏 ✅ |
| `__om3barFollow()`（mode=absolute） | 立刻拨回贴底（距底 0px）✅ |
| `__om3barFollow()`（mode=fixed） | 不乱插手（保持 static）✅ |
| 跟滚动的回归 | `scripts/dv_barstep3.py` 全绿（含"下滚 400px 后仍贴底"，`scrollY=67`）✅ |

---

## 6. 显式声明清单

| 约束 | 涉及 | 落到哪里 |
|---|---|---|
| 原子性 / 一致 | ✓ | 「两条链路」的结论行只有一句（按优先级判断），不会自相矛盾；开一份面板必收另一份 |
| 幂等 | ✓ | `__om3fillWheels()` 可重复调（`data-v` 元素打 `__om3wheelDone` 标记 + 有子节点就跳过）；`panelOf()`/`apply()` 可重复调 |
| 边界 | ✓ | 蓝牙接口缺失/返回 `{}`/返回 `[]` 三种都兜住；`ssid` 空 → 显示"读不到当前 Wi-Fi"；`SCV` 查不到就不放占位（不画空轮） |
| 超时 / 降级 | ✓ | 底栏 fixed→sticky→absolute 三级降级，每级都实测；面板状态轮询 3.5s、**不在该页签就不刷** |
| 状态一致性 | ✓ | 面板开合由**单一来源**（块07）决定；`#toc`/`#toc2` 的内联 `display` 与 `.open` 同步设置 |
| 兼容 | ✓ | 老原生/无原生不抛错；`#toc`、`#toc2` 的正文/锚点都没动；桌面单文件 HTML 仍由块09 兜底 |
| 性能 | ✓ | 色轮只在 `build()`/DOMContentLoaded/400ms/1500ms 各填一次，且已填的跳过；不在「连接相机」页时不读蓝牙 |
| 迁移 | ∉ | 无数据结构变化（`SCV` 是内存索引，localStorage 里的方案没动） |

---

## 7. 差异分析（规格点 → 实现）

| 规格点 | 实现 |
|---|---|
| 两条链路分开说 | ✅ `#camLinkCard` + `camLinkRender()`（`camOsBle` / `camWifiSsid` / `cam-on`）+ 3.5s 刷新（仅本页） |
| 🔍 跟着页签 | ✅ 块07 `panelOf()`（真入口）；块02 `curMod()/panel()` 保留当兜底 |
| 小色轮 | ✅ `.scwheel` 占位 + `__om3fillWheels()` 复用 `mpWheelSVG()`；索引两种键都登记 |
| 描述默认展开 | ✅ `details.scfold` 加 `open` |
| 一次只换一屏 | ✅ `scLast` + `scStepW()/scIdxNow()` + 140ms 后夹取 |
| 底栏 sticky 中间级 + 跟手 | ✅ `pinBar()` 三级 + `barFollow()`（只认 absolute） |

---

## 8. 没做 / 已知遗留（显式记录）

1. **`#toc2` 在块02 里没有监听**：块02 在解析期 `var nav2=document.getElementById('toc2')`，
   那时 `#toc2`（文档末尾的静态 `<nav>`）还没解析到 → `nav2` **永久 null**，`jumpToPane` 对 `#toc2` 不生效。
   **实务上无碍**：`#toc2` 的 31 个锚点**全部**指向 paneB（见 §2.1），点它们不需要切页签。**本轮未改**（改动面大、收益零）。
2. **`#toc2` 面板里没有搜索输入框**：`#toc2q` / `#toc2chips` / `#toc2res` 在文档另一处、不是 `#toc2` 的子节点。
   所以块07 里 `panelOf().querySelector('input')` 对 `#toc2` 是**空操作**（不自动聚焦，已用 try 兜住）。**无害，未改**。
3. **桌面单文件 HTML 的 🔍**：那里块07 不注册 `__om3tocToggle`（App 才注册），由**块09 兜底 + 块02** 各 toggle 一次，
   仍会两份面板互相干扰。**用户 2026-09-23 明确说过"桌面 HTML 不用管，只维护 app"** → 不改。
4. **块02 的 `window.__om3tocSync` 没人调用**（本轮新增的死代码，因为修复挪去了块07）。保留（万一以后桌面路径要用），无害。
5. **真机未验**（本轮所有验证都在无头 Chrome + `OM3Native` 替身上做的）：
   - 「两条链路」卡要**真机**才看得到真数据：手机蓝牙设置里连上相机 → 进「连接相机」页 → 卡上第一行应该写"相机蓝牙已连：OM-3…"；
   - `sticky` 那一级**在真机上到底走不走得到**（要看真机为什么 `fixed` 不生效）；跟手模式（absolute）在快速甩动时最多差一帧；
   - 场景对比卡的小色轮（34px）在真机上的观感（会不会太挤/看不清）。

---

## 9. 回退清单 & 文件

| # | 位置 | 回退动作 |
|---|---|---|
| 1 | 块07 `panelOf()/otherOf()/apply()/toggle()` | 恢复成只 `$('toc2')` 的版本（**但用户报的 bug 会回来**） |
| 2 | `#toc .om3tocclose` CSS | 选择器改回只写 `#toc2 .om3tocclose` |
| 3 | `SCV['r-' + slug]` | 删掉这一行（**小色轮会全部消失**） |
| 4 | `'相机蓝牙<b>配对过但没连</b>：'` | 改回 `'**配对过但没连**'` |
| 5 | `window.__om3barFollow = barFollow` | 删掉这一行（只是导出，无功能影响） |
| 6 | 整份源码 | 用 `app/base.before_r33.html`（= v2.18，md5 `2dcc2314fd3bd1cd070e06beae407f52`）覆盖 `app/base.html` |

| 文件 | 说明 |
|---|---|
| `app/base.html` | md5 `5a0087c9961dd7c3768ad3d7f40ab77e` |
| `app/base.before_r33.html` | 回退点 = v2.18 源码（md5 `2dcc2314fd3bd1cd070e06beae407f52`） |
| `apk/java/com/om3/handbook/MainActivity.java` | 新增 `bleOsConn()` / `bleDevJson()`（`javac --release 8` 通过） |
| `apk/assets/index.html` | md5 `fa6c6824df9f508121f5ef546e2485d3`（含版本徽标 v2.19 / build 219） |
| `apk/build/om3.apk` | **v2.19**（`versionCode 219` / `versionName 2.19`），md5 `ce12d5c7228d1080acd230ec59302363`，53,394,848 字节 |
| `~/Desktop/OM-3色彩配方手册.apk` | 已更新为同一份（md5 `ce12d5c7228d1080acd230ec59302363`）；签名 SHA-256 `d51a42f3…` 未变 → **可直接覆盖安装 v2.18** |
| `scripts/dv_r33.py` | **本轮新增**：第 33 轮验收探针（①目录面板 ②跨页签跳转 ③小色轮+默认展开 ④一次一屏 ⑤两条链路 6 场景+老原生 ⑥底栏三级兜底+跟手），**0 失败** |
| `scripts/verify_all.py` | 第 3 条改为"🔍 跟着页签"口径（+ B 页签 #toc2 检查） |
| `scripts/check_syntax.py` / `check_app.py` | 全绿（10 个内联块语法通过；0 运行错误 / `om3errs=0`） |

### 本轮的验收证据一览

| 脚本 | 结果 |
|---|---|
| `check_syntax.py` | 10 个内联脚本块全部通过 ✅ |
| `check_app.py` | 配方卡 58 / 加入按钮 81 / 优化版槽位 23 / 运行错误 0 ✅ |
| `dv_r33.py` | **0 失败**（①6 项 ②1 项 ③6 项 ④3 项 ⑤12 项 ⑥6 项 + 汇总）✅ |
| `dv_barstep3.py` | 0 失败（底栏 fixed/自愈/absolute 兜底/滚动后仍贴底）✅ |
| `dv_mpwheel.py` | 全部通过（色轮渲染器回归）✅ |
| `dv_mount.py` | 全部通过（挂载状态回归）✅ |
| `verify_all.py` | 全项正常、运行错误 0 ✅ |
| `javac --release 8`（MainActivity + R） | 退出码 0 ✅ |
| `aapt2 dump badging` | `versionCode=219 versionName=2.19` ✅ |
